from rest_framework import serializers
from .models import User, OTPVerification

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'phone_number', 'username', 'email', 'first_name', 'last_name', 
                 'is_store_owner', 'is_customer', 'created_at']
        read_only_fields = ['id', 'created_at']

class OTPVerificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = OTPVerification
        fields = ['phone_number', 'otp_code', 'is_verified', 'created_at', 'expires_at']
        read_only_fields = ['otp_code', 'created_at', 'expires_at']