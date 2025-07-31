from rest_framework import serializers
from django.contrib.auth import get_user_model
from apps.accounts.otp_models import OTPCode, UserProfile, LoginAttempt

User = get_user_model()


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profile"""
    
    class Meta:
        model = UserProfile
        fields = [
            'date_of_birth', 'gender', 'avatar', 'bio',
            'address', 'city', 'state', 'postal_code',
            'email_notifications', 'sms_notifications'
        ]
        extra_kwargs = {
            'avatar': {'required': False},
        }


class UserSerializer(serializers.ModelSerializer):
    """
    User serializer for API responses
    Includes profile information
    """
    profile = UserProfileSerializer(read_only=True)
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'phone_number', 'first_name', 'last_name', 'email',
            'is_phone_verified', 'is_store_owner', 'is_active',
            'date_joined', 'last_login', 'profile', 'full_name'
        ]
        read_only_fields = [
            'id', 'phone_number', 'is_phone_verified', 'date_joined', 'last_login'
        ]
    
    def get_full_name(self, obj):
        """Get user's full name"""
        return f"{obj.first_name} {obj.last_name}".strip()


class UserUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user information"""
    profile = UserProfileSerializer(required=False)
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'profile']
    
    def update(self, instance, validated_data):
        """Update user and profile"""
        profile_data = validated_data.pop('profile', {})
        
        # Update user fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update profile
        if profile_data:
            profile = instance.profile
            for attr, value in profile_data.items():
                setattr(profile, attr, value)
            profile.save()
        
        return instance


class OTPCodeSerializer(serializers.ModelSerializer):
    """Serializer for OTP codes (admin use)"""
    
    class Meta:
        model = OTPCode
        fields = [
            'id', 'phone_number', 'code_type', 'is_used',
            'created_at', 'expires_at', 'attempts'
        ]
        read_only_fields = ['id', 'created_at']


class LoginAttemptSerializer(serializers.ModelSerializer):
    """Serializer for login attempts (admin use)"""
    
    class Meta:
        model = LoginAttempt
        fields = [
            'id', 'phone_number', 'ip_address', 'is_successful',
            'created_at', 'user_agent'
        ]
        read_only_fields = ['id', 'created_at']


class SendOTPSerializer(serializers.Serializer):
    """Serializer for sending OTP request"""
    phone_number = serializers.CharField(max_length=15)
    code_type = serializers.ChoiceField(
        choices=['login', 'register', 'password_reset', 'phone_verify'],
        default='login'
    )
    
    def validate_phone_number(self, value):
        """Validate Iranian phone number format"""
        import re
        
        # Remove all non-digit characters
        digits = re.sub(r'\D', '', value)
        
        # Check various Iranian mobile formats
        if not re.match(r'^((\+98|0098|98|0)?9\d{9})$', value):
            raise serializers.ValidationError("شماره تلفن نامعتبر است")
        
        return value


class VerifyOTPSerializer(serializers.Serializer):
    """Serializer for verifying OTP"""
    phone_number = serializers.CharField(max_length=15)
    code = serializers.CharField(max_length=6, min_length=6)
    code_type = serializers.ChoiceField(
        choices=['login', 'register', 'password_reset', 'phone_verify'],
        default='login'
    )
    user_data = serializers.DictField(required=False)
    
    def validate_code(self, value):
        """Validate OTP code format"""
        if not value.isdigit():
            raise serializers.ValidationError("کد تایید باید شامل اعداد باشد")
        return value
    
    def validate(self, attrs):
        """Cross-field validation"""
        code_type = attrs.get('code_type')
        user_data = attrs.get('user_data', {})
        
        # For registration, require user data
        if code_type == 'register':
            if not user_data.get('first_name'):
                raise serializers.ValidationError({
                    'user_data': 'نام الزامی است'
                })
            if not user_data.get('last_name'):
                raise serializers.ValidationError({
                    'user_data': 'نام خانوادگی الزامی است'
                })
        
        return attrs


class CheckPhoneSerializer(serializers.Serializer):
    """Serializer for checking if phone exists"""
    phone_number = serializers.CharField(max_length=15)
    
    def validate_phone_number(self, value):
        """Validate Iranian phone number format"""
        import re
        
        if not re.match(r'^((\+98|0098|98|0)?9\d{9})$', value):
            raise serializers.ValidationError("شماره تلفن نامعتبر است")
        
        return value