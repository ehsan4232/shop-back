from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .models import SocialMediaAccount, SocialMediaPost, SocialMediaImportSession
from .serializers import *
from .services import SocialMediaImporter
from apps.products.models import Product
from apps.stores.models import Store

class SocialMediaAccountListView(generics.ListCreateAPIView):
    """List and create social media accounts"""
    serializer_class = SocialMediaAccountSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Get accounts for user's stores
        user_stores = Store.objects.filter(owner=self.request.user)
        return SocialMediaAccount.objects.filter(store__in=user_stores)
    
    def perform_create(self, serializer):
        # Associate with user's store
        store_id = self.request.data.get('store_id')
        store = get_object_or_404(Store, id=store_id, owner=self.request.user)
        serializer.save(store=store)

class SocialMediaAccountDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, delete social media account"""
    serializer_class = SocialMediaAccountSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user_stores = Store.objects.filter(owner=self.request.user)
        return SocialMediaAccount.objects.filter(store__in=user_stores)

class SocialMediaPostListView(generics.ListAPIView):
    """List social media posts for an account"""
    serializer_class = SocialMediaPostListSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        account_id = self.kwargs.get('account_id')
        user_stores = Store.objects.filter(owner=self.request.user)
        
        account = get_object_or_404(
            SocialMediaAccount,
            id=account_id,
            store__in=user_stores
        )
        
        queryset = SocialMediaPost.objects.filter(account=account)
        
        # Filter by import status
        imported = self.request.query_params.get('imported')
        if imported == 'true':
            queryset = queryset.filter(is_imported=True)
        elif imported == 'false':
            queryset = queryset.filter(is_imported=False)
        
        return queryset.order_by('-post_date')

class SocialMediaPostDetailView(generics.RetrieveAPIView):
    """Get detailed view of a social media post"""
    serializer_class = SocialMediaPostSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user_stores = Store.objects.filter(owner=self.request.user)
        return SocialMediaPost.objects.filter(account__store__in=user_stores)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def import_posts_from_social(request):
    """Import recent posts from social media account"""
    serializer = ImportPostsSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    data = serializer.validated_data
    
    # Get the account
    user_stores = Store.objects.filter(owner=request.user)
    account = get_object_or_404(
        SocialMediaAccount,
        id=data['account_id'],
        store__in=user_stores
    )
    
    # Create import session
    import_session = SocialMediaImportSession.objects.create(
        store=account.store,
        account=account,
        posts_limit=data['posts_limit'],
        import_images=data['import_images'],
        import_videos=data['import_videos'],
        import_captions=data['import_captions'],
        status='processing'
    )
    
    try:
        # Initialize importer
        importer = SocialMediaImporter(account)
        
        # Import posts
        imported_posts, error = importer.import_recent_posts(data['posts_limit'])
        
        if error:
            import_session.status = 'failed'
            import_session.error_message = error
            import_session.completed_at = timezone.now()
            import_session.save()
            
            return Response({
                'error': error,
                'session_id': import_session.id
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Update session
        import_session.status = 'completed'
        import_session.posts_found = len(imported_posts)
        import_session.posts_imported = len(imported_posts)
        import_session.completed_at = timezone.now()
        import_session.save()
        
        # Return imported posts
        posts_data = SocialMediaPostListSerializer(imported_posts, many=True).data
        
        return Response({
            'success': True,
            'posts': posts_data,
            'session': SocialMediaImportSessionSerializer(import_session).data
        })
        
    except Exception as e:
        import_session.status = 'failed'
        import_session.error_message = str(e)
        import_session.completed_at = timezone.now()
        import_session.save()
        
        return Response({
            'error': 'خطا در واردات پست‌ها',
            'details': str(e),
            'session_id': import_session.id
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def import_posts_to_product(request):
    """Import selected posts to a product"""
    serializer = ImportToProductSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    data = serializer.validated_data
    
    # Get the product
    user_stores = Store.objects.filter(owner=request.user)
    product = get_object_or_404(
        Product,
        id=data['product_id'],
        store__in=user_stores
    )
    
    # Get the posts
    posts = SocialMediaPost.objects.filter(
        id__in=data['post_ids'],
        account__store__in=user_stores
    )
    
    if not posts.exists():
        return Response({
            'error': 'هیچ پست معتبری یافت نشد'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Get the account from first post
    account = posts.first().account
    
    try:
        # Initialize importer
        importer = SocialMediaImporter(account)
        
        # Import to product
        imported_content, error = importer.import_to_product(
            data['post_ids'],
            product,
            import_images=data['import_images'],
            import_videos=data['import_videos'],
            import_text=data['import_text']
        )
        
        if error:
            return Response({
                'error': error
            }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({
            'success': True,
            'message': 'محتوا با موفقیت به محصول اضافه شد',
            'imported': imported_content
        })
        
    except Exception as e:
        return Response({
            'error': 'خطا در واردات محتوا به محصول',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def social_media_statistics(request):
    """Get social media statistics for user's stores"""
    user_stores = Store.objects.filter(owner=request.user)
    
    # Get statistics
    total_accounts = SocialMediaAccount.objects.filter(store__in=user_stores).count()
    active_accounts = SocialMediaAccount.objects.filter(
        store__in=user_stores,
        is_active=True
    ).count()
    
    total_posts = SocialMediaPost.objects.filter(
        account__store__in=user_stores
    ).count()
    
    imported_posts = SocialMediaPost.objects.filter(
        account__store__in=user_stores,
        is_imported=True
    ).count()
    
    # Recent activity
    recent_sessions = SocialMediaImportSession.objects.filter(
        store__in=user_stores
    ).order_by('-started_at')[:5]
    
    # Platform breakdown
    platform_stats = {}
    for platform_choice in SocialMediaAccount.PLATFORM_CHOICES:
        platform = platform_choice[0]
        count = SocialMediaAccount.objects.filter(
            store__in=user_stores,
            platform=platform,
            is_active=True
        ).count()
        if count > 0:
            platform_stats[platform] = count
    
    statistics = {
        'total_accounts': total_accounts,
        'active_accounts': active_accounts,
        'total_posts': total_posts,
        'imported_posts': imported_posts,
        'import_rate': round((imported_posts / total_posts * 100) if total_posts > 0 else 0, 1),
        'platform_breakdown': platform_stats,
        'recent_sessions': SocialMediaImportSessionSerializer(recent_sessions, many=True).data
    }
    
    return Response(statistics)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_import_session(request, session_id):
    """Get import session details"""
    user_stores = Store.objects.filter(owner=request.user)
    session = get_object_or_404(
        SocialMediaImportSession,
        id=session_id,
        store__in=user_stores
    )
    
    return Response(SocialMediaImportSessionSerializer(session).data)
