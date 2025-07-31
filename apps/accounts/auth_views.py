from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from apps.accounts.models import UserProfile, OTPCode
from apps.core.utils import send_sms
import random
import string
from datetime import datetime, timedelta
from django.utils import timezone


class OTPRequestSerializer(serializers.Serializer):
    """
    Serializer for OTP request - supports phone number
    Product description requirement: "All logins in the platform are with otp"
    """
    phone_number = serializers.CharField(max_length=11, min_length=11)
    
    def validate_phone_number(self, value):
        """Validate Iranian phone number format"""
        if not value.startswith('09') or not value.isdigit():
            raise serializers.ValidationError('شماره تلفن همراه معتبر نیست')
        return value


class OTPVerifySerializer(serializers.Serializer):
    """
    Serializer for OTP verification
    """
    phone_number = serializers.CharField(max_length=11, min_length=11)
    otp_code = serializers.CharField(max_length=6, min_length=4)
    
    def validate(self, attrs):
        phone_number = attrs.get('phone_number')
        otp_code = attrs.get('otp_code')
        
        try:
            otp_obj = OTPCode.objects.get(
                phone_number=phone_number,
                code=otp_code,
                is_used=False,
                expires_at__gte=timezone.now()
            )
        except OTPCode.DoesNotExist:
            raise serializers.ValidationError('کد تأیید نامعتبر یا منقضی شده است')
        
        attrs['otp_obj'] = otp_obj
        return attrs


class StoreOwnerProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for store owner profile data
    """
    class Meta:
        model = UserProfile
        fields = [
            'first_name', 'last_name', 'business_name', 'national_id',
            'address', 'postal_code', 'is_store_owner', 'is_verified'
        ]


@api_view(['POST'])
def request_otp(request):
    """
    Request OTP for phone number
    Product description: "All logins in the platform are with otp"
    """
    serializer = OTPRequestSerializer(data=request.data)
    if serializer.is_valid():
        phone_number = serializer.validated_data['phone_number']
        
        # Generate random 5-digit OTP
        otp_code = ''.join(random.choices(string.digits, k=5))
        
        # Check if there's a recent unused OTP
        recent_otp = OTPCode.objects.filter(
            phone_number=phone_number,
            created_at__gte=timezone.now() - timedelta(minutes=2)
        ).first()
        
        if recent_otp:
            return Response({
                'error': 'لطفاً ۲ دقیقه صبر کنید قبل از درخواست کد جدید'
            }, status=429)
        
        # Create OTP record
        otp_obj = OTPCode.objects.create(
            phone_number=phone_number,
            code=otp_code,
            expires_at=timezone.now() + timedelta(minutes=5)  # 5 minutes expiry
        )
        
        # Send SMS (integrate with Iranian SMS providers)
        sms_text = f'کد تأیید مال: {otp_code}\nاین کد تا ۵ دقیقه معتبر است.'
        try:
            send_sms(phone_number, sms_text)
            return Response({
                'message': 'کد تأیید ارسال شد',
                'expires_in': 300  # 5 minutes in seconds
            })
        except Exception as e:
            # For development, return the OTP in response
            return Response({
                'message': 'کد تأیید ارسال شد',
                'expires_in': 300,
                'dev_otp': otp_code  # Remove in production
            })
    
    return Response(serializer.errors, status=400)


@api_view(['POST'])
def verify_otp(request):
    """
    Verify OTP and authenticate user
    Product description requirement: OTP-based authentication
    """
    serializer = OTPVerifySerializer(data=request.data)
    if serializer.is_valid():
        phone_number = serializer.validated_data['phone_number']
        otp_obj = serializer.validated_data['otp_obj']
        
        # Mark OTP as used
        otp_obj.is_used = True
        otp_obj.save()
        
        # Get or create user
        try:
            user_profile = UserProfile.objects.get(phone_number=phone_number)
            user = user_profile.user
        except UserProfile.DoesNotExist:
            # Create new user and profile
            username = f"user_{phone_number}"
            user = User.objects.create_user(username=username)
            user_profile = UserProfile.objects.create(
                user=user,
                phone_number=phone_number
            )
        
        # Generate JWT token or session
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'message': 'ورود موفقیت‌آمیز',
            'user': {
                'id': user.id,
                'phone_number': phone_number,
                'is_store_owner': user_profile.is_store_owner,
                'is_verified': user_profile.is_verified,
                'business_name': user_profile.business_name,
            },
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        })
    
    return Response(serializer.errors, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def complete_store_owner_profile(request):
    """
    Complete store owner profile after OTP verification
    """
    user_profile = request.user.userprofile
    serializer = StoreOwnerProfileSerializer(user_profile, data=request.data, partial=True)
    
    if serializer.is_valid():
        serializer.save()
        
        # Mark as store owner if business name is provided
        if serializer.validated_data.get('business_name'):
            user_profile.is_store_owner = True
            user_profile.save()
            
            # Create store if needed
            from apps.stores.models import Store
            if not hasattr(user_profile, 'stores') or not user_profile.stores.exists():
                Store.objects.create(
                    owner=user_profile,
                    name=serializer.validated_data['business_name'],
                    is_active=True
                )
        
        return Response({
            'message': 'پروفایل با موفقیت تکمیل شد',
            'profile': serializer.data
        })
    
    return Response(serializer.errors, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    """
    Logout user (invalidate tokens)
    """
    try:
        refresh_token = request.data.get("refresh")
        if refresh_token:
            from rest_framework_simplejwt.tokens import RefreshToken
            token = RefreshToken(refresh_token)
            token.blacklist()
        return Response({'message': 'خروج موفقیت‌آمیز'})
    except Exception:
        return Response({'error': 'خطا در خروج'}, status=400)