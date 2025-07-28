from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from datetime import timedelta
import random
import string
import uuid

class User(AbstractUser):
    """
    Custom user model using phone number as username for OTP-based authentication
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phone = models.CharField(
        max_length=15, 
        unique=True, 
        verbose_name='شماره تلفن',
        help_text='شماره تلفن همراه (مثال: 09123456789)'
    )
    first_name = models.CharField(max_length=150, blank=True, verbose_name='نام')
    last_name = models.CharField(max_length=150, blank=True, verbose_name='نام خانوادگی')
    email = models.EmailField(blank=True, verbose_name='ایمیل')
    
    # User roles
    is_store_owner = models.BooleanField(default=False, verbose_name='مالک فروشگاه')
    is_customer = models.BooleanField(default=True, verbose_name='مشتری')
    is_verified = models.BooleanField(default=False, verbose_name='تأیید شده')
    
    # Profile information
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True, verbose_name='تصویر پروفایل')
    birth_date = models.DateField(null=True, blank=True, verbose_name='تاریخ تولد')
    gender = models.CharField(
        max_length=10,
        choices=[('male', 'مرد'), ('female', 'زن'), ('other', 'سایر')],
        blank=True,
        verbose_name='جنسیت'
    )
    
    # Address information
    city = models.CharField(max_length=100, blank=True, verbose_name='شهر')
    state = models.CharField(max_length=100, blank=True, verbose_name='استان')
    address = models.TextField(blank=True, verbose_name='آدرس')
    postal_code = models.CharField(max_length=10, blank=True, verbose_name='کد پستی')
    
    # Preferences
    language = models.CharField(
        max_length=5,
        choices=[('fa', 'فارسی'), ('en', 'English')],
        default='fa',
        verbose_name='زبان'
    )
    timezone = models.CharField(max_length=50, default='Asia/Tehran', verbose_name='منطقه زمانی')
    
    # Marketing preferences
    accepts_marketing = models.BooleanField(default=True, verbose_name='دریافت پیام‌های تبلیغاتی')
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    USERNAME_FIELD = 'phone'
    REQUIRED_FIELDS = ['username']
    
    class Meta:
        verbose_name = 'کاربر'
        verbose_name_plural = 'کاربران'
    
    def __str__(self):
        return self.phone
    
    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'.strip() or self.phone
    
    def can_create_store(self):
        \"\"\"Check if user can create a new store\"\"\"
        # You can add business logic here (e.g., subscription limits)
        return self.is_verified

class OTPVerification(models.Model):
    \"\"\"
    OTP verification for phone-based authentication
    \"\"\"
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    phone = models.CharField(max_length=15, verbose_name='شماره تلفن')
    otp_code = models.CharField(max_length=6, verbose_name='کد تأیید')
    purpose = models.CharField(
        max_length=20,
        choices=[
            ('login', 'ورود'),
            ('register', 'ثبت‌نام'),
            ('password_reset', 'بازیابی رمز عبور'),
            ('phone_verification', 'تأیید شماره تلفن')
        ],
        default='login',
        verbose_name='هدف'
    )
    is_verified = models.BooleanField(default=False, verbose_name='تأیید شده')
    is_used = models.BooleanField(default=False, verbose_name='استفاده شده')
    attempts = models.PositiveIntegerField(default=0, verbose_name='تعداد تلاش')
    max_attempts = models.PositiveIntegerField(default=3, verbose_name='حداکثر تلاش')
    
    # Timing
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(verbose_name='انقضا')
    verified_at = models.DateTimeField(null=True, blank=True, verbose_name='زمان تأیید')
    
    # Security
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'تأیید OTP'
        verbose_name_plural = 'تأییدات OTP'
        indexes = [
            models.Index(fields=['phone', '-created_at']),
            models.Index(fields=['otp_code', 'is_verified']),
        ]
    
    def save(self, *args, **kwargs):
        if not self.otp_code:
            self.otp_code = self.generate_otp()
        if not self.expires_at:
            # OTP expires in 5 minutes
            self.expires_at = timezone.now() + timedelta(minutes=5)
        super().save(*args, **kwargs)
    
    def generate_otp(self):
        \"\"\"Generate a 6-digit OTP code\"\"\"
        return ''.join(random.choices(string.digits, k=6))
    
    def is_expired(self):
        \"\"\"Check if OTP has expired\"\"\"
        return timezone.now() > self.expires_at
    
    def is_valid(self):
        \"\"\"Check if OTP is still valid for verification\"\"\"
        return not self.is_expired() and not self.is_used and self.attempts < self.max_attempts
    
    def verify(self, entered_code):
        \"\"\"Verify the entered OTP code\"\"\"
        self.attempts += 1
        
        if not self.is_valid():
            return False, 'کد تأیید منقضی شده یا غیرمعتبر است'
        
        if self.otp_code == entered_code:
            self.is_verified = True
            self.is_used = True
            self.verified_at = timezone.now()
            self.save()
            return True, 'کد تأیید با موفقیت تأیید شد'
        else:
            self.save()
            remaining_attempts = self.max_attempts - self.attempts
            if remaining_attempts > 0:
                return False, f'کد تأیید اشتباه است. {remaining_attempts} تلاش باقی مانده'
            else:
                return False, 'تعداد تلاش‌های مجاز به پایان رسید. لطفاً کد جدیدی درخواست کنید'
    
    def __str__(self):
        return f'{self.phone} - {self.otp_code} ({self.get_purpose_display()})'

class UserSession(models.Model):
    \"\"\"
    Track user sessions for security and analytics
    \"\"\"
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    session_key = models.CharField(max_length=40, unique=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    device_type = models.CharField(
        max_length=20,
        choices=[('mobile', 'موبایل'), ('tablet', 'تبلت'), ('desktop', 'دسکتاپ')],
        default='desktop'
    )
    location = models.CharField(max_length=100, blank=True, verbose_name='موقعیت جغرافیایی')
    is_active = models.BooleanField(default=True)
    last_activity = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'جلسه کاربر'
        verbose_name_plural = 'جلسات کاربران'
        ordering = ['-last_activity']
    
    def __str__(self):
        return f'{self.user.phone} - {self.device_type} - {self.created_at}'
    
    def is_recent(self):
        \"\"\"Check if session had recent activity (within 30 minutes)\"\"\"
        return timezone.now() - self.last_activity < timedelta(minutes=30)

class UserNotification(models.Model):
    \"\"\"
    User notifications for various events
    \"\"\"
    NOTIFICATION_TYPES = [
        ('order_status', 'وضعیت سفارش'),
        ('payment', 'پرداخت'),
        ('promotion', 'تخفیف و پیشنهاد'),
        ('system', 'سیستم'),
        ('security', 'امنیت'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200, verbose_name='عنوان')
    message = models.TextField(verbose_name='پیام')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES, verbose_name='نوع')
    is_read = models.BooleanField(default=False, verbose_name='خوانده شده')
    action_url = models.URLField(null=True, blank=True, verbose_name='لینک عمل')
    data = models.JSONField(default=dict, blank=True, verbose_name='داده‌های اضافی')
    
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = 'اعلان'
        verbose_name_plural = 'اعلانات'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['user', 'is_read']),
        ]
    
    def __str__(self):
        return f'{self.user.phone} - {self.title}'
    
    def mark_as_read(self):
        \"\"\"Mark notification as read\"\"\"
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])
