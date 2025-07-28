"""
Orders URL Configuration
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create router for ViewSets
router = DefaultRouter()
router.register(r'orders', views.OrderViewSet, basename='order')
router.register(r'cart', views.CartViewSet, basename='cart')
router.register(r'cart-items', views.CartItemViewSet, basename='cart-item')
router.register(r'wishlist', views.WishlistViewSet, basename='wishlist')

urlpatterns = [
    # ViewSet routes
    path('', include(router.urls)),
    
    # Cart management
    path('add-to-cart/', views.add_to_cart, name='add-to-cart'),
    path('update-cart-item/<uuid:item_id>/', views.update_cart_item, name='update-cart-item'),
    path('remove-from-cart/<uuid:item_id>/', views.remove_from_cart, name='remove-from-cart'),
    path('clear-cart/', views.clear_cart, name='clear-cart'),
    
    # Wishlist management
    path('add-to-wishlist/', views.add_to_wishlist, name='add-to-wishlist'),
    path('remove-from-wishlist/<uuid:product_id>/', views.remove_from_wishlist, name='remove-from-wishlist'),
    
    # Order management
    path('order-history/', views.order_history, name='order-history'),
    path('order-analytics/', views.order_analytics, name='order-analytics'),
    
    # Checkout
    path('checkout/', views.CheckoutView.as_view(), name='checkout'),
]
