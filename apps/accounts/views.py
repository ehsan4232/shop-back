from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from django.contrib.auth import authenticate
from django.utils import timezone
from django.core.cache import cache
from django.conf import settings
import logging

from .models import User, OTPVerification, UserSession
from .serializers import UserSerializer, OTPSerializer

logger = logging.getLogger(__name__)

@api_view(['POST'])
@permission_classes([AllowAny])
def send_otp(request):
    """Send OTP code to user's phone number"""
    phone = request.data.get('phone', '').strip()
    purpose = request.data.get('purpose', 'login')
    
    if not phone:
        return Response(
            {'error': 'شماره تلفن الزامی است'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Validate phone number format (Iranian mobile)
    if not phone.startswith('09') or len(phone) != 11:
        return Response(
            {'error': 'شماره تلفن نامعتبر است'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Rate limiting: max 3 OTP requests per phone per hour
    cache_key = f"otp_rate_limit_{phone}"
    attempts = cache.get(cache_key, 0)
    if attempts >= 3:
        return Response(
            {'error': 'حد مجاز درخواست کد تأیید. لطفاً یک ساعت دیگر تلاش کنید'}, 
            status=status.HTTP_429_TOO_MANY_REQUESTS
        )
    
    # Get or create user
    user, created = User.objects.get_or_create(
        phone=phone,
        defaults={
            'username': phone,  # Required by AbstractUser
            'is_verified': False
        }
    )
    
    # Invalidate previous OTP codes
    OTPVerification.objects.filter(
        phone=phone,
        is_used=False,
        is_verified=False
    ).update(is_used=True)
    
    # Create new OTP
    otp = OTPVerification.objects.create(
        user=user,
        phone=phone,
        purpose=purpose,
        ip_address=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
    )
    
    # TODO: Implement SMS sending with Kavenegar
    # For development, log the OTP code
    if settings.DEBUG:
        logger.info(f"OTP for {phone}: {otp.otp_code}")
    
    # Update rate limiting
    cache.set(cache_key, attempts + 1, 3600)  # 1 hour
    
    return Response({
        'message': 'کد تأیید ارسال شد',
        'expires_in': 300,  # 5 minutes
        'can_resend_in': 60  # 1 minute
    }, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([AllowAny])
def verify_otp(request):
    """Verify OTP code and authenticate user"""
    phone = request.data.get('phone', '').strip()
    code = request.data.get('code', '').strip()
    
    if not phone or not code:
        return Response(
            {'error': 'شماره تلفن و کد تأیید الزامی است'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # Get latest non-used OTP for this phone
        otp = OTPVerification.objects.filter(
            phone=phone,
            is_used=False
        ).latest('created_at')
        
        # Verify the code
        success, message = otp.verify(code)
        
        if success:
            user = otp.user
            
            # Mark user as verified on first successful login
            if not user.is_verified:
                user.is_verified = True
                user.last_login = timezone.now()
                user.last_login_ip = request.META.get('REMOTE_ADDR')
                user.save(update_fields=['is_verified', 'last_login', 'last_login_ip'])
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            access_token = refresh.access_token
            
            # Create user session record
            session_key = request.session.session_key or 'api_session'
            device_type = get_device_type(request.META.get('HTTP_USER_AGENT', ''))
            
            UserSession.objects.update_or_create(
                user=user,
                session_key=session_key,
                defaults={
                    'ip_address': request.META.get('REMOTE_ADDR', ''),
                    'user_agent': request.META.get('HTTP_USER_AGENT', '')[:500],
                    'device_type': device_type,
                    'is_active': True,
                    'last_activity': timezone.now()
                }
            )
            
            return Response({
                'access': str(access_token),
                'refresh': str(refresh),
                'expires_in': settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'].total_seconds(),
                'user': UserSerializer(user).data,
                'message': 'ورود موفقیت‌آمیز'
            }, status=status.HTTP_200_OK)
        
        else:
            return Response(
                {'error': message}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
    except OTPVerification.DoesNotExist:
        return Response(
            {'error': 'کد تأیید یافت نشد یا منقضی شده است'}, 
            status=status.HTTP_404_NOT_FOUND
        )

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
        logger.error(f"Logout error for user {request.user.phone}: {e}")
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
            'device_type': session.device_type,
            'ip_address': session.ip_address,
            'location': session.location,
            'is_active': session.is_active,
            'is_current': session.session_key == request.session.session_key,
            'last_activity': session.last_activity,
            'created_at': session.created_at
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
        session.is_active = False
        session.save()
        
        return Response(
            {'message': 'جلسه لغو شد'}, 
            status=status.HTTP_200_OK
        )
    
    except UserSession.DoesNotExist:
        return Response(
            {'error': 'جلسه یافت نشد'}, 
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
