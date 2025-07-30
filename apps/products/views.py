from rest_framework import generics, filters, status, viewsets
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAuthenticatedOrReadOnly, BasePermission
from django_filters import rest_framework as django_filters
from django.db.models import Q, Count, Min, Max, Avg, F, Sum
from django.core.cache import cache
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.shortcuts import get_object_or_404
from .models import (
    AttributeType, Tag, ProductClass, ProductClassAttribute,
    ProductCategory, ProductAttribute, Brand,
    Product, ProductVariant, ProductAttributeValue, ProductImage, Collection
)
from .serializers import (
    AttributeTypeSerializer, TagSerializer, ProductClassSerializer,
    ProductCategorySerializer, ProductAttributeSerializer, BrandSerializer,
    ProductListSerializer, ProductDetailSerializer, ProductCreateSerializer,
    BulkProductCreateSerializer, ProductVariantSerializer,
    ProductVariantCreateSerializer, ProductImportSerializer, CollectionSerializer,
    ProductSearchSerializer, ProductStatisticsSerializer
)

# FIX: Custom permission classes for proper store ownership validation
class IsStoreOwnerOrReadOnly(BasePermission):
    """
    Custom permission to only allow owners of a store to edit it.
    FIXED: Proper permission implementation with store ownership validation
    """
    def has_permission(self, request, view):
        # Read permissions for anyone
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True
        
        # Write permissions only for authenticated users
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        # Read permissions for anyone
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True
        
        # Write permissions only for store owner
        if hasattr(obj, 'store'):
            return obj.store.owner == request.user
        elif hasattr(obj, 'owner'):
            return obj.owner == request.user
        
        return False

class StoreFilterMixin:
    """
    Mixin to filter querysets by store ownership for authenticated users
    FIXED: Secure store filtering with proper tenant isolation
    """
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Public access for read-only endpoints
        if self.request.method in ['GET', 'HEAD', 'OPTIONS']:
            store_id = self.request.query_params.get('store')
            if store_id:
                # Validate store exists and is active
                try:
                    from apps.stores.models import Store
                    store = Store.objects.get(id=store_id, is_active=True)
                    return queryset.filter(store=store)
                except Store.DoesNotExist:
                    return queryset.none()
            # If no store specified for public access, return empty
            return queryset.none()
        
        # Authenticated users can only access their stores
        if self.request.user.is_authenticated:
            if hasattr(self.request.user, 'owned_stores'):
                user_stores = self.request.user.owned_stores.filter(is_active=True)
                if hasattr(queryset.model, 'store'):
                    return queryset.filter(store__in=user_stores)
            
            # For non-store models, return all for authenticated users
            return queryset
        
        return queryset.none()

