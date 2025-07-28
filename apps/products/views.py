from rest_framework import generics, filters, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django_filters import rest_framework as django_filters
from django.db.models import Q, Count, Min, Max, Avg, F
from django.core.cache import cache
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from .models import *
from .serializers import *
from .filters import ProductFilter

# Category Views
class CategoryListView(generics.ListAPIView):
    """List all categories with hierarchy"""
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        store_id = self.request.query_params.get('store')
        queryset = ProductCategory.objects.filter(
            is_active=True,
            parent__isnull=True  # Only root categories
        )
        if store_id:
            queryset = queryset.filter(store_id=store_id)
        return queryset.prefetch_related('children', 'attributes__attribute_type')

class CategoryDetailView(generics.RetrieveAPIView):
    """Get category details with all attributes and subcategories"""
    serializer_class = CategorySerializer
    lookup_field = 'slug'
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        return ProductCategory.objects.filter(is_active=True)

@api_view(['GET'])
@permission_classes([AllowAny])
def category_filters(request, slug):
    """Get available filters for a category"""
    try:
        category = ProductCategory.objects.get(slug=slug, is_active=True)
    except ProductCategory.DoesNotExist:
        return Response({'error': 'Category not found'}, status=404)
    
    # Get all products in this category tree
    descendant_ids = [category.id] + list(category.get_descendants().values_list('id', flat=True))
    products = Product.objects.filter(
        category_id__in=descendant_ids,
        status='published'
    )
    
    filters_data = {}
    
    # Price range
    price_range = products.aggregate(
        min_price=Min('base_price'),
        max_price=Max('base_price')
    )
    filters_data['price'] = {
        'name': 'قیمت',
        'type': 'range',
        'min_value': price_range['min_price'] or 0,
        'max_value': price_range['max_price'] or 0
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
    attributes = category.get_all_attributes()
    for attr in attributes:
        if attr.is_filterable:
            attr_values = ProductAttributeValue.objects.filter(
                product__in=products,
                attribute=attr
            ).values('value_text').annotate(
                count=Count('value_text')
            ).order_by('-count')
            
            filters_data[f'attr_{attr.attribute_type.name}'] = {
                'name': attr.attribute_type.name_fa,
                'type': attr.attribute_type.filter_type,
                'choices': [
                    {
                        'value': val['value_text'],
                        'label': val['value_text'],
                        'count': val['count']
                    } for val in attr_values
                ]
            }
    
    return Response(filters_data)

# Brand Views
class BrandListView(generics.ListAPIView):
    """List all brands"""
    serializer_class = BrandSerializer
    permission_classes = [AllowAny]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name_fa', 'name']
    ordering_fields = ['name_fa', 'product_count', 'created_at']
    ordering = ['-product_count', 'name_fa']
    
    def get_queryset(self):
        store_id = self.request.query_params.get('store')
        queryset = Brand.objects.filter(is_active=True)
        if store_id:
            queryset = queryset.filter(store_id=store_id)
        
        # Filter by category if specified
        category_slug = self.request.query_params.get('category')
        if category_slug:
            try:
                category = ProductCategory.objects.get(slug=category_slug)
                descendant_ids = [category.id] + list(category.get_descendants().values_list('id', flat=True))
                queryset = queryset.filter(products__category_id__in=descendant_ids).distinct()
            except ProductCategory.DoesNotExist:
                pass
        
        return queryset

class BrandDetailView(generics.RetrieveAPIView):
    """Get brand details"""
    serializer_class = BrandSerializer
    lookup_field = 'slug'
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        return Brand.objects.filter(is_active=True)

# Product Views
class ProductFilter(django_filters.FilterSet):
    """Advanced product filtering"""
    min_price = django_filters.NumberFilter(field_name="base_price", lookup_expr='gte')
    max_price = django_filters.NumberFilter(field_name="base_price", lookup_expr='lte')
    category = django_filters.CharFilter(method='filter_category')
    brand = django_filters.CharFilter(field_name="brand__slug")
    tags = django_filters.CharFilter(method='filter_tags')
    in_stock = django_filters.BooleanFilter(method='filter_in_stock')
    
    class Meta:
        model = Product
        fields = ['status', 'product_type', 'is_featured']
    
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

class ProductListView(generics.ListAPIView):
    """List products with advanced filtering and search"""
    serializer_class = ProductListSerializer
    permission_classes = [AllowAny]
    filterset_class = ProductFilter
    filter_backends = [
        django_filters.DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter
    ]
    search_fields = ['name_fa', 'name', 'description', 'brand__name_fa', 'sku']
    ordering_fields = [
        'created_at', 'base_price', 'view_count', 'sales_count', 'rating_average'
    ]
    ordering = ['-created_at']
    
    def get_queryset(self):
        store_id = self.request.query_params.get('store')
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
        
        return queryset.select_related('brand', 'category').prefetch_related(
            'tags', 'images', 'variants'
        ).distinct()

class ProductDetailView(generics.RetrieveAPIView):
    """Get product details with variants and attributes"""
    serializer_class = ProductDetailSerializer
    lookup_field = 'slug'
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        return Product.objects.filter(status='published').select_related(
            'brand', 'category'
        ).prefetch_related(
            'variants__attribute_values__attribute__attribute_type',
            'attribute_values__attribute__attribute_type',
            'images',
            'tags',
            'related_products'
        )
    
    def retrieve(self, request, *args, **kwargs):
        """Increment view count when retrieving product"""
        instance = self.get_object()
        instance.increment_view_count()
        return super().retrieve(request, *args, **kwargs)

@api_view(['GET'])
@permission_classes([AllowAny])
def product_search(request):
    """Advanced product search with autocomplete"""
    query = request.GET.get('q', '').strip()
    store_id = request.GET.get('store')
    limit = int(request.GET.get('limit', 10))
    
    if not query:
        return Response({'results': []})
    
    # Search products
    products = Product.objects.filter(status='published')
    if store_id:
        products = products.filter(store_id=store_id)
    
    # Search in multiple fields with different weights
    products = products.filter(
        Q(name_fa__icontains=query) |
        Q(name__icontains=query) |
        Q(description__icontains=query) |
        Q(brand__name_fa__icontains=query) |
        Q(sku__icontains=query) |
        Q(tags__name_fa__icontains=query)
    ).distinct()[:limit]
    
    # Also search categories
    categories = ProductCategory.objects.filter(
        is_active=True,
        name_fa__icontains=query
    )
    if store_id:
        categories = categories.filter(store_id=store_id)
    categories = categories[:5]
    
    # Also search brands
    brands = Brand.objects.filter(
        is_active=True,
        name_fa__icontains=query
    )
    if store_id:
        brands = brands.filter(store_id=store_id)
    brands = brands[:5]
    
    results = {
        'products': ProductListSerializer(products, many=True).data,
        'categories': CategorySerializer(categories, many=True).data,
        'brands': BrandSerializer(brands, many=True).data,
        'total_found': products.count()
    }
    
    return Response(results)

@api_view(['GET'])
@permission_classes([AllowAny])
def product_recommendations(request, product_id):
    """Get product recommendations"""
    try:
        product = Product.objects.get(id=product_id, status='published')
    except Product.DoesNotExist:
        return Response({'error': 'Product not found'}, status=404)
    
    # Get related products by:
    # 1. Same category
    # 2. Same brand
    # 3. Similar tags
    # 4. Similar price range
    
    recommendations = Product.objects.filter(
        status='published',
        store=product.store
    ).exclude(id=product.id)
    
    # Prioritize same category
    same_category = recommendations.filter(category=product.category)[:4]
    
    # Same brand
    if product.brand:
        same_brand = recommendations.filter(brand=product.brand).exclude(
            id__in=[p.id for p in same_category]
        )[:2]
    else:
        same_brand = []
    
    # Similar tags
    if product.tags.exists():
        similar_tags = recommendations.filter(
            tags__in=product.tags.all()
        ).exclude(
            id__in=[p.id for p in same_category] + [p.id for p in same_brand]
        ).distinct()[:2]
    else:
        similar_tags = []
    
    # Combine recommendations
    all_recommendations = list(same_category) + list(same_brand) + list(similar_tags)
    
    return Response(ProductListSerializer(all_recommendations[:8], many=True).data)

# Collection Views
class CollectionListView(generics.ListAPIView):
    """List all collections"""
    serializer_class = CollectionSerializer
    permission_classes = [AllowAny]
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

class CollectionDetailView(generics.RetrieveAPIView):
    """Get collection details with products"""
    serializer_class = CollectionDetailSerializer
    lookup_field = 'slug'
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        return Collection.objects.filter(is_active=True)

# Statistics and Analytics Views
@api_view(['GET'])
@permission_classes([AllowAny])
@method_decorator(cache_page(300))  # Cache for 5 minutes
def store_statistics(request):
    """Get store statistics for homepage"""
    store_id = request.GET.get('store')
    if not store_id:
        return Response({'error': 'Store ID required'}, status=400)
    
    try:
        store = Store.objects.get(id=store_id)
    except Store.DoesNotExist:
        return Response({'error': 'Store not found'}, status=404)
    
    # Get statistics
    stats = {
        'total_products': Product.objects.filter(store=store, status='published').count(),
        'total_categories': ProductCategory.objects.filter(store=store, is_active=True).count(),
        'total_brands': Brand.objects.filter(store=store, is_active=True).count(),
        'featured_products': Product.objects.filter(store=store, status='published', is_featured=True).count(),
        'recent_products': ProductListSerializer(
            Product.objects.filter(store=store, status='published').order_by('-created_at')[:6],
            many=True
        ).data,
        'popular_products': ProductListSerializer(
            Product.objects.filter(store=store, status='published').order_by('-view_count')[:6],
            many=True
        ).data,
        'featured_collections': CollectionSerializer(
            Collection.objects.filter(store=store, is_active=True, is_featured=True)[:3],
            many=True
        ).data
    }
    
    return Response(stats)

@api_view(['GET'])
@permission_classes([AllowAny])
def trending_searches(request):
    """Get trending searches (cached)"""
    store_id = request.GET.get('store')
    cache_key = f"trending_searches_{store_id}" if store_id else "trending_searches_global"
    
    trending = cache.get(cache_key)
    if not trending:
        # This would typically come from search analytics
        # For now, return static trending terms
        trending = [
            'تی شرت',
            'کفش ورزشی',
            'جواهرات طلا',
            'کیف زنانه',
            'ساعت مچی',
            'عطر',
            'لباس مجلسی',
            'اکسسوری'
        ]
        cache.set(cache_key, trending, 3600)  # Cache for 1 hour
    
    return Response({'trending_searches': trending})

# Tag Views
class TagListView(generics.ListAPIView):
    """List all tags"""
    serializer_class = TagSerializer
    permission_classes = [AllowAny]
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

# Variant management for admin
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_product_variants(request):
    """Generate product variants based on variant-creating attributes"""
    product_id = request.data.get('product_id')
    attribute_combinations = request.data.get('attributes', [])
    
    try:
        product = Product.objects.get(id=product_id, store__owner=request.user)
    except Product.DoesNotExist:
        return Response({'error': 'Product not found'}, status=404)
    
    if product.product_type != 'variable':
        return Response({'error': 'Product must be variable type'}, status=400)
    
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
            price=product.base_price,
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
        'message': f'{len(created_variants)} variants created successfully',
        'variants': ProductVariantSerializer(created_variants, many=True).data
    })
