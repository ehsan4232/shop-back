from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'products'

# Create router for ViewSets
router = DefaultRouter()
router.register(r'categories', views.CategoryViewSet, basename='category')
router.register(r'brands', views.BrandViewSet, basename='brand')
router.register(r'tags', views.TagViewSet, basename='tag')
router.register(r'products', views.ProductViewSet, basename='product')
router.register(r'collections', views.CollectionViewSet, basename='collection')

urlpatterns = [
    # ViewSet URLs
    path('', include(router.urls)),
    
    # Custom endpoints
    path('categories/<slug:slug>/filters/', views.category_filters, name='category-filters'),
    path('stores/<uuid:store_id>/statistics/', views.store_statistics, name='store-statistics'),
    path('analytics/', views.product_analytics, name='product-analytics'),
    path('trending-searches/', views.trending_searches, name='trending-searches'),
    path('import-from-social/', views.import_from_social_media, name='import-from-social'),
]