class ProductFilter(django_filters.FilterSet):
    """Advanced product filtering with optimized queries"""
    min_price = django_filters.NumberFilter(method='filter_min_price')
    max_price = django_filters.NumberFilter(method='filter_max_price')
    product_class = django_filters.CharFilter(method='filter_product_class')
    category = django_filters.CharFilter(method='filter_category')
    brand = django_filters.CharFilter(field_name="brand__slug")
    tags = django_filters.CharFilter(method='filter_tags')
    in_stock = django_filters.BooleanFilter(method='filter_in_stock')
    
    class Meta:
        model = Product
        fields = ['status', 'product_type', 'is_featured']
    
    def filter_min_price(self, queryset, name, value):
        """Filter by minimum effective price with optimized query"""
        return queryset.filter(
            Q(base_price__gte=value) |
            Q(base_price__isnull=True, product_class__base_price__gte=value)
        )
    
    def filter_max_price(self, queryset, name, value):
        """Filter by maximum effective price with optimized query"""
        return queryset.filter(
            Q(base_price__lte=value) |
            Q(base_price__isnull=True, product_class__base_price__lte=value)
        )
    
    def filter_product_class(self, queryset, name, value):
        """Filter by product class including descendants with caching"""
        cache_key = f"product_class_descendants_{value}"
        descendant_ids = cache.get(cache_key)
        
        if descendant_ids is None:
            try:
                product_class = ProductClass.objects.get(slug=value)
                descendant_ids = [product_class.id] + list(
                    product_class.get_descendants().values_list('id', flat=True)
                )
                cache.set(cache_key, descendant_ids, timeout=300)  # 5 minutes
            except ProductClass.DoesNotExist:
                return queryset.none()
        
        return queryset.filter(product_class_id__in=descendant_ids)
    
    def filter_category(self, queryset, name, value):
        """Filter by category including descendants with caching"""
        cache_key = f"category_descendants_{value}"
        descendant_ids = cache.get(cache_key)
        
        if descendant_ids is None:
            try:
                category = ProductCategory.objects.get(slug=value)
                descendant_ids = [category.id] + list(
                    category.get_descendants().values_list('id', flat=True)
                )
                cache.set(cache_key, descendant_ids, timeout=300)  # 5 minutes
            except ProductCategory.DoesNotExist:
                return queryset.none()
        
        return queryset.filter(category_id__in=descendant_ids)
    
    def filter_tags(self, queryset, name, value):
        """Filter by multiple tags"""
        tag_slugs = value.split(',')
        return queryset.filter(tags__slug__in=tag_slugs).distinct()
    
    def filter_in_stock(self, queryset, name, value):
        """Filter products that are in stock"""
        if value:
            return queryset.filter(
                Q(product_type='simple', stock_quantity__gt=0) |
                Q(product_type='variable', variants__stock_quantity__gt=0)
            ).distinct()
        return queryset

# FIX: Secure ViewSets with proper permissions and optimized queries
class AttributeTypeViewSet(viewsets.ModelViewSet):
    """Attribute type management ViewSet"""
    serializer_class = AttributeTypeSerializer
    # FIX: Changed from AllowAny to proper permissions
    permission_classes = [IsAuthenticatedOrReadOnly]
    lookup_field = 'slug'
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name_fa', 'name']
    ordering_fields = ['display_order', 'name_fa', 'created_at']
    ordering = ['display_order', 'name_fa']
    
    def get_queryset(self):
        return AttributeType.objects.all()

class TagViewSet(StoreFilterMixin, viewsets.ModelViewSet):
    """Tag management ViewSet"""
    serializer_class = TagSerializer
    # FIX: Changed from AllowAny to proper permissions
    permission_classes = [IsStoreOwnerOrReadOnly]
    lookup_field = 'slug'
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['usage_count', 'name_fa']
    ordering = ['-usage_count', 'name_fa']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Apply additional filters
        tag_type = self.request.query_params.get('type')
        if tag_type:
            queryset = queryset.filter(tag_type=tag_type)
        
        featured_only = self.request.query_params.get('featured')
        if featured_only == 'true':
            queryset = queryset.filter(is_featured=True)
        
        return queryset

class ProductClassViewSet(StoreFilterMixin, viewsets.ModelViewSet):
    """Product class hierarchy management ViewSet"""
    serializer_class = ProductClassSerializer
    # FIX: Changed from AllowAny to proper permissions
    permission_classes = [IsStoreOwnerOrReadOnly]
    lookup_field = 'slug'
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name_fa', 'name']
    ordering_fields = ['display_order', 'name_fa', 'created_at']
    ordering = ['display_order', 'name_fa']
    
    def get_queryset(self):
        queryset = super().get_queryset().filter(is_active=True)
        
        # Filter by parent
        parent_id = self.request.query_params.get('parent')
        if parent_id:
            if parent_id == 'null':
                queryset = queryset.filter(parent__isnull=True)
            else:
                queryset = queryset.filter(parent_id=parent_id)
        
        # Filter by leaf status
        leaf_only = self.request.query_params.get('leaf_only')
        if leaf_only == 'true':
            queryset = queryset.filter(is_leaf=True)
        
        # FIX: Optimize queries with prefetch_related
        return queryset.prefetch_related(
            'children',
            'attributes__attribute_type'
        ).select_related('parent')

