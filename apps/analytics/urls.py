from django.urls import path, include
from rest_framework.routers import DefaultRouter

# Create router for viewsets
router = DefaultRouter()

app_name = 'analytics'

urlpatterns = [
    # Include router URLs
    path('', include(router.urls)),
    
    # Custom endpoints
    path('dashboard/', view=None, name='dashboard-data'),  # Will be implemented later
    path('sales-chart/', view=None, name='sales-chart'),
    path('website-stats/', view=None, name='website-stats'),
    path('reports/', view=None, name='reports-list'),
]
