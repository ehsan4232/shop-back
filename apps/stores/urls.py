from django.urls import path
from . import views

urlpatterns = [
    # Store CRUD
    path('', views.StoreListCreateView.as_view(), name='store-list-create'),
    path('<uuid:pk>/', views.StoreDetailView.as_view(), name='store-detail'),
    
    # Store Theme & Settings
    path('<uuid:store_pk>/theme/', views.StoreThemeView.as_view(), name='store-theme'),
    path('<uuid:store_pk>/settings/', views.StoreSettingsView.as_view(), name='store-settings'),
    
    # Analytics & Statistics
    path('<uuid:store_pk>/statistics/', views.store_statistics, name='store-statistics'),
    path('<uuid:store_pk>/analytics/', views.store_analytics_data, name='store-analytics'),
    
    # Public Store Access
    path('public/<str:subdomain>/', views.store_public_info, name='store-public'),
    
    # Utilities
    path('check-subdomain/', views.check_subdomain_availability, name='check-subdomain'),
    path('check-domain/', views.check_domain_availability, name='check-domain'),
]
