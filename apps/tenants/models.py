# Multi-tenancy implementation for Mall platform
# Implements the core requirement: "platform for building websites for stores"

from django.db import models
from django_tenants.models import TenantMixin, DomainMixin
from django.core.validators import RegexValidator
from django.utils import timezone
from django.contrib.auth.models import AbstractUser
import uuid

class Tenant(TenantMixin):
    """
    Tenant model for store isolation
    Each store gets its own schema for complete data isolation
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Store Information
    store_name = models.CharField(max_length=100, verbose_name='نام فروشگاه')
    store_name_english = models.CharField(max_length=100, verbose_name='نام انگلیسی فروشگاه')
    description = models.TextField(blank=True, verbose_name='توضیحات فروشگاه')
    
    # Owner Information
    owner_name = models.CharField(max_length=100, verbose_name='نام مالک')
    phone_regex = RegexValidator(
        regex=r'^09\d{9}$',
        message="شماره تلفن باید به فرمت 09xxxxxxxxx باشد"
    )
    owner_phone = models.CharField(
        validators=[phone_regex], 
        max_length=11, 
        verbose_name='شماره تلفن مالک'
    )
    owner_email = models.EmailField(blank=True, verbose_name='ایمیل مالک')
    
    # Subscription Information
    plan_type = models.CharField(
        max_length=20,
        choices=[
            ('trial', 'آزمایشی'),
            ('basic', 'پایه'),
            ('premium', 'پریمیوم'),
            ('enterprise', 'سازمانی')
        ],
        default='trial',
        verbose_name='نوع پلن'
    )
    paid_until = models.DateField(verbose_name='پرداخت تا تاریخ')
    on_trial = models.BooleanField(default=True, verbose_name='در دوره آزمایشی')
    trial_end_date = models.DateField(null=True, blank=True, verbose_name='پایان دوره آزمایشی')
    
    # Store Configuration
    max_products = models.IntegerField(default=100, verbose_name='حداکثر تعداد محصولات')
    max_orders_per_month = models.IntegerField(default=1000, verbose_name='حداکثر سفارش در ماه')
    custom_domain_allowed = models.BooleanField(default=False, verbose_name='مجاز به دامنه سفارشی')
    
    # Features Enabled
    social_media_import_enabled = models.BooleanField(default=True, verbose_name='واردات از شبکه اجتماعی')
    sms_campaigns_enabled = models.BooleanField(default=False, verbose_name='کمپین پیامکی')
    analytics_enabled = models.BooleanField(default=True, verbose_name='آنالیتیکس')
    
    # Status
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاریخ بروزرسانی')
    
    # Auto-create schema when tenant is saved
    auto_create_schema = True
    
    class Meta:
        verbose_name = 'فروشگاه'
        verbose_name_plural = 'فروشگاه‌ها'
        
    def __str__(self):
        return self.store_name
    
    @property
    def is_trial_expired(self):
        """Check if trial period has expired"""
        if not self.on_trial or not self.trial_end_date:
            return False
        return timezone.now().date() > self.trial_end_date
    
    @property
    def is_subscription_active(self):
        """Check if subscription is active"""
        if self.on_trial:
            return not self.is_trial_expired
        return timezone.now().date() <= self.paid_until
    
    def get_remaining_trial_days(self):
        """Get remaining trial days"""
        if not self.on_trial or not self.trial_end_date:
            return 0
        remaining = (self.trial_end_date - timezone.now().date()).days
        return max(0, remaining)
    
    def upgrade_plan(self, new_plan: str, paid_until: str):
        """Upgrade tenant plan"""
        self.plan_type = new_plan
        self.paid_until = paid_until
        self.on_trial = False
        self.trial_end_date = None
        
        # Update limits based on plan
        plan_limits = {
            'basic': {'max_products': 500, 'max_orders_per_month': 5000},
            'premium': {'max_products': 2000, 'max_orders_per_month': 20000},
            'enterprise': {'max_products': -1, 'max_orders_per_month': -1}  # Unlimited
        }
        
        if new_plan in plan_limits:
            limits = plan_limits[new_plan]
            self.max_products = limits['max_products']
            self.max_orders_per_month = limits['max_orders_per_month']
            
            # Enable premium features
            if new_plan in ['premium', 'enterprise']:
                self.custom_domain_allowed = True
                self.sms_campaigns_enabled = True
        
        self.save()

class Domain(DomainMixin):
    """
    Domain model for tenant routing
    Supports both subdomains and custom domains
    """
    # Additional fields for Mall platform
    is_primary = models.BooleanField(default=False, verbose_name='دامنه اصلی')
    is_custom = models.BooleanField(default=False, verbose_name='دامنه سفارشی')
    ssl_enabled = models.BooleanField(default=True, verbose_name='SSL فعال')
    
    # Custom domain verification
    verification_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'در انتظار تایید'),
            ('verified', 'تایید شده'),
            ('failed', 'ناموفق')
        ],
        default='pending',
        verbose_name='وضعیت تایید'
    )
    verification_code = models.CharField(max_length=50, blank=True, verbose_name='کد تایید')
    verified_at = models.DateTimeField(null=True, blank=True, verbose_name='تاریخ تایید')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاریخ بروزرسانی')
    
    class Meta:
        verbose_name = 'دامنه'
        verbose_name_plural = 'دامنه‌ها'
        
    def __str__(self):
        return self.domain
    
    def generate_verification_code(self):
        """Generate verification code for custom domains"""
        import secrets
        self.verification_code = secrets.token_urlsafe(32)
        self.save(update_fields=['verification_code'])
        return self.verification_code
    
    def mark_as_verified(self):
        """Mark domain as verified"""
        self.verification_status = 'verified'
        self.verified_at = timezone.now()
        self.save(update_fields=['verification_status', 'verified_at'])

# Enhanced User model for multi-tenancy
class TenantUser(AbstractUser):
    """
    Enhanced user model for Mall platform
    Supports OTP authentication and tenant association
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Phone-based authentication (per product description: "All logins are with OTP")
    phone_regex = RegexValidator(
        regex=r'^09\d{9}$',
        message="شماره تلفن باید به فرمت 09xxxxxxxxx باشد"
    )
    phone_number = models.CharField(
        validators=[phone_regex], 
        max_length=11, 
        unique=True,
        verbose_name='شماره تلفن'
    )
    is_phone_verified = models.BooleanField(default=False, verbose_name='تلفن تایید شده')
    
    # User type
    user_type = models.CharField(
        max_length=20,
        choices=[
            ('platform_admin', 'مدیر پلتفرم'),
            ('store_owner', 'مالک فروشگاه'),
            ('store_staff', 'کارمند فروشگاه'),
            ('customer', 'مشتری')
        ],
        default='store_owner',
        verbose_name='نوع کاربر'
    )
    
    # Profile information
    full_name = models.CharField(max_length=100, blank=True, verbose_name='نام کامل')
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True, verbose_name='تصویر پروفایل')
    
    # Preferences
    language = models.CharField(
        max_length=10,
        choices=[('fa', 'فارسی'), ('en', 'English')],
        default='fa',
        verbose_name='زبان'
    )
    timezone = models.CharField(max_length=50, default='Asia/Tehran', verbose_name='منطقه زمانی')
    
    # Security
    last_otp_sent = models.DateTimeField(null=True, blank=True, verbose_name='آخرین ارسال کد')
    failed_login_attempts = models.IntegerField(default=0, verbose_name='تلاش‌های ناموفق ورود')
    account_locked_until = models.DateTimeField(null=True, blank=True, verbose_name='قفل حساب تا')
    
    # Override username field to use phone number
    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = []
    
    class Meta:
        verbose_name = 'کاربر'
        verbose_name_plural = 'کاربران'
        
    def __str__(self):
        return f"{self.full_name} ({self.phone_number})"
    
    @property
    def is_account_locked(self):
        """Check if account is currently locked"""
        if not self.account_locked_until:
            return False
        return timezone.now() < self.account_locked_until
    
    def lock_account(self, duration_minutes=30):
        """Lock account for specified duration"""
        self.account_locked_until = timezone.now() + timezone.timedelta(minutes=duration_minutes)
        self.save(update_fields=['account_locked_until'])
    
    def unlock_account(self):
        """Unlock account and reset failed attempts"""
        self.account_locked_until = None
        self.failed_login_attempts = 0
        self.save(update_fields=['account_locked_until', 'failed_login_attempts'])

