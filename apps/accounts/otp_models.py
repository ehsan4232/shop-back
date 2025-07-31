from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.core.validators import RegexValidator
import random
import string
from datetime import timedelta


class User(AbstractUser):
    """
    Extended user model with phone number as primary identifier
    Per product description: All logins are with OTP
    """
    phone_regex = RegexValidator(
        regex=r'^(\+98|0)?9\d{9}$',
        message="شماره تلفن باید در قالب صحیح ایرانی باشد"
    )
    
    phone_number = models.CharField(
        max_length=15,
        validators=[phone_regex],
        unique=True,
        verbose_name="شماره تلفن"
    )
    is_phone_verified = models.BooleanField(default=False, verbose_name="تلفن تایید شده")
    is_store_owner = models.BooleanField(default=False, verbose_name="صاحب فروشگاه")
    
    # Remove username requirement - we use phone number
    username = None
    
    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    class Meta:
        verbose_name = "کاربر"
        verbose_name_plural = "کاربران"

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.phone_number})"


class OTPCode(models.Model):
    """
    OTP codes for phone verification
    Critical per product description: All logins are with OTP
    """
    CODE_TYPES = [
        ('login', 'ورود'),
        ('register', 'ثبت‌نام'),
        ('password_reset', 'بازیابی رمز عبور'),
        ('phone_verify', 'تایید شماره تلفن'),
    ]
    
    phone_number = models.CharField(
        max_length=15,
        verbose_name="شماره تلفن"
    )
    code = models.CharField(
        max_length=6,
        verbose_name="کد تایید"
    )
    code_type = models.CharField(
        max_length=20,
        choices=CODE_TYPES,
        default='login',
        verbose_name="نوع کد"
    )
    is_used = models.BooleanField(default=False, verbose_name="استفاده شده")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="زمان ایجاد")
    expires_at = models.DateTimeField(verbose_name="زمان انقضا")
    attempts = models.PositiveIntegerField(default=0, verbose_name="تعداد تلاش")
    
    class Meta:
        verbose_name = "کد تایید"
        verbose_name_plural = "کدهای تایید"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.phone_number} - {self.code} ({self.get_code_type_display()})"

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = self.generate_code()
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(minutes=2)  # 2 minute expiry
        super().save(*args, **kwargs)

    def generate_code(self):
        """Generate 6-digit OTP code"""
        return ''.join(random.choices(string.digits, k=6))

    def is_expired(self):
        """Check if OTP code is expired"""
        return timezone.now() > self.expires_at

    def is_valid(self):
        """Check if OTP code is valid (not used, not expired, attempts < 3)"""
        return not self.is_used and not self.is_expired() and self.attempts < 3

    @classmethod
    def create_otp(cls, phone_number, code_type='login'):
        """Create new OTP and invalidate old ones"""
        # Invalidate all previous OTPs for this phone
        cls.objects.filter(
            phone_number=phone_number,
            code_type=code_type,
            is_used=False
        ).update(is_used=True)
        
        # Create new OTP
        return cls.objects.create(
            phone_number=phone_number,
            code_type=code_type
        )


class LoginAttempt(models.Model):
    """
    Track login attempts for security
    """
    phone_number = models.CharField(max_length=15, verbose_name="شماره تلفن")
    ip_address = models.GenericIPAddressField(verbose_name="آدرس IP")
    user_agent = models.TextField(blank=True, verbose_name="User Agent")
    is_successful = models.BooleanField(default=False, verbose_name="موفق")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="زمان تلاش")
    otp_code = models.ForeignKey(
        OTPCode,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="کد OTP"
    )

    class Meta:
        verbose_name = "تلاش ورود"
        verbose_name_plural = "تلاش‌های ورود"
        ordering = ['-created_at']

    def __str__(self):
        status = "موفق" if self.is_successful else "ناموفق"
        return f"{self.phone_number} - {status} ({self.created_at})"

    @classmethod
    def is_rate_limited(cls, phone_number, ip_address):
        """
        Check if user is rate limited
        Max 5 failed attempts per phone per hour
        Max 10 failed attempts per IP per hour
        """
        one_hour_ago = timezone.now() - timedelta(hours=1)
        
        phone_attempts = cls.objects.filter(
            phone_number=phone_number,
            is_successful=False,
            created_at__gte=one_hour_ago
        ).count()
        
        ip_attempts = cls.objects.filter(
            ip_address=ip_address,
            is_successful=False,
            created_at__gte=one_hour_ago
        ).count()
        
        return phone_attempts >= 5 or ip_attempts >= 10


class UserProfile(models.Model):
    """
    Extended user profile information
    """
    GENDER_CHOICES = [
        ('M', 'مرد'),
        ('F', 'زن'),
        ('O', 'سایر'),
    ]
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name="کاربر"
    )
    date_of_birth = models.DateField(
        null=True,
        blank=True,
        verbose_name="تاریخ تولد"
    )
    gender = models.CharField(
        max_length=1,
        choices=GENDER_CHOICES,
        blank=True,
        verbose_name="جنسیت"
    )
    avatar = models.ImageField(
        upload_to='avatars/',
        null=True,
        blank=True,
        verbose_name="تصویر پروفایل"
    )
    bio = models.TextField(
        max_length=500,
        blank=True,
        verbose_name="درباره من"
    )
    
    # Address information
    address = models.TextField(blank=True, verbose_name="آدرس")
    city = models.CharField(max_length=100, blank=True, verbose_name="شهر")
    state = models.CharField(max_length=100, blank=True, verbose_name="استان")
    postal_code = models.CharField(max_length=10, blank=True, verbose_name="کد پستی")
    
    # Preferences
    email_notifications = models.BooleanField(
        default=True,
        verbose_name="اعلان‌های ایمیل"
    )
    sms_notifications = models.BooleanField(
        default=True,
        verbose_name="اعلان‌های پیامکی"
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="زمان ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="زمان بروزرسانی")

    class Meta:
        verbose_name = "پروفایل کاربر"
        verbose_name_plural = "پروفایل‌های کاربران"

    def __str__(self):
        return f"پروفایل {self.user.first_name} {self.user.last_name}"

    def get_full_address(self):
        """Get formatted full address"""
        parts = [self.address, self.city, self.state]
        return ", ".join([part for part in parts if part])


# Signal to create profile automatically
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Automatically create profile when user is created"""
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Save profile when user is saved"""
    if hasattr(instance, 'profile'):
        instance.profile.save()