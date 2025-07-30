from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from .models import User, OTPVerification, UserNotification
from apps.core.validators import MallValidators

class UserRegistrationSerializer(serializers.ModelSerializer):
    """Complete user registration with validation"""
    password = serializers.CharField(write_only=True, validators=[validate_password])
    confirm_password = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = [
            'phone', 'first_name', 'last_name', 'email', 
            'password', 'confirm_password'
        ]
    
    def validate_phone(self, value):
        """Validate Iranian phone number"""
        return MallValidators.validate_iranian_phone(value)
    
    def validate(self, attrs):
        """Validate password confirmation"""
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError("رمز عبور و تکرار آن یکسان نیستند")
        return attrs
    
    def create(self, validated_data):
        """Create user with proper validation"""
        validated_data.pop('confirm_password')
        user = User.objects.create_user(**validated_data)
        return user

class UserLoginSerializer(serializers.Serializer):
    """User login with OTP support"""
    phone = serializers.CharField()
    password = serializers.CharField(required=False)
    otp_code = serializers.CharField(required=False)
    
    def validate_phone(self, value):
        return MallValidators.validate_iranian_phone(value)
    
    def validate(self, attrs):
        phone = attrs.get('phone')
        password = attrs.get('password')
        otp_code = attrs.get('otp_code')
        
        if not password and not otp_code:
            raise serializers.ValidationError("رمز عبور یا کد تأیید الزامی است")
        
        # Try password authentication first
        if password:
            user = authenticate(username=phone, password=password)
            if user:
                attrs['user'] = user
                return attrs
        
        # Try OTP authentication
        if otp_code:
            try:
                otp = OTPVerification.objects.get(
                    phone=phone,
                    otp_code=otp_code,
                    is_verified=False,
                    purpose='login'
                )
                is_valid, message = otp.verify(otp_code)
                if is_valid:
                    user = User.objects.get(phone=phone)
                    attrs['user'] = user
                    return attrs
                else:
                    raise serializers.ValidationError(message)
            except OTPVerification.DoesNotExist:
                raise serializers.ValidationError("کد تأیید معتبر نیست")
        
        raise serializers.ValidationError("اطلاعات ورود صحیح نیست")

class OTPRequestSerializer(serializers.Serializer):
    """Request OTP for various purposes"""
    phone = serializers.CharField()
    purpose = serializers.ChoiceField(choices=[
        ('login', 'ورود'),
        ('register', 'ثبت‌نام'),
        ('password_reset', 'بازیابی رمز عبور'),
        ('phone_verification', 'تأیید شماره تلفن')
    ])
    
    def validate_phone(self, value):
        return MallValidators.validate_iranian_phone(value)

class OTPVerifySerializer(serializers.Serializer):
    """Verify OTP code"""
    phone = serializers.CharField()
    otp_code = serializers.CharField(max_length=6, min_length=6)
    purpose = serializers.CharField()
    
    def validate_phone(self, value):
        return MallValidators.validate_iranian_phone(value)
    
    def validate(self, attrs):
        try:
            otp = OTPVerification.objects.get(
                phone=attrs['phone'],
                otp_code=attrs['otp_code'],
                purpose=attrs['purpose'],
                is_verified=False
            )
            
            is_valid, message = otp.verify(attrs['otp_code'])
            if not is_valid:
                raise serializers.ValidationError(message)
            
            attrs['otp'] = otp
            return attrs
            
        except OTPVerification.DoesNotExist:
            raise serializers.ValidationError("کد تأیید معتبر نیست")

class UserSerializer(serializers.ModelSerializer):
    """Complete user serializer"""
    full_name = serializers.ReadOnlyField()
    
    class Meta:
        model = User
        fields = [
            'id', 'phone', 'username', 'email', 'first_name', 'last_name',
            'full_name', 'is_store_owner', 'is_customer', 'is_verified',
            'avatar', 'birth_date', 'gender', 'city', 'state', 'address',
            'postal_code', 'language', 'timezone', 'accepts_marketing',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'full_name']

class UserUpdateSerializer(serializers.ModelSerializer):
    """Update user profile"""
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'email', 'avatar', 'birth_date',
            'gender', 'city', 'state', 'address', 'postal_code',
            'language', 'timezone', 'accepts_marketing'
        ]

class PasswordChangeSerializer(serializers.Serializer):
    """Change user password"""
    old_password = serializers.CharField()
    new_password = serializers.CharField(validators=[validate_password])
    confirm_password = serializers.CharField()
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError("رمز عبور جدید و تکرار آن یکسان نیستند")
        return attrs
    
    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("رمز عبور فعلی صحیح نیست")
        return value

class UserNotificationSerializer(serializers.ModelSerializer):
    """User notifications"""
    class Meta:
        model = UserNotification
        fields = [
            'id', 'title', 'message', 'notification_type', 'is_read',
            'action_url', 'data', 'created_at', 'read_at'
        ]
        read_only_fields = ['id', 'created_at', 'read_at']

class OTPVerificationSerializer(serializers.ModelSerializer):
    """OTP verification display"""
    class Meta:
        model = OTPVerification
        fields = ['phone', 'purpose', 'is_verified', 'created_at', 'expires_at']
        read_only_fields = ['created_at', 'expires_at']