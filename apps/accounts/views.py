from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.cache import cache
from django.conf import settings
import logging

from .models import UserSession, UserNotification
from .serializers import UserSerializer

User = get_user_model()
logger = logging.getLogger(__name__)

# Legacy views for backward compatibility - redirect to new OTP system

@api_view(['POST'])
@permission_classes([AllowAny])
def send_otp(request):
    """Legacy send OTP - redirect to new OTP system"""
    return Response({
        'message': 'این روش منسوخ شده است. لطفا از /api/v1/send-otp/ استفاده کنید',
        'redirect_to': '/api/v1/send-otp/'
    }, status=status.HTTP_301_MOVED_PERMANENTLY)

@api_view(['POST'])
@permission_classes([AllowAny])
def verify_otp(request):
    """Legacy verify OTP - redirect to new OTP system"""
    return Response({
        'message': 'این روش منسوخ شده است. لطفا از /api/v1/verify-otp/ استفاده کنید',
        'redirect_to': '/api/v1/verify-otp/'
    }, status=status.HTTP_301_MOVED_PERMANENTLY)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    """Logout user and invalidate tokens"""
    try:
        # Get refresh token from request
        refresh_token = request.data.get('refresh_token')
        
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()
        
        # Mark user sessions as inactive
        UserSession.objects.filter(
            user=request.user,
            is_active=True
        ).update(is_active=False)
        
        return Response(
            {'message': 'خروج موفقیت‌آمیز'}, 
            status=status.HTTP_200_OK
        )
    
    except Exception as e:
        logger.error(f"Logout error for user {request.user.phone_number}: {e}")
        return Response(
            {'message': 'خروج موفقیت‌آمیز'}, 
            status=status.HTTP_200_OK
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profile(request):
    """Get current user profile"""
    return Response({
        'user': UserSerializer(request.user).data
    }, status=status.HTTP_200_OK)

@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def update_profile(request):
    """Update user profile"""
    user = request.user
    serializer = UserSerializer(user, data=request.data, partial=True)
    
    if serializer.is_valid():
        serializer.save()
        return Response({
            'user': serializer.data,
            'message': 'پروفایل به‌روزرسانی شد'
        }, status=status.HTTP_200_OK)
    
    return Response(
        {'errors': serializer.errors}, 
        status=status.HTTP_400_BAD_REQUEST
    )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_sessions(request):
    """Get user's active sessions"""
    sessions = UserSession.objects.filter(
        user=request.user
    ).order_by('-last_activity')[:10]
    
    sessions_data = []
    for session in sessions:
        sessions_data.append({
            'id': str(session.id),
            'ip_address': session.ip_address,
            'is_active': session.is_active,
            'is_current': session.session_key == getattr(request.session, 'session_key', 'api_session'),
            'last_activity': session.last_activity,
            'created_at': session.created_at,
            'device_info': session.device_info
        })
    
    return Response({
        'sessions': sessions_data
    }, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def revoke_session(request):
    """Revoke a specific user session"""
    session_id = request.data.get('session_id')
    
    try:
        session = UserSession.objects.get(
            id=session_id,
            user=request.user
        )
        session.revoke()
        
        return Response(
            {'message': 'جلسه لغو شد'}, 
            status=status.HTTP_200_OK
        )
    
    except UserSession.DoesNotExist:
        return Response(
            {'error': 'جلسه یافت نشد'}, 
            status=status.HTTP_404_NOT_FOUND
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def notifications(request):
    """Get user notifications"""
    notifications = UserNotification.objects.filter(
        user=request.user
    ).order_by('-created_at')[:20]
    
    notifications_data = []
    for notification in notifications:
        notifications_data.append({
            'id': str(notification.id),
            'title': notification.title,
            'message': notification.message,
            'notification_type': notification.notification_type,
            'is_read': notification.is_read,
            'action_url': notification.action_url,
            'created_at': notification.created_at
        })
    
    return Response({
        'notifications': notifications_data,
        'unread_count': UserNotification.objects.filter(
            user=request.user, 
            is_read=False
        ).count()
    }, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_notification_read(request):
    """Mark notification as read"""
    notification_id = request.data.get('notification_id')
    
    try:
        notification = UserNotification.objects.get(
            id=notification_id,
            user=request.user
        )
        notification.mark_as_read()
        
        return Response(
            {'message': 'اعلان خوانده شد'}, 
            status=status.HTTP_200_OK
        )
    
    except UserNotification.DoesNotExist:
        return Response(
            {'error': 'اعلان یافت نشد'}, 
            status=status.HTTP_404_NOT_FOUND
        )

def get_device_type(user_agent):
    """Determine device type from user agent"""
    user_agent = user_agent.lower()
    
    if any(mobile in user_agent for mobile in ['mobile', 'android', 'iphone']):
        return 'mobile'
    elif any(tablet in user_agent for tablet in ['tablet', 'ipad']):
        return 'tablet'
    else:
        return 'desktop'

# Custom token refresh view with session tracking
class CustomTokenRefreshView(TokenRefreshView):
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        
        if response.status_code == 200:
            # Update session last activity
            try:
                refresh_token = request.data.get('refresh')
                if refresh_token:
                    refresh = RefreshToken(refresh_token)
                    user_id = refresh.payload.get('user_id')
                    
                    UserSession.objects.filter(
                        user_id=user_id,
                        is_active=True
                    ).update(last_activity=timezone.now())
            
            except Exception as e:
                logger.error(f"Token refresh session update error: {e}")
        
        return response