from django.urls import path, include
from rest_framework.routers import DefaultRouter

# Create router for viewsets
router = DefaultRouter()

app_name = 'logistics'

urlpatterns = [
    # Include router URLs
    path('', include(router.urls)),
    
    # Custom endpoints
    path('providers/', view=None, name='providers-list'),  # Will be implemented later
    path('calculate-shipping/', view=None, name='calculate-shipping'),
    path('track/<str:tracking_number>/', view=None, name='track-shipment'),
]
