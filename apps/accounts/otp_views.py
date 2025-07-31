from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.conf import settings
from apps.accounts.otp_models import OTPCode, LoginAttempt
from apps.accounts.serializers import UserSerializer
from apps.communications.services import SMSService
import logging
import re

User = get_user_model()
logger = logging.getLogger(__name__)


def get_client_ip(request):
    """Get client IP address"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def normalize_phone_number(phone):
    """Normalize Iranian phone numbers"""
    # Remove all non-digit characters
    phone = re.sub(r'\D', '', phone)
    
    # Convert to standard format
    if phone.startswith('0098'):
        phone = phone[4:]
    elif phone.startswith('98'):
        phone = phone[2:]
    elif phone.startswith('0'):
        phone = phone[1:]
    
    # Add country code if needed
    if len(phone) == 10 and phone.startswith('9'):
        phone = '98' + phone
    
    return phone


@api_view(['POST'])
@permission_classes([AllowAny])
def send_otp(request):
    """
    Send OTP code to phone number
    Critical per product description: All logins are with OTP
    """
    try:
        phone_number = request.data.get('phone_number')
        code_type = request.data.get('code_type', 'login')
        
        if not phone_number:
            return Response({
                'error': 'شماره تلفن الزامی است'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Normalize phone number
        phone_number = normalize_phone_number(phone_number)
        
        # Validate Iranian mobile number format
        if not re.match(r'^989\d{9}$', phone_number):
            return Response({
                'error': 'شماره تلفن نامعتبر است'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check rate limiting
        client_ip = get_client_ip(request)
        if LoginAttempt.is_rate_limited(phone_number, client_ip):
            return Response({
                'error': 'تعداد تلاش‌های شما بیش از حد مجاز است. لطفاً بعداً تلاش کنید'
            }, status=status.HTTP_429_TOO_MANY_REQUESTS)
        
        # For register type, check if user already exists
        if code_type == 'register':
            if User.objects.filter(phone_number=phone_number).exists():
                return Response({
                    'error': 'کاربری با این شماره تلفن قبلاً ثبت‌نام کرده است'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # For login type, check if user exists
        elif code_type == 'login':
            if not User.objects.filter(phone_number=phone_number).exists():
                return Response({
                    'error': 'کاربری با این شماره تلفن یافت نشد'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create OTP
        otp = OTPCode.create_otp(phone_number, code_type)
        
        # Send SMS
        try:
            sms_service = SMSService()
            message = f"کد تایید مال: {otp.code}\nاین کد تا ۲ دقیقه معتبر است."
            
            sms_result = sms_service.send_sms(
                phone_number=phone_number,
                message=message
            )
            
            if not sms_result.get('success'):
                logger.error(f"SMS sending failed: {sms_result.get('error')}")
                return Response({
                    'error': 'خطا در ارسال پیامک. لطفاً دوباره تلاش کنید'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        except Exception as e:
            logger.error(f"SMS service error: {str(e)}")
            return Response({
                'error': 'خطا در ارسال پیامک'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Log attempt
        LoginAttempt.objects.create(
            phone_number=phone_number,
            ip_address=client_ip,
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            is_successful=False,  # Will be updated on successful verification
            otp_code=otp
        )
        
        logger.info(f"OTP sent to {phone_number} for {code_type}")
        
        return Response({
            'message': 'کد تایید با موفقیت ارسال شد',
            'expires_at': otp.expires_at.isoformat(),
            'phone_number': phone_number
        })
        
    except Exception as e:
        logger.error(f"Error in send_otp: {str(e)}")
        return Response({
            'error': 'خطای داخلی سرور'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def verify_otp(request):
    """
    Verify OTP code and authenticate user
    """
    try:
        phone_number = request.data.get('phone_number')
        code = request.data.get('code')
        code_type = request.data.get('code_type', 'login')
        
        if not phone_number or not code:
            return Response({
                'error': 'شماره تلفن و کد تایید الزامی است'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Normalize phone number
        phone_number = normalize_phone_number(phone_number)
        client_ip = get_client_ip(request)
        
        # Find OTP
        try:
            otp = OTPCode.objects.get(
                phone_number=phone_number,
                code=code,
                code_type=code_type,
                is_used=False
            )
        except OTPCode.DoesNotExist:
            # Log failed attempt
            LoginAttempt.objects.create(
                phone_number=phone_number,
                ip_address=client_ip,
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                is_successful=False
            )
            
            return Response({
                'error': 'کد تایید نامعتبر است'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if OTP is valid
        if not otp.is_valid():
            return Response({
                'error': 'کد تایید منقضی شده یا استفاده شده است'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Increment attempts
        otp.attempts += 1
        otp.save()
        
        # Handle different code types
        if code_type == 'register':
            # For registration, create new user
            user_data = request.data.get('user_data', {})
            
            if not user_data.get('first_name') or not user_data.get('last_name'):
                return Response({
                    'error': 'نام و نام خانوادگی الزامی است'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            user = User.objects.create_user(
                phone_number=phone_number,
                first_name=user_data.get('first_name'),
                last_name=user_data.get('last_name'),
                email=user_data.get('email', ''),
                is_phone_verified=True
            )
            
            # Update profile if additional data provided
            if user_data.get('is_store_owner'):
                user.is_store_owner = True
                user.save()
            
            logger.info(f"New user registered: {phone_number}")
            
        elif code_type == 'login':
            # For login, get existing user
            try:
                user = User.objects.get(phone_number=phone_number)
                
                # Mark phone as verified if not already
                if not user.is_phone_verified:
                    user.is_phone_verified = True
                    user.save()
                    
            except User.DoesNotExist:
                return Response({
                    'error': 'کاربر یافت نشد'
                }, status=status.HTTP_404_NOT_FOUND)
        
        # Mark OTP as used
        otp.is_used = True
        otp.save()
        
        # Update login attempt as successful
        LoginAttempt.objects.filter(
            phone_number=phone_number,
            otp_code=otp
        ).update(is_successful=True)
        
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        access = refresh.access_token
        
        # Update last login
        user.last_login = timezone.now()
        user.save()
        
        logger.info(f"User authenticated: {phone_number}")
        
        return Response({
            'message': 'ورود موفقیت‌آمیز',
            'access': str(access),
            'refresh': str(refresh),
            'user': UserSerializer(user).data,
            'is_new_user': code_type == 'register'
        })
        
    except Exception as e:
        logger.error(f"Error in verify_otp: {str(e)}")
        return Response({
            'error': 'خطای داخلی سرور'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def resend_otp(request):
    """
    Resend OTP code
    """
    try:
        phone_number = request.data.get('phone_number')
        code_type = request.data.get('code_type', 'login')
        
        if not phone_number:
            return Response({
                'error': 'شماره تلفن الزامی است'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Normalize phone number
        phone_number = normalize_phone_number(phone_number)
        
        # Check if last OTP was sent recently (prevent spam)
        last_otp = OTPCode.objects.filter(
            phone_number=phone_number,
            code_type=code_type
        ).order_by('-created_at').first()
        
        if last_otp:
            time_diff = timezone.now() - last_otp.created_at
            if time_diff.total_seconds() < 60:  # 60 seconds cooldown
                remaining = 60 - int(time_diff.total_seconds())
                return Response({
                    'error': f'لطفاً {remaining} ثانیه صبر کنید'
                }, status=status.HTTP_429_TOO_MANY_REQUESTS)
        
        # Use the same send_otp logic
        request.data['phone_number'] = phone_number
        request.data['code_type'] = code_type
        
        return send_otp(request)
        
    except Exception as e:
        logger.error(f"Error in resend_otp: {str(e)}")
        return Response({
            'error': 'خطای داخلی سرور'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def check_phone_exists(request):
    """
    Check if phone number is already registered
    """
    try:
        phone_number = request.data.get('phone_number')
        
        if not phone_number:
            return Response({
                'error': 'شماره تلفن الزامی است'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Normalize phone number
        phone_number = normalize_phone_number(phone_number)
        
        # Validate format
        if not re.match(r'^989\d{9}$', phone_number):
            return Response({
                'error': 'شماره تلفن نامعتبر است'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        exists = User.objects.filter(phone_number=phone_number).exists()
        
        return Response({
            'exists': exists,
            'phone_number': phone_number
        })
        
    except Exception as e:
        logger.error(f"Error in check_phone_exists: {str(e)}")
        return Response({
            'error': 'خطای داخلی سرور'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)