class OTPCode(models.Model):
    """
    OTP codes for phone number verification
    Implements product description requirement: "All logins in the platform are with otp"
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    phone_number = models.CharField(max_length=11, verbose_name='شماره تلفن')
    code = models.CharField(max_length=6, verbose_name='کد تایید')
    
    # OTP purpose
    purpose = models.CharField(
        max_length=20,
        choices=[
            ('login', 'ورود'),
            ('register', 'ثبت‌نام'),
            ('password_reset', 'بازیابی رمز عبور'),
            ('phone_verification', 'تایید شماره تلفن')
        ],
        default='login',
        verbose_name='هدف'
    )
    
    # Status
    is_used = models.BooleanField(default=False, verbose_name='استفاده شده')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    expires_at = models.DateTimeField(verbose_name='تاریخ انقضا')
    used_at = models.DateTimeField(null=True, blank=True, verbose_name='تاریخ استفاده')
    
    # IP tracking for security
    created_from_ip = models.GenericIPAddressField(null=True, blank=True, verbose_name='IP ایجاد')
    used_from_ip = models.GenericIPAddressField(null=True, blank=True, verbose_name='IP استفاده')
    
    class Meta:
        verbose_name = 'کد تایید'
        verbose_name_plural = 'کدهای تایید'
        indexes = [
            models.Index(fields=['phone_number', 'purpose', '-created_at']),
            models.Index(fields=['code', 'expires_at']),
            models.Index(fields=['is_used', 'expires_at']),
        ]
        
    def __str__(self):
        return f"{self.phone_number} - {self.get_purpose_display()}"
    
    def save(self, *args, **kwargs):
        if not self.code:
            import random
            self.code = str(random.randint(100000, 999999))
        
        if not self.expires_at:
            # OTP expires in 5 minutes
            self.expires_at = timezone.now() + timezone.timedelta(minutes=5)
        
        super().save(*args, **kwargs)
    
    @property
    def is_expired(self):
        """Check if OTP has expired"""
        return timezone.now() > self.expires_at
    
    @property
    def is_valid(self):
        """Check if OTP is valid (not used and not expired)"""
        return not self.is_used and not self.is_expired
    
    def mark_as_used(self, ip_address=None):
        """Mark OTP as used"""
        self.is_used = True
        self.used_at = timezone.now()
        if ip_address:
            self.used_from_ip = ip_address
        self.save(update_fields=['is_used', 'used_at', 'used_from_ip'])
    
    @classmethod
    def create_otp(cls, phone_number: str, purpose: str = 'login', ip_address: str = None):
        """Create new OTP code"""
        # Invalidate any existing unused OTPs for this phone/purpose
        cls.objects.filter(
            phone_number=phone_number,
            purpose=purpose,
            is_used=False
        ).update(is_used=True, used_at=timezone.now())
        
        # Create new OTP
        otp = cls.objects.create(
            phone_number=phone_number,
            purpose=purpose,
            created_from_ip=ip_address
        )
        
        return otp
    
    @classmethod
    def verify_otp(cls, phone_number: str, code: str, purpose: str = 'login', ip_address: str = None):
        """Verify OTP code"""
        try:
            otp = cls.objects.get(
                phone_number=phone_number,
                code=code,
                purpose=purpose,
                is_used=False
            )
            
            if otp.is_expired:
                return False, 'کد تایید منقضی شده است'
            
            otp.mark_as_used(ip_address)
            return True, 'کد تایید معتبر است'
            
        except cls.DoesNotExist:
            return False, 'کد تایید نامعتبر است'
