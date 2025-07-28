from django.urls import path, include
from .views import *

app_name = 'products'

urlpatterns = [
    # Categories
    path('categories/', CategoryListView.as_view(), name='category-list'),
    path('categories/<slug:slug>/', CategoryDetailView.as_view(), name='category-detail'),
    path('categories/<slug:slug>/filters/', category_filters, name='category-filters'),
    
    # Brands
    path('brands/', BrandListView.as_view(), name='brand-list'),
    path('brands/<slug:slug>/', BrandDetailView.as_view(), name='brand-detail'),
    
    # Tags
    path('tags/', TagListView.as_view(), name='tag-list'),
    
    # Products
    path('products/', ProductListView.as_view(), name='product-list'),
    path('products/<slug:slug>/', ProductDetailView.as_view(), name='product-detail'),
    path('products/<uuid:product_id>/recommendations/', product_recommendations, name='product-recommendations'),
    
    # Search
    path('search/', product_search, name='product-search'),
    path('trending/', trending_searches, name='trending-searches'),
    
    # Collections
    path('collections/', CollectionListView.as_view(), name='collection-list'),
    path('collections/<slug:slug>/', CollectionDetailView.as_view(), name='collection-detail'),
    
    # Statistics
    path('statistics/', store_statistics, name='store-statistics'),
    
    # Admin functionality
    path('admin/generate-variants/', generate_product_variants, name='generate-variants'),
]
