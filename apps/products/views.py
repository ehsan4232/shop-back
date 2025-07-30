from rest_framework import generics, filters, status, viewsets
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
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

class ProductFilter(django_filters.FilterSet):
    """Advanced product filtering"""
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
        """Filter by minimum effective price"""
        return queryset.filter(
            Q(base_price__gte=value) |
            Q(base_price__isnull=True, product_class__base_price__gte=value)
        )
    
    def filter_max_price(self, queryset, name, value):
        """Filter by maximum effective price"""
        return queryset.filter(
            Q(base_price__lte=value) |
            Q(base_price__isnull=True, product_class__base_price__lte=value)
        )
    
    def filter_product_class(self, queryset, name, value):
        """Filter by product class including descendants"""
        try:
            product_class = ProductClass.objects.get(slug=value)
            descendant_ids = [product_class.id] + list(product_class.get_descendants().values_list('id', flat=True))
            return queryset.filter(product_class_id__in=descendant_ids)
        except ProductClass.DoesNotExist:
            return queryset.none()
    
    def filter_category(self, queryset, name, value):
        """Filter by category including descendants"""
        try:
            category = ProductCategory.objects.get(slug=value)
            descendant_ids = [category.id] + list(category.get_descendants().values_list('id', flat=True))
            return queryset.filter(category_id__in=descendant_ids)
        except ProductCategory.DoesNotExist:
            return queryset.none()
    
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

class AttributeTypeViewSet(viewsets.ModelViewSet):
    """Attribute type management ViewSet"""
    serializer_class = AttributeTypeSerializer
    permission_classes = [AllowAny]
    lookup_field = 'slug'
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name_fa', 'name']
    ordering_fields = ['display_order', 'name_fa', 'created_at']
    ordering = ['display_order', 'name_fa']
    
    def get_queryset(self):
        return AttributeType.objects.all()

class TagViewSet(viewsets.ModelViewSet):
    """Tag management ViewSet"""
    serializer_class = TagSerializer
    permission_classes = [AllowAny]
    lookup_field = 'slug'
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['usage_count', 'name_fa']
    ordering = ['-usage_count', 'name_fa']
    
    def get_queryset(self):
        store_id = self.request.query_params.get('store')
        queryset = Tag.objects.all()
        if store_id:
            queryset = queryset.filter(store_id=store_id)
        
        tag_type = self.request.query_params.get('type')
        if tag_type:
            queryset = queryset.filter(tag_type=tag_type)
        
        featured_only = self.request.query_params.get('featured')
        if featured_only == 'true':
            queryset = queryset.filter(is_featured=True)
        
        return queryset

class ProductClassViewSet(viewsets.ModelViewSet):
    """Product class hierarchy management ViewSet"""
    serializer_class = ProductClassSerializer
    permission_classes = [AllowAny]
    lookup_field = 'slug'
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name_fa', 'name']
    ordering_fields = ['display_order', 'name_fa', 'created_at']
    ordering = ['display_order', 'name_fa']
    
    def get_queryset(self):
        store_id = self.request.query_params.get('store')
        queryset = ProductClass.objects.filter(is_active=True)
        if store_id:
            queryset = queryset.filter(store_id=store_id)
        
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
        
        return queryset.prefetch_related('children', 'attributes__attribute_type')

class CategoryViewSet(viewsets.ModelViewSet):
    """Category management ViewSet"""
    serializer_class = ProductCategorySerializer
    permission_classes = [AllowAny]
    lookup_field = 'slug'
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name_fa', 'name']
    ordering_fields = ['display_order', 'name_fa', 'created_at']
    ordering = ['display_order', 'name_fa']
    
    def get_queryset(self):
        store_id = self.request.query_params.get('store')
        queryset = ProductCategory.objects.filter(is_active=True)
        if store_id:
            queryset = queryset.filter(store_id=store_id)
        
        # Filter by parent
        parent_id = self.request.query_params.get('parent')
        if parent_id:
            if parent_id == 'null':
                queryset = queryset.filter(parent__isnull=True)
            else:
                queryset = queryset.filter(parent_id=parent_id)
        
        return queryset.prefetch_related('children', 'attributes__attribute_type')

