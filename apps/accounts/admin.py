from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, OTPVerification

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('phone_number', 'username', 'is_store_owner', 'is_customer', 'created_at')
    list_filter = ('is_store_owner', 'is_customer', 'is_staff', 'is_active')
    search_fields = ('phone_number', 'username', 'email')
    ordering = ('-created_at',)
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Custom fields', {'fields': ('phone_number', 'is_store_owner', 'is_customer')}),
    )
    
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Custom fields', {'fields': ('phone_number', 'is_store_owner', 'is_customer')}),
    )

@admin.register(OTPVerification)
class OTPVerificationAdmin(admin.ModelAdmin):
    list_display = ('phone_number', 'otp_code', 'is_verified', 'created_at', 'expires_at')
    list_filter = ('is_verified', 'created_at')
    search_fields = ('phone_number',)
    readonly_fields = ('otp_code', 'created_at', 'expires_at')