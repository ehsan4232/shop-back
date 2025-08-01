"""
URL configuration for Mall project
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

# API v1 patterns
api_v1_patterns = [
    # Authentication
    path('auth/', include('apps.accounts.urls')),
    
    # Core Features
    path('products/', include('apps.products.urls')),
    path('stores/', include('apps.stores.urls')),
    path('orders/', include('apps.orders.urls')),
    
    # Additional Features
    path('social-media/', include('apps.social_media.urls')),
    path('payments/', include('apps.payments.urls')),
    path('communications/', include('apps.communications.urls')),
    path('logistics/', include('apps.logistics.urls')),
    path('analytics/', include('apps.analytics.urls')),
    path('themes/', include('apps.themes.urls')),  # ADDED: Separate themes management
]

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),
    
    # API
    path('api/v1/', include(api_v1_patterns)),
    
    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    
    # Health check
    path('health/', include('django_extensions.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    
    # Django Debug Toolbar
    if 'debug_toolbar' in settings.INSTALLED_APPS:
        import debug_toolbar
        urlpatterns = [path('__debug__/', include(debug_toolbar.urls))] + urlpatterns

# Custom error handlers
handler404 = 'mall.views.handler404'
handler500 = 'mall.views.handler500'
