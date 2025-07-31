from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import RegexValidator
from django.utils import timezone
from apps.accounts.otp_models import User, UserProfile, OTPCode, LoginAttempt
import uuid

# Re-export from otp_models to maintain compatibility
__all__ = ['User', 'UserProfile', 'OTPCode', 'LoginAttempt']

# Additional models that weren't in otp_models

class UserSession(models.Model):
    """
    Track user sessions for security and analytics
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    session_key = models.CharField(max_length=40, unique=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    device_info = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField()

    class Meta:
        verbose_name = "جلسه کاربر"
        verbose_name_plural = "جلسات کاربران"
        ordering = ['-last_activity']
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['session_key']),
            models.Index(fields=['expires_at']),
            models.Index(fields=['ip_address']),
        ]

    def __str__(self):
        return f"{self.user.first_name} - {self.ip_address}"

    def is_expired(self):
        return timezone.now() > self.expires_at

    def revoke(self):
        self.is_active = False
        self.save(update_fields=['is_active'])


class UserNotification(models.Model):
    """
    User notifications system
    """
    NOTIFICATION_TYPES = [
        ('order', 'سفارش'),
        ('payment', 'پرداخت'),
        ('promotion', 'تخفیف'),
        ('system', 'سیستم'),
        ('store', 'فروشگاه'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200, verbose_name="عنوان")
    message = models.TextField(verbose_name="پیام")
    notification_type = models.CharField(
        max_length=20, 
        choices=NOTIFICATION_TYPES, 
        default='system',
        verbose_name="نوع اعلان"
    )
    is_read = models.BooleanField(default=False, verbose_name="خوانده شده")
    is_sent_sms = models.BooleanField(default=False, verbose_name="پیامک ارسال شده")
    is_sent_email = models.BooleanField(default=False, verbose_name="ایمیل ارسال شده")
    action_url = models.URLField(blank=True, verbose_name="لینک اقدام")
    data = models.JSONField(default=dict, blank=True, verbose_name="داده‌های اضافی")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="زمان ایجاد")

    class Meta:
        verbose_name = "اعلان کاربر"
        verbose_name_plural = "اعلان‌های کاربران"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['notification_type']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.user.first_name} - {self.title}"

    def mark_as_read(self):
        self.is_read = True
        self.save(update_fields=['is_read'])


class UserAddress(models.Model):
    """
    User addresses for shipping
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses')
    title = models.CharField(max_length=100, verbose_name="عنوان آدرس")
    recipient_name = models.CharField(max_length=100, verbose_name="نام گیرنده")
    recipient_phone = models.CharField(max_length=15, verbose_name="تلفن گیرنده")
    address = models.TextField(verbose_name="آدرس کامل")
    city = models.CharField(max_length=100, verbose_name="شهر")
    state = models.CharField(max_length=100, verbose_name="استان")
    postal_code = models.CharField(max_length=10, verbose_name="کد پستی")
    latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    is_default = models.BooleanField(default=False, verbose_name="آدرس پیش‌فرض")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "آدرس کاربر"
        verbose_name_plural = "آدرس‌های کاربران"
        ordering = ['-is_default', '-created_at']
        indexes = [
            models.Index(fields=['user', 'is_default']),
            models.Index(fields=['city', 'state']),
        ]

    def __str__(self):
        return f"{self.user.first_name} - {self.title}"

    def save(self, *args, **kwargs):
        # Ensure only one default address per user
        if self.is_default:
            UserAddress.objects.filter(
                user=self.user, 
                is_default=True
            ).exclude(id=self.id).update(is_default=False)
        super().save(*args, **kwargs)


class UserPreferences(models.Model):
    """
    User preferences and settings
    """
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='preferences',
        primary_key=True
    )
    
    # Language and locale
    language = models.CharField(
        max_length=5, 
        default='fa',
        choices=[('fa', 'فارسی'), ('en', 'English')],
        verbose_name="زبان"
    )
    timezone = models.CharField(
        max_length=50, 
        default='Asia/Tehran',
        verbose_name="منطقه زمانی"
    )
    
    # Notification preferences
    email_notifications = models.BooleanField(default=True, verbose_name="اعلان‌های ایمیل")
    sms_notifications = models.BooleanField(default=True, verbose_name="اعلان‌های پیامکی")
    push_notifications = models.BooleanField(default=True, verbose_name="اعلان‌های فوری")
    marketing_emails = models.BooleanField(default=False, verbose_name="ایمیل‌های تبلیغاتی")
    
    # Shopping preferences
    currency = models.CharField(
        max_length=3, 
        default='IRR',
        choices=[('IRR', 'ریال'), ('USD', 'دلار')],
        verbose_name="واحد پول"
    )
    default_payment_method = models.CharField(
        max_length=50, 
        blank=True,
        verbose_name="روش پرداخت پیش‌فرض"
    )
    
    # Privacy settings
    profile_visibility = models.CharField(
        max_length=20,
        default='private',
        choices=[
            ('public', 'عمومی'),
            ('friends', 'دوستان'),
            ('private', 'خصوصی')
        ],
        verbose_name="نمایش پروفایل"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "تنظیمات کاربر"
        verbose_name_plural = "تنظیمات کاربران"

    def __str__(self):
        return f"تنظیمات {self.user.first_name} {self.user.last_name}"


# Signal handlers to create related models
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=User)
def create_user_preferences(sender, instance, created, **kwargs):
    """Create user preferences when user is created"""
    if created:
        UserPreferences.objects.get_or_create(user=instance)