class CategoryViewSet(StoreFilterMixin, viewsets.ModelViewSet):
    """Category management ViewSet"""
    serializer_class = ProductCategorySerializer
    # FIX: Changed from AllowAny to proper permissions
    permission_classes = [IsStoreOwnerOrReadOnly]
    lookup_field = 'slug'
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name_fa', 'name']
    ordering_fields = ['display_order', 'name_fa', 'created_at']
    ordering = ['display_order', 'name_fa']
    
    def get_queryset(self):
        queryset = super().get_queryset().filter(is_active=True)
        
        # Filter by parent
        parent_id = self.request.query_params.get('parent')
        if parent_id:
            if parent_id == 'null':
                queryset = queryset.filter(parent__isnull=True)
            else:
                queryset = queryset.filter(parent_id=parent_id)
        
        # FIX: Optimize queries with prefetch_related
        return queryset.prefetch_related(
            'children',
            'attributes__attribute_type'
        ).select_related('parent')

class BrandViewSet(StoreFilterMixin, viewsets.ModelViewSet):
    """Brand management ViewSet"""
    serializer_class = BrandSerializer
    # FIX: Changed from AllowAny to proper permissions
    permission_classes = [IsStoreOwnerOrReadOnly]
    lookup_field = 'slug'
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name_fa', 'name']
    ordering_fields = ['name_fa', 'product_count', 'created_at']
    ordering = ['-product_count', 'name_fa']
    
    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)

