"""
Product-related services for enhanced functionality
Consolidates business logic and complex operations
"""

from django.db import transaction
from django.core.cache import cache
from django.db.models import Q, Count, Avg, Sum, F
from typing import Dict, Any, List, Optional
from decimal import Decimal
import uuid

from .models import (
    Product, ProductClass, ProductCategory, Brand, Tag,
    ProductVariant, ProductAttributeValue, ProductImage
)


class ProductCreationService:
    """
    Service for creating products with comprehensive validation and setup
    """
    
    @staticmethod
    @transaction.atomic
    def create_product_from_data(store, product_data: Dict[str, Any]) -> Product:
        """
        Create a product with all related data in a single transaction
        """
        # Extract related data
        attribute_values_data = product_data.pop('attribute_values', [])
        variants_data = product_data.pop('variants_data', [])
        tags_data = product_data.pop('tags', [])
        images_data = product_data.pop('images', [])
        
        # Set store
        product_data['store'] = store
        
        # Create the product
        product = Product.objects.create(**product_data)
        
        # Add tags
        if tags_data:
            product.tags.set(tags_data)
        
        # Create attribute values
        for attr_data in attribute_values_data:
            ProductAttributeValue.objects.create(
                product=product,
                **attr_data
            )
        
        # Create variants for variable products
        if product.product_type == 'variable' and variants_data:
            ProductCreationService._create_variants(product, variants_data)
        
        # Create images
        for img_data in images_data:
            ProductImage.objects.create(
                product=product,
                **img_data
            )
        
        # Update related counts
        product.category.update_product_count()
        product.product_class.update_product_count()
        if product.brand:
            product.brand.update_product_count()
        
        return product
    
    @staticmethod
    def create_product_from_social_media(store, product_class, category, social_content: Dict, additional_data: Dict = None):
        """
        Create a product from social media content
        """
        product_data = {
            'store': store,
            'product_class': product_class,
            'category': category,
            'name': social_content.get('title', 'محصول وارداتی'),
            'name_fa': social_content.get('title_fa', 'محصول وارداتی'),
            'description': social_content.get('description', ''),
            'short_description': social_content.get('summary', ''),
            'base_price': social_content.get('suggested_price'),
            'imported_from_social': True,
            'social_media_source': social_content.get('platform'),
            'social_media_post_id': social_content.get('post_id'),
            'status': 'draft',  # Start as draft for review
        }
        
        # Merge additional data
        if additional_data:
            product_data.update(additional_data)
        
        # Handle images from social media
        images_data = []
        for img_url in social_content.get('images', []):
            images_data.append({
                'image': img_url,  # This would need proper file handling
                'imported_from_social': True,
                'social_media_url': img_url
            })
        
        product_data['images'] = images_data
        
        return ProductCreationService.create_product_from_data(store, product_data)
    
    @staticmethod
    def _create_variants(product: Product, variants_data: List[Dict]):
        """
        Create product variants with attribute values
        """
        for variant_data in variants_data:
            attributes = variant_data.pop('attributes', {})
            
            variant = ProductVariant.objects.create(
                product=product,
                **variant_data
            )
            
            # Create attribute values for variant
            for attr_name, attr_value in attributes.items():
                try:
                    from .models import ProductAttribute
                    attribute = ProductAttribute.objects.get(
                        category=product.category,
                        attribute_type__name=attr_name
                    )
                    
                    ProductAttributeValue.objects.create(
                        variant=variant,
                        attribute=attribute,
                        value_text=str(attr_value)
                    )
                except ProductAttribute.DoesNotExist:
                    continue


