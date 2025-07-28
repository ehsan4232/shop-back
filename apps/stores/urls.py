"""
Store URLs configuration
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create router for ViewSets
router = DefaultRouter()
router.register(r'', views.StoreViewSet, basename='store')

urlpatterns = [
    # Store ViewSet routes (list, retrieve, create, update, delete)
    path('', include(router.urls)),
    
    # Custom store endpoints
    path('current/', views.CurrentStoreView.as_view(), name='current-store'),
    path('statistics/', views.StoreStatisticsView.as_view(), name='store-statistics'),
    path('analytics/', views.StoreAnalyticsView.as_view(), name='store-analytics'),
    
    # Theme management
    path('theme/', views.StoreThemeView.as_view(), name='store-theme'),
    path('theme/preview/', views.ThemePreviewView.as_view(), name='theme-preview'),
    
    # Settings management
    path('settings/', views.StoreSettingsView.as_view(), name='store-settings'),
    
    # Domain management
    path('domain/check/', views.DomainCheckView.as_view(), name='domain-check'),
    path('domain/setup/', views.DomainSetupView.as_view(), name='domain-setup'),
    
    # Store validation
    path('validate/subdomain/', views.SubdomainValidationView.as_view(), name='validate-subdomain'),
    path('validate/domain/', views.DomainValidationView.as_view(), name='validate-domain'),
]
