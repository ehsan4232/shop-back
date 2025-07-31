from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from .models import Product
from .serializers import ProductSerializer
from rest_framework import viewsets
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

class ProductViewSet(viewsets.ModelViewSet):
    """
    Enhanced Product ViewSet with stock warning support
    """
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['category', 'brand', 'status', 'product_type', 'is_featured']
    search_fields = ['name', 'name_fa', 'description', 'sku']
    ordering_fields = ['created_at', 'price', 'view_count', 'sales_count', 'stock_quantity']
    ordering = ['-created_at']

    def get_queryset(self):
        return Product.objects.filter(
            store=self.request.user.store
        ).select_related(
            'product_class', 'category', 'brand'
        ).prefetch_related(
            'tags', 'images', 'variants__attribute_values'
        )

    @action(detail=True, methods=['get'])
    def stock_warning(self, request, pk=None):
        """
        Get stock warning data for a product
        Product description: "warning for store customer when the count is less than 3"
        """
        product = get_object_or_404(Product, pk=pk, store=request.user.store)
        
        # Use the enhanced method from the model
        stock_data = product.get_stock_warning_data()
        
        return Response(stock_data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def import_social_media(self, request, pk=None):
        """
        Import content from social media platforms
        Product description: "Get from social media" button functionality
        """
        product = get_object_or_404(Product, pk=pk, store=request.user.store)
        
        platform = request.data.get('platform')  # 'telegram' or 'instagram'
        source_id = request.data.get('source_id')  # username/channel
        
        if not platform or not source_id:
            return Response(
                {'error': 'پلتفرم و شناسه منبع الزامی است'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Import social media service (you'll need to implement this)
            from apps.social_media.services import SocialMediaImporter
            
            importer = SocialMediaImporter()
            posts_data = importer.import_from_platform(platform, source_id)
            
            # Store the imported data
            product.import_from_social_media(platform, {
                'source_id': source_id,
                'posts': posts_data,
                'imported_at': timezone.now().isoformat()
            })
            
            return Response({
                'message': f'با موفقیت از {platform} وارد شد',
                'posts_count': len(posts_data.get('data', [])),
                'social_data': posts_data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'error': f'خطا در واردکردن از {platform}: {str(e)}'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['get'])
    def low_stock(self, request):
        """
        Get products with low stock for store management
        """
        low_stock_products = self.get_queryset().filter(
            stock_quantity__lte=models.F('low_stock_threshold'),
            manage_stock=True,
            status='published'
        ).order_by('stock_quantity')
        
        serializer = self.get_serializer(low_stock_products, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
        """
        Duplicate a product instance for the "create another" functionality
        Product description: "checkbox for creating another instance with same info"
        """
        original_product = get_object_or_404(Product, pk=pk, store=request.user.store)
        
        # Create a copy with modified fields
        new_product_data = {
            'product_class': original_product.product_class,
            'category': original_product.category,
            'brand': original_product.brand,
            'name': request.data.get('name', f"{original_product.name} - کپی"),
            'name_fa': request.data.get('name_fa', f"{original_product.name_fa} - کپی"),
            'description': original_product.description,
            'short_description': original_product.short_description,
            'base_price': request.data.get('base_price', original_product.base_price),
            'compare_price': original_product.compare_price,
            'cost_price': original_product.cost_price,
            'stock_quantity': request.data.get('stock_quantity', 0),
            'manage_stock': original_product.manage_stock,
            'low_stock_threshold': original_product.low_stock_threshold,
            'weight': original_product.weight,
            'product_type': original_product.product_type,
            'status': 'draft',  # Always start as draft
            'store': request.user.store
        }
        
        try:
            # Create new product
            new_product = Product.objects.create(**new_product_data)
            
            # Copy tags
            new_product.tags.set(original_product.tags.all())
            
            # Copy attribute values
            for attr_value in original_product.attribute_values.all():
                attr_value.pk = None  # Create new instance
                attr_value.product = new_product
                attr_value.save()
            
            serializer = self.get_serializer(new_product)
            return Response({
                'message': 'محصول با موفقیت کپی شد',
                'product': serializer.data
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {'error': f'خطا در کپی کردن محصول: {str(e)}'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

# Additional ViewSet for Product Class management
class ProductClassViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Product Classes with OOP validation
    """
    
    def get_queryset(self):
        return ProductClass.objects.filter(
            store=self.request.user.store
        ).select_related('parent').prefetch_related('children', 'attributes')

    @action(detail=True, methods=['get'])
    def can_create_products(self, request, pk=None):
        """
        Check if this product class can create product instances
        Product description: "Instance Creation: Only from leaf nodes"
        """
        product_class = get_object_or_404(ProductClass, pk=pk, store=request.user.store)
        
        can_create, message = product_class.can_create_product_instances()
        
        return Response({
            'can_create': can_create,
            'message': message,
            'is_leaf': product_class.is_leaf,
            'children_count': product_class.get_children().count(),
            'products_count': product_class.products.count()
        })

    @action(detail=True, methods=['get'])
    def inherited_attributes(self, request, pk=None):
        """
        Get all inherited attributes from ancestors
        """
        product_class = get_object_or_404(ProductClass, pk=pk, store=request.user.store)
        
        inherited_attrs = product_class.get_inherited_attributes()
        
        # Serialize the attributes
        attrs_data = []
        for attr in inherited_attrs:
            attrs_data.append({
                'id': attr.id,
                'name': attr.attribute_type.name,
                'name_fa': attr.attribute_type.name_fa,
                'data_type': attr.attribute_type.data_type,
                'is_required': attr.is_required,
                'default_value': attr.default_value,
                'from_class': attr.product_class.name_fa,
                'is_categorizer': attr.is_categorizer
            })
        
        return Response({
            'inherited_attributes': attrs_data,
            'effective_price': product_class.get_effective_price(),
            'inherited_media': product_class.get_inherited_media()
        })