class ProductSearchService:
    """
    Advanced product search and filtering service
    """
    
    @staticmethod
    def search_products(store, query: str, filters: Dict = None, limit: int = 50) -> Dict:
        """
        Comprehensive product search with caching
        """
        cache_key = f"product_search_{store.id}_{hash(query)}_{hash(str(filters))}_{limit}"
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
        
        # Start with store products
        products = Product.objects.filter(
            store=store,
            status='published'
        ).select_related(
            'brand', 'category', 'product_class'
        ).prefetch_related(
            'tags', 'images'
        )
        
        # Apply search query
        if query and len(query) >= 2:
            products = products.filter(
                Q(name_fa__icontains=query) |
                Q(name__icontains=query) |
                Q(description__icontains=query) |
                Q(brand__name_fa__icontains=query) |
                Q(sku__icontains=query) |
                Q(tags__name_fa__icontains=query) |
                Q(product_class__name_fa__icontains=query)
            ).distinct()
        
        # Apply filters
        if filters:
            products = ProductSearchService._apply_filters(products, filters)
        
        # Limit results
        products = products[:limit]
        
        result = {
            'products': list(products),
            'total_found': products.count(),
            'query': query,
            'filters': filters or {}
        }
        
        # Cache for 5 minutes
        cache.set(cache_key, result, timeout=300)
        return result
    
    @staticmethod
    def _apply_filters(queryset, filters: Dict):
        """
        Apply various filters to product queryset
        """
        # Price range
        if 'min_price' in filters:
            queryset = queryset.filter(
                Q(base_price__gte=filters['min_price']) |
                Q(base_price__isnull=True, product_class__base_price__gte=filters['min_price'])
            )
        
        if 'max_price' in filters:
            queryset = queryset.filter(
                Q(base_price__lte=filters['max_price']) |
                Q(base_price__isnull=True, product_class__base_price__lte=filters['max_price'])
            )
        
        # Category filter with descendants
        if 'category' in filters:
            try:
                category = ProductCategory.objects.get(slug=filters['category'])
                descendant_ids = [category.id] + list(
                    category.get_descendants().values_list('id', flat=True)
                )
                queryset = queryset.filter(category_id__in=descendant_ids)
            except ProductCategory.DoesNotExist:
                pass
        
        # Product class filter with descendants
        if 'product_class' in filters:
            try:
                product_class = ProductClass.objects.get(slug=filters['product_class'])
                descendant_ids = [product_class.id] + list(
                    product_class.get_descendants().values_list('id', flat=True)
                )
                queryset = queryset.filter(product_class_id__in=descendant_ids)
            except ProductClass.DoesNotExist:
                pass
        
        # Brand filter
        if 'brand' in filters:
            queryset = queryset.filter(brand__slug=filters['brand'])
        
        # Tags filter
        if 'tags' in filters:
            tag_slugs = filters['tags'] if isinstance(filters['tags'], list) else [filters['tags']]
            queryset = queryset.filter(tags__slug__in=tag_slugs).distinct()
        
        # Stock filter
        if filters.get('in_stock'):
            queryset = queryset.filter(
                Q(product_type='simple', stock_quantity__gt=0) |
                Q(product_type='variable', variants__stock_quantity__gt=0)
            ).distinct()
        
        # Featured filter
        if filters.get('is_featured'):
            queryset = queryset.filter(is_featured=True)
        
        return queryset


class ProductAnalyticsService:
    """
    Service for product analytics and statistics
    """
    
    @staticmethod
    def get_store_product_analytics(store) -> Dict:
        """
        Get comprehensive product analytics for a store
        """
        cache_key = f"store_product_analytics_{store.id}"
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
        
        products = Product.objects.filter(store=store)
        
        analytics = {
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
            'total_views': products.aggregate(total=Sum('view_count'))['total'] or 0,
            'total_sales': products.aggregate(total=Sum('sales_count'))['total'] or 0,
            'avg_price': products.filter(status='published').aggregate(
                avg=Avg('base_price')
            )['avg'] or 0,
            'avg_rating': products.filter(status='published').aggregate(
                avg=Avg('rating_average')
            )['avg'] or 0,
        }
        
        # Top performing products
        analytics['top_viewed'] = list(
            products.filter(status='published')
            .order_by('-view_count')[:5]
            .values('id', 'name_fa', 'view_count')
        )
        
        analytics['top_selling'] = list(
            products.filter(status='published')
            .order_by('-sales_count')[:5]
            .values('id', 'name_fa', 'sales_count')
        )
        
        # Cache for 10 minutes
        cache.set(cache_key, analytics, timeout=600)
        return analytics
    
    @staticmethod
    def get_product_performance(product: Product) -> Dict:
        """
        Get detailed performance metrics for a specific product
        """
        # Basic metrics
        performance = {
            'total_views': product.view_count,
            'total_sales': product.sales_count,
            'current_rating': product.rating_average,
            'rating_count': product.rating_count,
            'current_stock': product.stock_quantity,
            'is_low_stock': product.is_low_stock,
            'discount_percentage': product.discount_percentage,
        }
        
        # Conversion rate
        if product.view_count > 0:
            performance['conversion_rate'] = (product.sales_count / product.view_count) * 100
        else:
            performance['conversion_rate'] = 0
        
        # Variant performance (for variable products)
        if product.product_type == 'variable':
            variants = product.variants.all()
            performance['variant_count'] = variants.count()
            performance['variants_in_stock'] = variants.filter(stock_quantity__gt=0).count()
            performance['avg_variant_price'] = variants.aggregate(
                avg=Avg('price')
            )['avg'] or 0
        
        return performance


