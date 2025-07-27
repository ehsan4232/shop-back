from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from .models import ProductCategory, Product, ProductInstance
from .serializers import ProductCategorySerializer, ProductSerializer, ProductInstanceSerializer

class ProductCategoryViewSet(viewsets.ModelViewSet):
    serializer_class = ProductCategorySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['store', 'parent', 'is_categorizer']
    search_fields = ['name', 'name_fa']
    
    def get_queryset(self):
        return ProductCategory.objects.filter(store__owner=self.request.user)

class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['store', 'category', 'is_active', 'is_featured']
    search_fields = ['name', 'name_fa', 'description_fa']
    ordering_fields = ['created_at', 'view_count', 'base_price']
    ordering = ['-created_at']
    
    def get_queryset(self):
        return Product.objects.filter(store__owner=self.request.user)
    
    @action(detail=True, methods=['post'])
    def increment_view(self, request, pk=None):
        product = self.get_object()
        product.increment_view_count()
        return Response({'view_count': product.view_count})

class ProductInstanceViewSet(viewsets.ModelViewSet):
    serializer_class = ProductInstanceSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['product', 'is_active']
    search_fields = ['sku', 'product__name_fa']
    
    def get_queryset(self):
        return ProductInstance.objects.filter(product__store__owner=self.request.user)