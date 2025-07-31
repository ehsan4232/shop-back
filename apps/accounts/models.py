from django.db import models
from django.core.validators import RegexValidator
from apps.core.mixins import TimestampMixin
import uuid


class OTPCode(TimestampMixin):
    """
    OTP codes for phone-based authentication
    Product description requirement: "All logins in the platform are with otp"
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    phone_validator = RegexValidator(
        regex=r'^09\d{9}$',
        message='شماره تلفن همراه باید به صورت 09xxxxxxxxx باشد'
    )
    
    phone_number = models.CharField(
        max_length=11, 
        validators=[phone_validator],
        verbose_name='شماره تلفن همراه'
    )
    code = models.CharField(max_length=6, verbose_name='کد تأیید')
    expires_at = models.DateTimeField(verbose_name='تاریخ انقضا')
    is_used = models.BooleanField(default=False, verbose_name='استفاده شده')
    
    # Tracking fields for security
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    attempts = models.PositiveIntegerField(default=0, verbose_name='تعداد تلاش')
    
    class Meta:
        verbose_name = 'کد تأیید'
        verbose_name_plural = 'کدهای تأیید'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['phone_number', 'code']),
            models.Index(fields=['expires_at']),
            models.Index(fields=['is_used']),
        ]
    
    def __str__(self):
        return f'{self.phone_number} - {self.code}'
    
    def is_expired(self):
        from django.utils import timezone
        return timezone.now() > self.expires_at
    
    def is_valid(self):
        return not self.is_used and not self.is_expired()


class UserProfile(TimestampMixin):
    """
    Extended user profile for store owners and customers
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField('auth.User', on_delete=models.CASCADE, related_name='userprofile')
    
    # Contact information
    phone_validator = RegexValidator(
        regex=r'^09\d{9}$',
        message='شماره تلفن همراه باید به صورت 09xxxxxxxxx باشد'
    )
    phone_number = models.CharField(
        max_length=11, 
        unique=True,
        validators=[phone_validator],
        verbose_name='شماره تلفن همراه'
    )
    
    # Personal information
    first_name = models.CharField(max_length=50, blank=True, verbose_name='نام')
    last_name = models.CharField(max_length=50, blank=True, verbose_name='نام خانوادگی')
    national_id = models.CharField(
        max_length=10, 
        blank=True, 
        validators=[RegexValidator(r'^\d{10}$', 'کد ملی باید ۱۰ رقم باشد')],
        verbose_name='کد ملی'
    )
    
    # Business information
    business_name = models.CharField(max_length=100, blank=True, verbose_name='نام تجاری')
    business_type = models.CharField(max_length=50, blank=True, verbose_name='نوع کسب‌وکار')
    
    # Address
    address = models.TextField(blank=True, verbose_name='آدرس')
    city = models.CharField(max_length=50, blank=True, verbose_name='شهر')
    state = models.CharField(max_length=50, blank=True, verbose_name='استان')
    postal_code = models.CharField(max_length=10, blank=True, verbose_name='کد پستی')
    
    # Profile status
    is_store_owner = models.BooleanField(default=False, verbose_name='صاحب فروشگاه')
    is_verified = models.BooleanField(default=False, verbose_name='تأیید شده')
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    
    # Avatar
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True, verbose_name='تصویر پروفایل')
    
    # Settings
    email_notifications = models.BooleanField(default=True, verbose_name='اعلان‌های ایمیل')
    sms_notifications = models.BooleanField(default=True, verbose_name='اعلان‌های پیامک')
    
    # Verification dates
    phone_verified_at = models.DateTimeField(null=True, blank=True)
    email_verified_at = models.DateTimeField(null=True, blank=True)
    business_verified_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = 'پروفایل کاربر'
        verbose_name_plural = 'پروفایل‌های کاربران'
        indexes = [
            models.Index(fields=['phone_number']),
            models.Index(fields=['is_store_owner']),
            models.Index(fields=['is_verified']),
            models.Index(fields=['business_name']),
        ]
    
    def __str__(self):
        if self.first_name and self.last_name:
            return f'{self.first_name} {self.last_name}'
        elif self.business_name:
            return self.business_name
        return self.phone_number
    
    @property
    def full_name(self):
        if self.first_name and self.last_name:
            return f'{self.first_name} {self.last_name}'
        return self.business_name or self.phone_number
    
    def verify_phone(self):
        """Mark phone as verified"""
        from django.utils import timezone
        self.phone_verified_at = timezone.now()
        self.save(update_fields=['phone_verified_at'])
    
    def verify_business(self):
        """Mark business as verified"""
        from django.utils import timezone
        self.business_verified_at = timezone.now()
        self.is_verified = True
        self.save(update_fields=['business_verified_at', 'is_verified'])


class LoginAttempt(TimestampMixin):
    """
    Track login attempts for security
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    phone_number = models.CharField(max_length=11, verbose_name='شماره تلفن')
    ip_address = models.GenericIPAddressField(verbose_name='آدرس IP')
    user_agent = models.TextField(verbose_name='User Agent')
    success = models.BooleanField(default=False, verbose_name='موفق')
    failure_reason = models.CharField(max_length=100, blank=True, verbose_name='دلیل عدم موفقیت')
    
    class Meta:
        verbose_name = 'تلاش ورود'
        verbose_name_plural = 'تلاش‌های ورود'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['phone_number', '-created_at']),
            models.Index(fields=['ip_address', '-created_at']),
            models.Index(fields=['success']),
        ]
    
    def __str__(self):
        return f'{self.phone_number} - {"موفق" if self.success else "ناموفق"}'


# Signal handlers for user creation
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create UserProfile when User is created"""
    if created and not hasattr(instance, 'userprofile'):
        UserProfile.objects.create(user=instance)