class BrandViewSet(viewsets.ModelViewSet):
    """Brand management ViewSet"""
    serializer_class = BrandSerializer
    permission_classes = [AllowAny]
    lookup_field = 'slug'
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name_fa', 'name']
    ordering_fields = ['name_fa', 'product_count', 'created_at']
    ordering = ['-product_count', 'name_fa']
    
    def get_queryset(self):
        store_id = self.request.query_params.get('store')
        queryset = Brand.objects.filter(is_active=True)
        if store_id:
            queryset = queryset.filter(store_id=store_id)
        return queryset

class ProductViewSet(viewsets.ModelViewSet):
    """Product management ViewSet"""
    permission_classes = [AllowAny]
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
        store_id = self.request.query_params.get('store')
        
        if self.action == 'list':
            queryset = Product.objects.filter(status='published')
        else:
            # For admin actions, include all statuses
            if self.request.user.is_authenticated and self.request.user.is_store_owner:
                queryset = Product.objects.all()
            else:
                queryset = Product.objects.filter(status='published')
        
        if store_id:
            queryset = queryset.filter(store_id=store_id)
        
        # Dynamic attribute filtering
        for key, value in self.request.query_params.items():
            if key.startswith('attr_') and value:
                attr_name = key[5:]  # Remove 'attr_' prefix
                queryset = queryset.filter(
                    attribute_values__attribute__attribute_type__name=attr_name,
                    attribute_values__value_text=value
                )
        
        return queryset.select_related('brand', 'category', 'product_class').prefetch_related(
            'tags', 'images', 'variants'
        ).distinct()
    
    def retrieve(self, request, *args, **kwargs):
        """Increment view count when retrieving product"""
        instance = self.get_object()
        instance.increment_view_count()
        return super().retrieve(request, *args, **kwargs)
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def bulk_create(self, request):
        """Bulk create products"""
        serializer = BulkProductCreateSerializer(data=request.data)
        if serializer.is_valid():
            products = serializer.save()
            return Response({
                'message': f'{len(products)} محصول با موفقیت ایجاد شد',
                'products': ProductListSerializer(products, many=True).data
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def create_variants(self, request, slug=None):
        """Generate product variants"""
        product = self.get_object()
        if product.store.owner != request.user:
            return Response({'error': 'دسترسی غیرمجاز'}, status=status.HTTP_403_FORBIDDEN)
        
        attribute_combinations = request.data.get('attributes', [])
        
        # Generate all combinations
        import itertools
        
        variant_attrs = []
        for attr_data in attribute_combinations:
            attr = ProductAttribute.objects.get(id=attr_data['attribute_id'])
            values = attr_data['values']
            variant_attrs.append([(attr, value) for value in values])
        
        # Create variants for all combinations
        created_variants = []
        for combination in itertools.product(*variant_attrs):
            # Create variant
            variant = ProductVariant.objects.create(
                product=product,
                price=product.get_effective_price(),
                stock_quantity=0
            )
            
            # Set attribute values
            for attr, value in combination:
                ProductAttributeValue.objects.create(
                    variant=variant,
                    attribute=attr,
                    value_text=value
                )
            
            created_variants.append(variant)
        
        return Response({
            'message': f'{len(created_variants)} نوع محصول ایجاد شد',
            'variants': ProductVariantSerializer(created_variants, many=True).data
        })
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        """Advanced product search"""
        serializer = ProductSearchSerializer(data=request.query_params)
        if serializer.is_valid():
            query = serializer.validated_data.get('query', '')
            store_id = request.query_params.get('store')
            limit = int(request.query_params.get('limit', 10))
            
            if not query:
                return Response({'results': []})
            
            # Search products
            products = Product.objects.filter(status='published')
            if store_id:
                products = products.filter(store_id=store_id)
            
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
            
            return Response({
                'products': ProductListSerializer(products, many=True).data,
                'total_found': products.count()
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def recommendations(self, request, slug=None):
        """Get product recommendations"""
        product = self.get_object()
        
        recommendations = Product.objects.filter(
            status='published',
            store=product.store
        ).exclude(id=product.id)
        
        # Same product class
        same_class = recommendations.filter(product_class=product.product_class)[:4]
        
        # Same category
        same_category = recommendations.filter(category=product.category).exclude(
            id__in=[p.id for p in same_class]
        )[:4]
        
        # Same brand
        if product.brand:
            same_brand = recommendations.filter(brand=product.brand).exclude(
                id__in=[p.id for p in same_class] + [p.id for p in same_category]
            )[:2]
        else:
            same_brand = []
        
        # Similar tags
        if product.tags.exists():
            similar_tags = recommendations.filter(
                tags__in=product.tags.all()
            ).exclude(
                id__in=[p.id for p in same_class] + [p.id for p in same_category] + [p.id for p in same_brand]
            ).distinct()[:2]
        else:
            similar_tags = []
        
        all_recommendations = list(same_class) + list(same_category) + list(same_brand) + list(similar_tags)
        
        return Response(ProductListSerializer(all_recommendations[:8], many=True).data)

class CollectionViewSet(viewsets.ModelViewSet):
    """Collection management ViewSet"""
    serializer_class = CollectionSerializer
    permission_classes = [AllowAny]
    lookup_field = 'slug'
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['display_order', 'name_fa', 'created_at']
    ordering = ['display_order', 'name_fa']
    
    def get_queryset(self):
        store_id = self.request.query_params.get('store')
        queryset = Collection.objects.filter(is_active=True)
        if store_id:
            queryset = queryset.filter(store_id=store_id)
        
        featured_only = self.request.query_params.get('featured')
        if featured_only == 'true':
            queryset = queryset.filter(is_featured=True)
        
        return queryset

@api_view(['GET'])
@permission_classes([AllowAny])
def category_filters(request, slug):
    """Get available filters for a category"""
    try:
        category = ProductCategory.objects.get(slug=slug, is_active=True)
    except ProductCategory.DoesNotExist:
        return Response({'error': 'دسته‌بندی یافت نشد'}, status=status.HTTP_404_NOT_FOUND)
    
    # Get all products in this category tree
    descendant_ids = [category.id] + list(category.get_descendants().values_list('id', flat=True))
    products = Product.objects.filter(
        category_id__in=descendant_ids,
        status='published'
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
    
    # Dynamic attributes
    attributes = ProductAttribute.objects.filter(
        category__in=category.get_descendants(include_self=True)
    ).select_related('attribute_type')
    
    for attr in attributes:
        # Get distinct values for this attribute
        values = ProductAttributeValue.objects.filter(
            attribute=attr,
            product__in=products
        ).values_list('value_text', flat=True).distinct()
        
        if values:
            filters_data[f'attr_{attr.attribute_type.name}'] = {
                'name': attr.attribute_type.name_fa,
                'type': 'choice',
                'choices': [{'value': value, 'label': value} for value in values if value]
            }
    
    return Response(filters_data)

@api_view(['GET'])
@permission_classes([AllowAny])
@method_decorator(cache_page(300))
def store_statistics(request):
    """Get store statistics for homepage"""
    store_id = request.GET.get('store')
    if not store_id:
        return Response({'error': 'شناسه فروشگاه الزامی است'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        from apps.stores.models import Store
        store = Store.objects.get(id=store_id)
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
            many=True
        ).data
    }
    
    return Response(stats)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def import_from_social_media(request):
    """Import product from social media post"""
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
        store = Store.objects.get(id=store_id, owner=request.user)
    except Store.DoesNotExist:
        return Response({'error': 'فروشگاه یافت نشد'}, status=status.HTTP_404_NOT_FOUND)
    
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
def trending_searches(request):
    """Get trending search terms"""
    # This would be implemented with analytics data
    # For now, return sample data
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
def product_class_hierarchy(request):
    """Get product class hierarchy for a store"""
    store_id = request.GET.get('store')
    if not store_id:
        return Response({'error': 'شناسه فروشگاه الزامی است'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        from apps.stores.models import Store
        store = Store.objects.get(id=store_id)
    except Store.DoesNotExist:
        return Response({'error': 'فروشگاه یافت نشد'}, status=status.HTTP_404_NOT_FOUND)
    
    # Get root classes (no parent)
    root_classes = ProductClass.objects.filter(
        store=store,
        is_active=True,
        parent__isnull=True
    ).order_by('display_order', 'name_fa')
    
    serializer = ProductClassSerializer(root_classes, many=True, context={'request': request})
    return Response(serializer.data)
