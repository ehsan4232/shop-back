from django.urls import path
from . import views

urlpatterns = [
    # Social Media Accounts
    path('accounts/', views.SocialMediaAccountListView.as_view(), name='social-accounts-list'),
    path('accounts/<uuid:pk>/', views.SocialMediaAccountDetailView.as_view(), name='social-account-detail'),
    
    # Posts
    path('accounts/<uuid:account_id>/posts/', views.SocialMediaPostListView.as_view(), name='social-posts-list'),
    path('posts/<uuid:pk>/', views.SocialMediaPostDetailView.as_view(), name='social-post-detail'),
    
    # Import Actions
    path('import-posts/', views.import_posts_from_social, name='import-posts'),
    path('import-to-product/', views.import_posts_to_product, name='import-to-product'),
    
    # Statistics
    path('statistics/', views.social_media_statistics, name='social-statistics'),
]
