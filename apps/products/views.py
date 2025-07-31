# Enhanced views with stock warning API endpoint
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.generic import ListView, DetailView
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_ratelimit.decorators import ratelimit
from django.core.cache import cache
from django.db.models import Q, F, Count, Avg
from .models import (
    Product, ProductClass, ProductCategory, Brand, Tag, 
    ProductVariant, ProductAttributeValue, Collection
)
from .serializers import (
    ProductSerializer, ProductClassSerializer, ProductCategorySerializer,
    BrandSerializer, TagSerializer, ProductVariantSerializer
)
from apps.social_media.services import SocialMediaImporter
import logging

logger = logging.getLogger(__name__)

# API Views
class ProductViewSet(viewsets.ModelViewSet):
    """Enhanced Product ViewSet with stock warning support"""
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = Product.objects.select_related(
            'store', 'product_class', 'category', 'brand'
        ).prefetch_related(
            'tags', 'images', 'variants', 'attribute_values__attribute__attribute_type'
        )
        
        # Filter by store if user is store owner
        if hasattr(self.request.user, 'store'):
            queryset = queryset.filter(store=self.request.user.store)
        
        return queryset
    
    @action(detail=True, methods=['get'])
    def stock_warning(self, request, pk=None):
        """Get stock warning data for a product - Implements product description requirement"""
        product = self.get_object()
        
        try:
            # Get comprehensive stock warning data
            warning_data = product.get_stock_warning_data()
            
            return Response({
                'success': True,
                'product_id': str(product.id),
                'needs_warning': warning_data['needs_warning'],
                'stock_count': warning_data.get('stock_count'),
                'message': warning_data.get('message', ''),
                'level': warning_data.get('level', 'info'),
                'variant_warnings': warning_data.get('variant_warnings', []),
                'last_updated': product.updated_at.isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error getting stock warning for product {pk}: {str(e)}")
            return Response({
                'success': False,
                'error': 'خطا در دریافت اطلاعات موجودی'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    @ratelimit(key='user', rate='10/m', method='POST', block=True)
    def import_social_media(self, request, pk=None):
        """Import content from social media - Implements product description requirement"""
        product = self.get_object()
        
        try:
            platform = request.data.get('platform')  # 'instagram' or 'telegram'
            source_id = request.data.get('source_id')  # username or channel
            limit = min(int(request.data.get('limit', 5)), 10)  # Max 10 posts
            
            if not platform or not source_id:
                return Response({
                    'success': False,
                    'error': 'پلتفرم و شناسه منبع الزامی است'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Use the social media importer service
            importer = SocialMediaImporter()
            
            # Get content from platform
            content = importer.get_platform_content(platform, source_id, limit)
            
            if not content:
                return Response({
                    'success': False,
                    'error': f'محتوایی از {platform} یافت نشد'
                })
            
            # Import content to product
            result = importer.import_content_to_product(product, platform, content)
            
            return Response({
                'success': True,
                'imported_images': result['imported_images'],
                'imported_texts': result['imported_texts'],
                'total_processed': result['total_processed'],
                'errors': result.get('errors', []),
                'message': f'محتوا از {platform} با موفقیت وارد شد'
            })
            
        except Exception as e:
            logger.error(f"Error importing social media content: {str(e)}")
            return Response({
                'success': False,
                'error': 'خطا در واردکردن محتوای شبکه اجتماعی'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def low_stock_products(self, request):
        """Get products with low stock for dashboard alerts"""
        queryset = self.get_queryset().filter(
            Q(stock_quantity__lte=F('low_stock_threshold')) |
            Q(variants__stock_quantity__lte=3)
        ).distinct()
        
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'success': True,
            'count': queryset.count(),
            'products': serializer.data
        })

class ProductClassViewSet(viewsets.ModelViewSet):
    """Enhanced Product Class ViewSet with inheritance validation"""
    serializer_class = ProductClassSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = ProductClass.objects.select_related('parent', 'store').prefetch_related(
            'attributes__attribute_type', 'children'
        )
        
        if hasattr(self.request.user, 'store'):
            queryset = queryset.filter(store=self.request.user.store)
        
        return queryset
    
    @action(detail=True, methods=['get'])
    def can_create_products(self, request, pk=None):
        """Check if this class can create product instances"""
        product_class = self.get_object()
        can_create, message = product_class.can_create_product_instances()
        
        return Response({
            'can_create': can_create,
            'message': message,
            'is_leaf': product_class.is_leaf,
            'has_children': product_class.get_children().exists(),
            'product_count': product_class.product_count
        })
    
    @action(detail=True, methods=['get'])
    def inherited_attributes(self, request, pk=None):
        """Get all inherited attributes from ancestors"""
        product_class = self.get_object()
        attributes = product_class.get_inherited_attributes()
        
        data = []
        for attr in attributes:
            data.append({
                'id': attr.id,
                'attribute_type': {
                    'id': attr.attribute_type.id,
                    'name': attr.attribute_type.name,
                    'name_fa': attr.attribute_type.name_fa,
                    'data_type': attr.attribute_type.data_type
                },
                'default_value': attr.default_value,
                'is_required': attr.is_required,
                'is_inherited': attr.is_inherited,
                'display_order': attr.display_order
            })
        
        return Response({
            'success': True,
            'attributes': data,
            'count': len(data)
        })

# Template Views
class ProductListView(ListView):
    """Product list view with filtering and stock warnings"""
    model = Product
    template_name = 'products/product_list.html'
    context_object_name = 'products'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Product.objects.filter(
            status='published'
        ).select_related(
            'product_class', 'category', 'brand'
        ).prefetch_related('images', 'tags')
        
        # Apply filters
        category_slug = self.request.GET.get('category')
        if category_slug:
            queryset = queryset.filter(category__slug=category_slug)
        
        brand_slug = self.request.GET.get('brand')
        if brand_slug:
            queryset = queryset.filter(brand__slug=brand_slug)
        
        # Search
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name_fa__icontains=search) |
                Q(description__icontains=search) |
                Q(tags__name_fa__icontains=search)
            ).distinct()
        
        # Price range
        min_price = self.request.GET.get('min_price')
        max_price = self.request.GET.get('max_price')
        if min_price:
            queryset = queryset.filter(base_price__gte=min_price)
        if max_price:
            queryset = queryset.filter(base_price__lte=max_price)
        
        # Stock filter
        stock_filter = self.request.GET.get('stock')
        if stock_filter == 'available':
            queryset = queryset.filter(stock_quantity__gt=0)
        elif stock_filter == 'low':
            queryset = queryset.filter(
                stock_quantity__lte=F('low_stock_threshold'),
                stock_quantity__gt=0
            )
        elif stock_filter == 'out':
            queryset = queryset.filter(stock_quantity=0)
        
        # Ordering
        order = self.request.GET.get('order', '-created_at')
        if order in ['price', '-price', 'name_fa', '-name_fa', '-created_at', '-view_count']:
            queryset = queryset.order_by(order)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add filter options
        context['categories'] = ProductCategory.objects.filter(
            is_active=True
        ).order_by('name_fa')
        
        context['brands'] = Brand.objects.filter(
            is_active=True
        ).order_by('name_fa')
        
        # Current filters
        context['current_filters'] = {
            'category': self.request.GET.get('category', ''),
            'brand': self.request.GET.get('brand', ''),
            'search': self.request.GET.get('search', ''),
            'min_price': self.request.GET.get('min_price', ''),
            'max_price': self.request.GET.get('max_price', ''),
            'stock': self.request.GET.get('stock', ''),
            'order': self.request.GET.get('order', '-created_at')
        }
        
        return context

class ProductDetailView(DetailView):
    """Product detail view with stock warning and social media data"""
    model = Product
    template_name = 'products/product_detail.html'
    context_object_name = 'product'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'
    
    def get_queryset(self):
        return Product.objects.select_related(
            'product_class', 'category', 'brand', 'store'
        ).prefetch_related(
            'images', 'variants__attribute_values__attribute__attribute_type',
            'attribute_values__attribute__attribute_type', 'tags'
        )
    
    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        
        # Increment view count
        Product.objects.filter(id=obj.id).update(view_count=F('view_count') + 1)
        
        return obj
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = context['product']
        
        # Stock warning data
        context['stock_warning'] = product.get_stock_warning_data()
        
        # Related products
        context['related_products'] = Product.objects.filter(
            category=product.category,
            status='published'
        ).exclude(id=product.id)[:4]
        
        # Product attributes with color support
        attributes = []
        for attr_value in product.attribute_values.all():
            attr_data = {
                'name': attr_value.attribute.attribute_type.name_fa,
                'type': attr_value.attribute.attribute_type.data_type,
                'value': attr_value.get_value()
            }
            
            # Special handling for color attributes
            if attr_value.attribute.attribute_type.data_type == 'color':
                attr_data['color_hex'] = attr_value.value_color
                attr_data['display_html'] = f'<div class="color-preview" style="background-color: {attr_value.value_color};"></div>{attr_value.value_color}'
            
            attributes.append(attr_data)
        
        context['product_attributes'] = attributes
        
        # Social media data if imported
        if product.imported_from_social and product.social_media_data:
            context['social_media_info'] = {
                'platform': product.social_media_source,
                'imported_at': product.last_social_import,
                'data': product.social_media_data
            }
        
        return context

# Utility API endpoints
@require_http_methods(["GET"])
@ratelimit(key='ip', rate='60/m', method='GET', block=True)
def product_stock_warning_api(request, product_id):
    """API endpoint for getting stock warning data"""
    try:
        product = get_object_or_404(Product, id=product_id)
        warning_data = product.get_stock_warning_data()
        
        return JsonResponse({
            'success': True,
            'product_id': str(product.id),
            **warning_data
        })
        
    except Exception as e:
        logger.error(f"Error in stock warning API: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'خطا در دریافت اطلاعات موجودی'
        }, status=500)

@require_http_methods(["GET"])
def product_class_validation_api(request, class_id):
    """API endpoint for validating product class creation rules"""
    try:
        product_class = get_object_or_404(ProductClass, id=class_id)
        can_create, message = product_class.can_create_product_instances()
        
        return JsonResponse({
            'success': True,
            'can_create': can_create,
            'message': message,
            'is_leaf': product_class.is_leaf,
            'has_children': product_class.get_children().exists()
        })
        
    except Exception as e:
        logger.error(f"Error in class validation API: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'خطا در اعتبارسنجی کلاس محصول'
        }, status=500)