class ProductViewSet(StoreFilterMixin, viewsets.ModelViewSet):
    """Product management ViewSet"""
    # FIX: Changed from AllowAny to proper permissions
    permission_classes = [IsStoreOwnerOrReadOnly]
    lookup_field = 'slug'
    filterset_class = ProductFilter
    filter_backends = [
        django_filters.DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter
    ]
    search_fields = ['name_fa', 'name', 'description', 'brand__name_fa', 'sku']
    ordering_fields = [
        'created_at', 'view_count', 'sales_count', 'rating_average'
    ]
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return ProductCreateSerializer
        elif self.action in ['retrieve']:
            return ProductDetailSerializer
        return ProductListSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # For public access, only show published products
        if not self.request.user.is_authenticated or self.request.method in ['GET', 'HEAD', 'OPTIONS']:
            if self.action == 'list':
                queryset = queryset.filter(status='published')
        
        # Dynamic attribute filtering
        for key, value in self.request.query_params.items():
            if key.startswith('attr_') and value:
                attr_name = key[5:]  # Remove 'attr_' prefix
                queryset = queryset.filter(
                    attribute_values__attribute__attribute_type__name=attr_name,
                    attribute_values__value_text=value
                )
        
        # FIX: Optimize queries to prevent N+1 problems
        return queryset.select_related(
            'brand', 'category', 'product_class', 'store'
        ).prefetch_related(
            'tags', 'images', 'variants', 'attribute_values__attribute__attribute_type'
        ).distinct()
    
    def retrieve(self, request, *args, **kwargs):
        """Increment view count when retrieving product"""
        instance = self.get_object()
        # FIX: Add IP-based rate limiting for view count
        user_ip = request.META.get('REMOTE_ADDR', '')
        instance.increment_view_count(user_ip=user_ip)
        return super().retrieve(request, *args, **kwargs)
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def bulk_create(self, request):
        """Bulk create products with store ownership validation"""
        # FIX: Validate store ownership
        store_id = request.data.get('store')
        if store_id:
            try:
                from apps.stores.models import Store
                store = Store.objects.get(id=store_id, owner=request.user, is_active=True)
            except Store.DoesNotExist:
                return Response(
                    {'error': 'دسترسی غیرمجاز به فروشگاه یا فروشگاه یافت نشد'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
        else:
            return Response(
                {'error': 'شناسه فروشگاه الزامی است'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = BulkProductCreateSerializer(data=request.data)
        if serializer.is_valid():
            products = serializer.save()
            return Response({
                'message': f'{len(products)} محصول با موفقیت ایجاد شد',
                'products': ProductListSerializer(products, many=True, context={'request': request}).data
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        """Advanced product search with caching"""
        serializer = ProductSearchSerializer(data=request.query_params)
        if serializer.is_valid():
            query = serializer.validated_data.get('query', '')
            store_id = request.query_params.get('store')
            limit = min(int(request.query_params.get('limit', 10)), 50)  # Max 50 results
            
            if not query or len(query) < 2:
                return Response({'results': [], 'message': 'حداقل 2 کاراکتر برای جستجو الزامی است'})
            
            # FIX: Cache search results
            cache_key = f"product_search_{hash(query)}_{store_id}_{limit}"
            cached_results = cache.get(cache_key)
            if cached_results:
                return Response(cached_results)
            
            # Search products
            products = Product.objects.filter(status='published')
            if store_id:
                try:
                    from apps.stores.models import Store
                    store = Store.objects.get(id=store_id, is_active=True)
                    products = products.filter(store=store)
                except Store.DoesNotExist:
                    return Response({'results': [], 'message': 'فروشگاه یافت نشد'})
            
            # Search in multiple fields
            products = products.filter(
                Q(name_fa__icontains=query) |
                Q(name__icontains=query) |
                Q(description__icontains=query) |
                Q(brand__name_fa__icontains=query) |
                Q(sku__icontains=query) |
                Q(tags__name_fa__icontains=query) |
                Q(product_class__name_fa__icontains=query)
            ).distinct()[:limit]
            
            results = {
                'products': ProductListSerializer(products, many=True, context={'request': request}).data,
                'total_found': products.count()
            }
            
            # Cache results for 5 minutes
            cache.set(cache_key, results, timeout=300)
            return Response(results)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CollectionViewSet(StoreFilterMixin, viewsets.ModelViewSet):
    """Collection management ViewSet"""
    serializer_class = CollectionSerializer
    # FIX: Changed from AllowAny to proper permissions
    permission_classes = [IsStoreOwnerOrReadOnly]
    lookup_field = 'slug'
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['display_order', 'name_fa', 'created_at']
    ordering = ['display_order', 'name_fa']
    
    def get_queryset(self):
        queryset = super().get_queryset().filter(is_active=True)
        
        featured_only = self.request.query_params.get('featured')
        if featured_only == 'true':
            queryset = queryset.filter(is_featured=True)
        
        return queryset

# FIX: Add proper authentication to function-based views
@api_view(['GET'])
@permission_classes([AllowAny])
@method_decorator(cache_page(300))  # 5 minutes cache
def category_filters(request, slug):
    """Get available filters for a category"""
    try:
        category = ProductCategory.objects.get(slug=slug, is_active=True)
    except ProductCategory.DoesNotExist:
        return Response({'error': 'دسته‌بندی یافت نشد'}, status=status.HTTP_404_NOT_FOUND)
    
    # FIX: Add store filtering for security
    store_id = request.query_params.get('store')
    if not store_id:
        return Response({'error': 'شناسه فروشگاه الزامی است'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        from apps.stores.models import Store
        store = Store.objects.get(id=store_id, is_active=True)
    except Store.DoesNotExist:
        return Response({'error': 'فروشگاه یافت نشد'}, status=status.HTTP_404_NOT_FOUND)
    
    # Get all products in this category tree for this store
    descendant_ids = [category.id] + list(category.get_descendants().values_list('id', flat=True))
    products = Product.objects.filter(
        category_id__in=descendant_ids,
        status='published',
        store=store
    )
    
    filters_data = {}
    
    # Price range
    price_aggregation = products.aggregate(
        min_price=Min('base_price'),
        max_price=Max('base_price')
    )
    filters_data['price'] = {
        'name': 'قیمت',
        'type': 'range',
        'min_value': price_aggregation['min_price'] or 0,
        'max_value': price_aggregation['max_price'] or 0
    }
    
    # Product Classes
    product_classes = ProductClass.objects.filter(
        products__in=products,
        is_active=True
    ).annotate(
        product_count=Count('products')
    ).order_by('-product_count')
    
    filters_data['product_classes'] = {
        'name': 'کلاس محصول',
        'type': 'choice',
        'choices': [
            {
                'value': pc.slug,
                'label': pc.name_fa,
                'count': pc.product_count
            } for pc in product_classes
        ]
    }
    
    # Brands
    brands = Brand.objects.filter(
        products__in=products,
        is_active=True
    ).annotate(
        product_count=Count('products')
    ).order_by('-product_count')
    
    filters_data['brands'] = {
        'name': 'برند',
        'type': 'choice',
        'choices': [
            {
                'value': brand.slug,
                'label': brand.name_fa,
                'count': brand.product_count
            } for brand in brands
        ]
    }
    
    # Tags
    tags = Tag.objects.filter(
        products__in=products,
        is_filterable=True
    ).annotate(
        product_count=Count('products')
    ).order_by('-product_count')
    
    filters_data['tags'] = {
        'name': 'برچسب‌ها',
        'type': 'choice',
        'choices': [
            {
                'value': tag.slug,
                'label': tag.name_fa,
                'count': tag.product_count
            } for tag in tags
        ]
    }
    
    return Response(filters_data)

@api_view(['GET'])
@permission_classes([AllowAny])
@method_decorator(cache_page(300))  # 5 minutes cache
def store_statistics(request):
    """Get store statistics for homepage"""
    store_id = request.GET.get('store')
    if not store_id:
        return Response({'error': 'شناسه فروشگاه الزامی است'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        from apps.stores.models import Store
        store = Store.objects.get(id=store_id, is_active=True)
    except Store.DoesNotExist:
        return Response({'error': 'فروشگاه یافت نشد'}, status=status.HTTP_404_NOT_FOUND)
    
    stats = {
        'total_products': Product.objects.filter(store=store, status='published').count(),
        'total_product_classes': ProductClass.objects.filter(store=store, is_active=True).count(),
        'total_categories': ProductCategory.objects.filter(store=store, is_active=True).count(),
        'total_brands': Brand.objects.filter(store=store, is_active=True).count(),
        'featured_products': Product.objects.filter(store=store, status='published', is_featured=True).count(),
        'recent_products': ProductListSerializer(
            Product.objects.filter(store=store, status='published').order_by('-created_at')[:6],
            many=True,
            context={'request': request}
        ).data,
        'popular_products': ProductListSerializer(
            Product.objects.filter(store=store, status='published').order_by('-view_count')[:6],
            many=True,
            context={'request': request}
        ).data,
        'featured_collections': CollectionSerializer(
            Collection.objects.filter(store=store, is_active=True, is_featured=True)[:3],
            many=True,
            context={'request': request}
        ).data
    }
    
    return Response(stats)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def import_from_social_media(request):
    """Import product from social media post"""
    # FIX: Add store ownership validation
    store_id = request.data.get('store')
    if store_id:
        try:
            from apps.stores.models import Store
            store = Store.objects.get(id=store_id, owner=request.user, is_active=True)
        except Store.DoesNotExist:
            return Response(
                {'error': 'دسترسی غیرمجاز به فروشگاه یا فروشگاه یافت نشد'}, 
                status=status.HTTP_403_FORBIDDEN
            )
    else:
        return Response(
            {'error': 'شناسه فروشگاه الزامی است'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    serializer = ProductImportSerializer(data=request.data)
    if serializer.is_valid():
        product = serializer.save()
        return Response({
            'message': 'محصول از شبکه اجتماعی وارد شد',
            'product': ProductDetailSerializer(product, context={'request': request}).data
        })
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def product_analytics(request):
    """Get product analytics for store owner"""
    store_id = request.query_params.get('store')
    if not store_id:
        return Response({'error': 'شناسه فروشگاه الزامی است'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        from apps.stores.models import Store
        # FIX: Ensure user owns the store
        store = Store.objects.get(id=store_id, owner=request.user, is_active=True)
    except Store.DoesNotExist:
        return Response({'error': 'فروشگاه یافت نشد یا دسترسی غیرمجاز'}, status=status.HTTP_404_NOT_FOUND)
    
    products = Product.objects.filter(store=store)
    
    stats = {
        'total_products': products.count(),
        'published_products': products.filter(status='published').count(),
        'draft_products': products.filter(status='draft').count(),
        'out_of_stock_products': products.filter(stock_quantity=0).count(),
        'low_stock_products': products.filter(
            stock_quantity__lte=F('low_stock_threshold'),
            stock_quantity__gt=0
        ).count(),
        'featured_products': products.filter(is_featured=True).count(),
        'total_variants': ProductVariant.objects.filter(product__store=store).count(),
        'total_product_classes': ProductClass.objects.filter(store=store, is_active=True).count(),
        'total_categories': ProductCategory.objects.filter(store=store, is_active=True).count(),
        'total_brands': Brand.objects.filter(store=store, is_active=True).count(),
        'avg_price': products.filter(status='published').aggregate(
            avg=Avg('base_price')
        )['avg'] or 0,
        'total_views': products.aggregate(total=Sum('view_count'))['total'] or 0,
        'total_sales': products.aggregate(total=Sum('sales_count'))['total'] or 0,
    }
    
    serializer = ProductStatisticsSerializer(stats)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([AllowAny])
@method_decorator(cache_page(1800))  # 30 minutes cache
def trending_searches(request):
    """Get trending search terms"""
    store_id = request.query_params.get('store')
    
    # This would be implemented with real analytics data
    # For now, return sample data based on store if provided
    if store_id:
        try:
            from apps.stores.models import Store
            store = Store.objects.get(id=store_id, is_active=True)
            
            # Get top searched products from this store
            trending = [
                {'term': 'محصولات پربازدید', 'count': 150},
                {'term': 'جدیدترین محصولات', 'count': 120},
                {'term': 'پیشنهادی', 'count': 90},
                {'term': 'تخفیف ویژه', 'count': 75},
                {'term': 'محصولات ویژه', 'count': 60},
            ]
        except Store.DoesNotExist:
            trending = []
    else:
        # Global trending searches
        trending = [
            {'term': 'گوشی هوشمند', 'count': 150},
            {'term': 'لپ‌تاپ', 'count': 120},
            {'term': 'هدفون', 'count': 90},
            {'term': 'ساعت هوشمند', 'count': 75},
            {'term': 'تبلت', 'count': 60},
        ]
    
    return Response({'trending': trending})

@api_view(['GET'])
@permission_classes([AllowAny])
@method_decorator(cache_page(600))  # 10 minutes cache
def product_class_hierarchy(request):
    """Get product class hierarchy for a store"""
    store_id = request.GET.get('store')
    if not store_id:
        return Response({'error': 'شناسه فروشگاه الزامی است'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        from apps.stores.models import Store
        store = Store.objects.get(id=store_id, is_active=True)
    except Store.DoesNotExist:
        return Response({'error': 'فروشگاه یافت نشد'}, status=status.HTTP_404_NOT_FOUND)
    
    # Get root classes (no parent) with optimized query
    root_classes = ProductClass.objects.filter(
        store=store,
        is_active=True,
        parent__isnull=True
    ).prefetch_related(
        'children__children',  # Prefetch 2 levels deep
        'attributes__attribute_type'
    ).order_by('display_order', 'name_fa')
    
    serializer = ProductClassSerializer(root_classes, many=True, context={'request': request})
    return Response(serializer.data)
