from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from django_tenants.admin import TenantAdminMixin
from .models import Tenant, Domain, TenantUser, OTPCode

@admin.register(Tenant)
class TenantAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = [
        'store_name', 'owner_name', 'owner_phone', 'plan_type', 
        'subscription_status', 'trial_status', 'is_active', 'created_at'
    ]
    list_filter = [
        'plan_type', 'on_trial', 'is_active', 'social_media_import_enabled',
        'sms_campaigns_enabled', 'created_at'
    ]
    search_fields = ['store_name', 'store_name_english', 'owner_name', 'owner_phone']
    ordering = ['-created_at']
    readonly_fields = ['schema_name', 'created_at', 'updated_at', 'subscription_status', 'trial_status']
    
    fieldsets = (
        ('اطلاعات فروشگاه', {
            'fields': (
                'store_name', 'store_name_english', 'description', 'schema_name'
            )
        }),
        ('اطلاعات مالک', {
            'fields': (
                'owner_name', 'owner_phone', 'owner_email'
            )
        }),
        ('اشتراک و پلن', {
            'fields': (
                'plan_type', 'paid_until', 'on_trial', 'trial_end_date',
                'subscription_status', 'trial_status'
            )
        }),
        ('محدودیت‌ها', {
            'fields': (
                'max_products', 'max_orders_per_month', 'custom_domain_allowed'
            )
        }),
        ('قابلیت‌ها', {
            'fields': (
                'social_media_import_enabled', 'sms_campaigns_enabled', 'analytics_enabled'
            )
        }),
        ('وضعیت', {
            'fields': (
                'is_active', 'created_at', 'updated_at'
            )
        }),
    )
    
    def subscription_status(self, obj):
        """Display subscription status with visual indicators"""
        if obj.on_trial:
            if obj.is_trial_expired:
                return format_html(
                    '<span style="color: #dc3545; font-weight: bold;">❌ آزمایشی منقضی</span>'
                )
            else:
                remaining = obj.get_remaining_trial_days()
                return format_html(
                    '<span style="color: #ffc107; font-weight: bold;">🔄 آزمایشی ({} روز باقی‌مانده)</span>',
                    remaining
                )
        else:
            if obj.is_subscription_active:
                return format_html(
                    '<span style="color: #28a745; font-weight: bold;">✅ فعال تا {}</span>',
                    obj.paid_until.strftime('%Y/%m/%d')
                )
            else:
                return format_html(
                    '<span style="color: #dc3545; font-weight: bold;">❌ منقضی شده</span>'
                )
    subscription_status.short_description = 'وضعیت اشتراک'
    
    def trial_status(self, obj):
        """Display trial status"""
        if not obj.on_trial:
            return format_html('<span style="color: #6c757d;">غیرآزمایشی</span>')
        
        if obj.is_trial_expired:
            return format_html('<span style="color: #dc3545;">منقضی شده</span>')
        
        remaining = obj.get_remaining_trial_days()
        if remaining <= 3:
            color = '#dc3545'  # Red for urgent
        elif remaining <= 7:
            color = '#ffc107'  # Yellow for warning
        else:
            color = '#28a745'  # Green for safe
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} روز باقی‌مانده</span>',
            color, remaining
        )
    trial_status.short_description = 'وضعیت آزمایشی'
    
    actions = ['extend_trial', 'activate_subscription', 'deactivate_stores']
    
    def extend_trial(self, request, queryset):
        """Extend trial period by 30 days"""
        updated = 0
        for tenant in queryset.filter(on_trial=True):
            if tenant.trial_end_date:
                tenant.trial_end_date = max(
                    tenant.trial_end_date + timezone.timedelta(days=30),
                    timezone.now().date() + timezone.timedelta(days=30)
                )
            else:
                tenant.trial_end_date = timezone.now().date() + timezone.timedelta(days=30)
            tenant.save()
            updated += 1
        
        self.message_user(request, f'{updated} فروشگاه دوره آزمایشی تمدید شد.')
    extend_trial.short_description = 'تمدید دوره آزمایشی (30 روز)'
    
    def activate_subscription(self, request, queryset):
        """Activate subscription for selected tenants"""
        updated = 0
        for tenant in queryset:
            tenant.on_trial = False
            tenant.paid_until = timezone.now().date() + timezone.timedelta(days=365)
            tenant.plan_type = 'basic'
            tenant.save()
            updated += 1
        
        self.message_user(request, f'{updated} فروشگاه فعال شد.')
    activate_subscription.short_description = 'فعال‌سازی اشتراک (1 سال)'
    
    def deactivate_stores(self, request, queryset):
        """Deactivate selected stores"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} فروشگاه غیرفعال شد.')
    deactivate_stores.short_description = 'غیرفعال‌سازی فروشگاه‌ها'

@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    list_display = [
        'domain', 'tenant', 'is_primary', 'is_custom', 
        'verification_status', 'ssl_enabled', 'created_at'
    ]
    list_filter = [
        'is_primary', 'is_custom', 'verification_status', 
        'ssl_enabled', 'created_at'
    ]
    search_fields = ['domain', 'tenant__store_name']
    ordering = ['-created_at']
    readonly_fields = ['verification_code', 'verified_at', 'created_at', 'updated_at']
    
    fieldsets = (
        ('اطلاعات دامنه', {
            'fields': ('domain', 'tenant', 'is_primary', 'is_custom')
        }),
        ('تنظیمات', {
            'fields': ('ssl_enabled',)
        }),
        ('تایید دامنه سفارشی', {
            'fields': (
                'verification_status', 'verification_code', 'verified_at'
            ),
            'classes': ('collapse',)
        }),
        ('تاریخ‌ها', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['generate_verification_codes', 'mark_as_verified']
    
    def generate_verification_codes(self, request, queryset):
        """Generate verification codes for custom domains"""
        updated = 0
        for domain in queryset.filter(is_custom=True, verification_status='pending'):
            domain.generate_verification_code()
            updated += 1
        
        self.message_user(request, f'{updated} کد تایید ایجاد شد.')
    generate_verification_codes.short_description = 'ایجاد کد تایید'
    
    def mark_as_verified(self, request, queryset):
        """Mark domains as verified"""
        updated = 0
        for domain in queryset.filter(verification_status__in=['pending', 'failed']):
            domain.mark_as_verified()
            updated += 1
        
        self.message_user(request, f'{updated} دامنه تایید شد.')
    mark_as_verified.short_description = 'تایید دامنه‌ها'

@admin.register(TenantUser)
class TenantUserAdmin(admin.ModelAdmin):
    list_display = [
        'phone_number', 'full_name', 'user_type', 
        'is_phone_verified', 'is_active', 'last_login'
    ]
    list_filter = [
        'user_type', 'is_phone_verified', 'is_active', 
        'language', 'date_joined'
    ]
    search_fields = ['phone_number', 'full_name', 'email']
    ordering = ['-date_joined']
    readonly_fields = [
        'last_login', 'date_joined', 'last_otp_sent', 
        'failed_login_attempts', 'account_locked_until'
    ]
    
    fieldsets = (
        ('اطلاعات ورود', {
            'fields': (
                'phone_number', 'is_phone_verified', 'password'
            )
        }),
        ('اطلاعات شخصی', {
            'fields': (
                'full_name', 'email', 'avatar', 'user_type'
            )
        }),
        ('تنظیمات', {
            'fields': (
                'language', 'timezone'
            )
        }),
        ('امنیت', {
            'fields': (
                'last_otp_sent', 'failed_login_attempts', 'account_locked_until'
            ),
            'classes': ('collapse',)
        }),
        ('وضعیت', {
            'fields': (
                'is_active', 'is_staff', 'is_superuser', 'last_login', 'date_joined'
            )
        }),
    )
    
    actions = ['unlock_accounts', 'verify_phone_numbers']
    
    def unlock_accounts(self, request, queryset):
        """Unlock selected user accounts"""
        updated = 0
        for user in queryset.filter(account_locked_until__isnull=False):
            user.unlock_account()
            updated += 1
        
        self.message_user(request, f'{updated} حساب کاربری آزاد شد.')
    unlock_accounts.short_description = 'آزادسازی حساب‌های کاربری'
    
    def verify_phone_numbers(self, request, queryset):
        """Verify phone numbers for selected users"""
        updated = queryset.update(is_phone_verified=True)
        self.message_user(request, f'{updated} شماره تلفن تایید شد.')
    verify_phone_numbers.short_description = 'تایید شماره تلفن'

@admin.register(OTPCode)
class OTPCodeAdmin(admin.ModelAdmin):
    list_display = [
        'phone_number', 'purpose', 'code', 'is_used', 
        'is_expired_display', 'created_at'
    ]
    list_filter = [
        'purpose', 'is_used', 'created_at'
    ]
    search_fields = ['phone_number', 'code']
    ordering = ['-created_at']
    readonly_fields = [
        'code', 'is_expired_display', 'created_at', 'expires_at', 
        'used_at', 'created_from_ip', 'used_from_ip'
    ]
    
    fieldsets = (
        ('اطلاعات کد', {
            'fields': (
                'phone_number', 'purpose', 'code', 'is_used'
            )
        }),
        ('زمان‌بندی', {
            'fields': (
                'created_at', 'expires_at', 'used_at', 'is_expired_display'
            )
        }),
        ('امنیت', {
            'fields': (
                'created_from_ip', 'used_from_ip'
            ),
            'classes': ('collapse',)
        }),
    )
    
    def is_expired_display(self, obj):
        """Display expiration status with visual indicators"""
        if obj.is_expired:
            return format_html('<span style="color: #dc3545;">❌ منقضی شده</span>')
        else:
            return format_html('<span style="color: #28a745;">✅ معتبر</span>')
    is_expired_display.short_description = 'وضعیت انقضا'
    
    def has_add_permission(self, request):
        return False  # Don't allow manual creation through admin
    
    def has_change_permission(self, request, obj=None):
        return False  # Don't allow editing OTP codes

# Customize admin site
admin.site.site_header = "مال - پنل مدیریت پلتفرم"
admin.site.site_title = "مال - مدیریت فروشگاه‌ها"
admin.site.index_title = "خوش آمدید به پنل مدیریت پلتفرم مال"
