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
    
    # Theme system endpoints (product requirement: "various fancy and modern designs")
    path('themes/', views.ThemeListView.as_view(), name='theme-list'),
    path('themes/<uuid:theme_id>/', views.ThemeDetailView.as_view(), name='theme-detail'),
    path('themes/<uuid:theme_id>/preview/', views.ThemePreviewView.as_view(), name='theme-preview'),
    path('themes/<uuid:theme_id>/rate/', views.ThemeRatingView.as_view(), name='theme-rate'),
    path('themes/recommended/', views.RecommendedThemesView.as_view(), name='recommended-themes'),
    
    # Store theme management
    path('<uuid:store_id>/apply-theme/', views.ApplyThemeView.as_view(), name='apply-theme'),
    path('<uuid:store_id>/theme-customization/', views.ThemeCustomizationView.as_view(), name='theme-customization'),
    path('<uuid:store_id>/theme-css/', views.GenerateThemeCSSView.as_view(), name='theme-css'),
    
    # Dashboard analytics (product requirement: "dashboards of charts and info")
    path('<uuid:store_id>/analytics/dashboard/', views.StoreDashboardAnalyticsView.as_view(), name='dashboard-analytics'),
    path('<uuid:store_id>/analytics/sales/', views.SalesAnalyticsView.as_view(), name='sales-analytics'),
    path('<uuid:store_id>/analytics/visitors/', views.VisitorAnalyticsView.as_view(), name='visitor-analytics'),
    
    # Settings management
    path('settings/', views.StoreSettingsView.as_view(), name='store-settings'),
    
    # Domain management
    path('domain/check/', views.DomainCheckView.as_view(), name='domain-check'),
    path('domain/setup/', views.DomainSetupView.as_view(), name='domain-setup'),
    
    # Store validation
    path('validate/subdomain/', views.SubdomainValidationView.as_view(), name='validate-subdomain'),
    path('validate/domain/', views.DomainValidationView.as_view(), name='validate-domain'),
]