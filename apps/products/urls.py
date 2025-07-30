from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create router for ViewSets
router = DefaultRouter()
router.register(r'attribute-types', views.AttributeTypeViewSet, basename='attributetype')
router.register(r'tags', views.TagViewSet, basename='tag')
router.register(r'product-classes', views.ProductClassViewSet, basename='productclass')
router.register(r'categories', views.CategoryViewSet, basename='category')
router.register(r'brands', views.BrandViewSet, basename='brand')
router.register(r'products', views.ProductViewSet, basename='product')
router.register(r'collections', views.CollectionViewSet, basename='collection')

app_name = 'products'

urlpatterns = [
    # Include router URLs
    path('', include(router.urls)),
    
    # Additional API endpoints
    path('categories/<slug:slug>/filters/', views.category_filters, name='category-filters'),
    path('store-statistics/', views.store_statistics, name='store-statistics'),
    path('import-social-media/', views.import_from_social_media, name='import-social-media'),
    path('analytics/', views.product_analytics, name='product-analytics'),
    path('trending-searches/', views.trending_searches, name='trending-searches'),
    path('product-class-hierarchy/', views.product_class_hierarchy, name='product-class-hierarchy'),
]