class ProductRecommendationService:
    """
    Service for product recommendations
    """
    
    @staticmethod
    def get_related_products(product: Product, limit: int = 6) -> List[Product]:
        """
        Get products related to the given product
        """
        cache_key = f"related_products_{product.id}_{limit}"
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
        
        # Get products from same category and product class
        related = Product.objects.filter(
            store=product.store,
            status='published'
        ).exclude(id=product.id).select_related(
            'brand', 'category', 'product_class'
        )
        
        # Prioritize by similarity
        # 1. Same product class
        same_class = related.filter(product_class=product.product_class)[:limit//2]
        
        # 2. Same category
        same_category = related.filter(
            category=product.category
        ).exclude(
            id__in=[p.id for p in same_class]
        )[:limit//2]
        
        # 3. Same brand
        if product.brand:
            same_brand = related.filter(
                brand=product.brand
            ).exclude(
                id__in=[p.id for p in list(same_class) + list(same_category)]
            )[:limit//3]
        else:
            same_brand = []
        
        # Combine and limit
        result = list(same_class) + list(same_category) + list(same_brand)
        result = result[:limit]
        
        # If not enough, fill with popular products
        if len(result) < limit:
            popular = related.order_by('-view_count').exclude(
                id__in=[p.id for p in result]
            )[:limit - len(result)]
            result.extend(popular)
        
        # Cache for 30 minutes
        cache.set(cache_key, result, timeout=1800)
        return result
    
    @staticmethod
    def get_trending_products(store, limit: int = 10) -> List[Product]:
        """
        Get trending products for a store
        """
        cache_key = f"trending_products_{store.id}_{limit}"
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
        
        # Calculate trending score based on recent views and sales
        from django.utils import timezone
        from datetime import timedelta
        
        recent_date = timezone.now() - timedelta(days=7)
        
        trending = Product.objects.filter(
            store=store,
            status='published',
            updated_at__gte=recent_date
        ).annotate(
            trending_score=F('view_count') + (F('sales_count') * 5)
        ).order_by('-trending_score')[:limit]
        
        result = list(trending)
        
        # Cache for 1 hour
        cache.set(cache_key, result, timeout=3600)
        return result


# Service shortcuts for common operations
def create_simple_product(store, name_fa: str, product_class, category, price: Decimal, **kwargs):
    """
    Quick method to create a simple product
    """
    product_data = {
        'name_fa': name_fa,
        'name': kwargs.get('name', name_fa),
        'product_class': product_class,
        'category': category,
        'base_price': price,
        'product_type': 'simple',
        'status': 'draft',
        **kwargs
    }
    
    return ProductCreationService.create_product_from_data(store, product_data)


def get_store_homepage_data(store):
    """
    Get all data needed for store homepage
    """
    cache_key = f"store_homepage_{store.id}"
    cached_result = cache.get(cache_key)
    if cached_result:
        return cached_result
    
    data = {
        'featured_products': Product.objects.filter(
            store=store,
            status='published',
            is_featured=True
        ).order_by('-created_at')[:6],
        
        'recent_products': Product.objects.filter(
            store=store,
            status='published'
        ).order_by('-created_at')[:8],
        
        'popular_products': Product.objects.filter(
            store=store,
            status='published'
        ).order_by('-view_count')[:6],
        
        'trending_products': ProductRecommendationService.get_trending_products(store, 6),
        
        'categories': ProductCategory.objects.filter(
            store=store,
            is_active=True,
            parent__isnull=True
        ).order_by('display_order')[:8],
        
        'brands': Brand.objects.filter(
            store=store,
            is_active=True
        ).order_by('-product_count')[:6],
    }
    
    # Cache for 15 minutes
    cache.set(cache_key, data, timeout=900)
    return data
