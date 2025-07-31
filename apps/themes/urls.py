from django.urls import path, include
from rest_framework.routers import DefaultRouter

# Create router for viewsets
router = DefaultRouter()

app_name = 'themes'

urlpatterns = [
    # Include router URLs
    path('', include(router.urls)),
    
    # Custom endpoints
    path('available/', view=None, name='available-themes'),  # Will be implemented later
    path('<uuid:theme_id>/preview/', view=None, name='theme-preview'),
]
