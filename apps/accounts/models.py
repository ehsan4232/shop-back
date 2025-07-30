from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.core.validators import RegexValidator
from datetime import timedelta
import random
import string
import uuid

class User(AbstractUser):
    """
    Custom user model using phone number as username for OTP-based authentication
    FIXED: Resolved phone/username field conflicts and enhanced for production
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # FIXED: Use username for phone to avoid AbstractUser conflicts
    username = models.CharField(
        max_length=15, 
        unique=True, 
        validators=[
            RegexValidator(
                regex=r'^(\+98|0)?9\d{9}$',
                message='شماره تلفن معتبر وارد کنید (مثال: 09123456789)'
            )
        ],
        verbose_name='شماره تلفن',
        help_text='شماره تلفن همراه (مثال: 09123456789)'
    )
    
    # Keep phone as alias for easier API usage
    @property
    def phone(self):
        return self.username
    
    @phone.setter
    def phone(self, value):
        self.username = value
    
    first_name = models.CharField(max_length=150, blank=True, verbose_name='نام')
    last_name = models.CharField(max_length=150, blank=True, verbose_name='نام خانوادگی')
    email = models.EmailField(blank=True, verbose_name='ایمیل')
    
    # User roles - ENHANCED for business logic
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
    
    # FIXED: Enhanced tracking fields
    failed_login_attempts = models.PositiveIntegerField(default=0, verbose_name='تلاش‌های ناموفق ورود')
    last_failed_login = models.DateTimeField(null=True, blank=True, verbose_name='آخرین تلاش ناموفق')
    is_locked = models.BooleanField(default=False, verbose_name='قفل شده')
    locked_until = models.DateTimeField(null=True, blank=True, verbose_name='قفل تا')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    USERNAME_FIELD = 'username'  # FIXED: Use username (which contains phone)
    REQUIRED_FIELDS = ['first_name']  # FIXED: Remove username from required
    
    class Meta:
        verbose_name = 'کاربر'
        verbose_name_plural = 'کاربران'
        # FIXED: Add performance indexes
        indexes = [
            models.Index(fields=['username']),  # Phone lookup
            models.Index(fields=['email']),
            models.Index(fields=['is_verified', 'is_active']),
            models.Index(fields=['is_store_owner']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return self.username  # Display phone number
    
    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'.strip() or self.username
    
    def can_create_store(self):
        """
        ENHANCED: Check if user can create a new store with business rules
        """
        if not self.is_verified:
            return False, 'کاربر تأیید نشده است'
        
        if self.is_locked:
            return False, 'حساب کاربری قفل شده است'
        
        # Check existing stores limit (business rule from product description)
        existing_stores = getattr(self, 'owned_stores', None)
        if existing_stores and existing_stores.count() >= 5:  # Max 5 stores per user
            return False, 'حداکثر تعداد فروشگاه مجاز ایجاد شده است'
        
        return True, 'امکان ایجاد فروشگاه وجود دارد'
    
    def lock_account(self, duration_minutes=30):
        """Lock user account for security"""
        self.is_locked = True
        self.locked_until = timezone.now() + timedelta(minutes=duration_minutes)
        self.save(update_fields=['is_locked', 'locked_until'])
    
    def unlock_account(self):
        """Unlock user account"""
        self.is_locked = False
        self.locked_until = None
        self.failed_login_attempts = 0
        self.save(update_fields=['is_locked', 'locked_until', 'failed_login_attempts'])
    
    def is_account_locked(self):
        """Check if account is currently locked"""
        if not self.is_locked:
            return False
        
        if self.locked_until and timezone.now() > self.locked_until:
            self.unlock_account()
            return False
        
        return True

class OTPVerification(models.Model):
    """
    ENHANCED: OTP verification for phone-based authentication with business logic
    """
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
            ('phone_verification', 'تأیید شماره تلفن'),
            ('store_creation', 'ایجاد فروشگاه'),  # ADDED: For store creation
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
    
    # Security - ENHANCED
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    country_code = models.CharField(max_length=2, blank=True, verbose_name='کد کشور')  # For geolocation
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'تأیید OTP'
        verbose_name_plural = 'تأییدات OTP'
        # FIXED: Enhanced indexes for performance
        indexes = [
            models.Index(fields=['phone', '-created_at']),
            models.Index(fields=['otp_code', 'is_verified']),
            models.Index(fields=['purpose', 'is_used']),
            models.Index(fields=['ip_address', '-created_at']),
        ]
        # FIXED: Add unique constraint to prevent spam
        constraints = [
            models.UniqueConstraint(
                fields=['phone', 'purpose'],
                condition=models.Q(is_used=False, is_verified=False),
                name='unique_active_otp_per_phone_purpose'
            )
        ]
    
    def save(self, *args, **kwargs):
        if not self.otp_code:
            self.otp_code = self.generate_otp()
        if not self.expires_at:
            # ENHANCED: Different expiry times based on purpose
            minutes = 5 if self.purpose in ['login', 'register'] else 10
            self.expires_at = timezone.now() + timedelta(minutes=minutes)
        super().save(*args, **kwargs)
    
    def generate_otp(self):
        """
        ENHANCED: Generate secure OTP with better randomization
        """
        # For high-security purposes, use 6 digits
        if self.purpose in ['store_creation', 'password_reset']:
            return ''.join(random.choices(string.digits, k=6))
        # For regular login, 4 digits is sufficient
        return ''.join(random.choices(string.digits, k=4))
    
    def is_expired(self):
        """Check if OTP has expired"""
        return timezone.now() > self.expires_at
    
    def is_valid(self):
        """ENHANCED: Check if OTP is still valid for verification"""
        if self.is_expired() or self.is_used:
            return False
        
        if self.attempts >= self.max_attempts:
            return False
        
        # ADDED: Rate limiting per IP
        if self.ip_address:
            recent_attempts = OTPVerification.objects.filter(
                ip_address=self.ip_address,
                created_at__gte=timezone.now() - timedelta(hours=1)
            ).count()
            
            if recent_attempts > 10:  # Max 10 OTP requests per hour per IP
                return False
        
        return True
    
    def verify(self, entered_code):
        """
        ENHANCED: Verify the entered OTP code with security measures
        """
        self.attempts += 1
        
        if not self.is_valid():
            self.save()
            return False, 'کد تأیید منقضی شده یا غیرمعتبر است'
        
        if self.otp_code == entered_code:
            self.is_verified = True
            self.is_used = True
            self.verified_at = timezone.now()
            self.save()
            
            # ADDED: Update user verification status if needed
            if self.user and self.purpose in ['register', 'phone_verification']:
                self.user.is_verified = True
                self.user.save(update_fields=['is_verified'])
            
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
    """
    ENHANCED: Track user sessions for security and analytics
    """
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
    
    # ADDED: Enhanced session tracking
    store_context = models.JSONField(default=dict, blank=True, verbose_name='زمینه فروشگاه')  # For multi-tenant
    
    class Meta:
        verbose_name = 'جلسه کاربر'
        verbose_name_plural = 'جلسات کاربران'
        ordering = ['-last_activity']
        # FIXED: Add performance indexes
        indexes = [
            models.Index(fields=['user', '-last_activity']),
            models.Index(fields=['session_key']),
            models.Index(fields=['ip_address']),
            models.Index(fields=['is_active', '-created_at']),
        ]
    
    def __str__(self):
        return f'{self.user.username} - {self.device_type} - {self.created_at}'
    
    def is_recent(self):
        """Check if session had recent activity (within 30 minutes)"""
        return timezone.now() - self.last_activity < timedelta(minutes=30)

class UserNotification(models.Model):
    """
    ENHANCED: User notifications for various events with better categorization
    """
    NOTIFICATION_TYPES = [
        ('order_status', 'وضعیت سفارش'),
        ('payment', 'پرداخت'),
        ('promotion', 'تخفیف و پیشنهاد'),
        ('system', 'سیستم'),
        ('security', 'امنیت'),
        ('store_update', 'به‌روزرسانی فروشگاه'),  # ADDED
        ('product_update', 'به‌روزرسانی محصول'),  # ADDED
    ]
    
    PRIORITY_LEVELS = [  # ADDED: Priority system
        ('low', 'کم'),
        ('medium', 'متوسط'),
        ('high', 'بالا'),
        ('urgent', 'فوری'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200, verbose_name='عنوان')
    message = models.TextField(verbose_name='پیام')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES, verbose_name='نوع')
    priority = models.CharField(max_length=10, choices=PRIORITY_LEVELS, default='medium', verbose_name='اولویت')  # ADDED
    is_read = models.BooleanField(default=False, verbose_name='خوانده شده')
    action_url = models.URLField(null=True, blank=True, verbose_name='لینک عمل')
    data = models.JSONField(default=dict, blank=True, verbose_name='داده‌های اضافی')
    
    # ADDED: Enhanced delivery tracking
    is_sent = models.BooleanField(default=False, verbose_name='ارسال شده')
    sent_via = models.JSONField(default=list, blank=True, verbose_name='روش‌های ارسال')  # ['web', 'sms', 'email']
    
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = 'اعلان'
        verbose_name_plural = 'اعلانات'
        ordering = ['-created_at']
        # FIXED: Enhanced indexes for performance
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['notification_type', '-created_at']),
            models.Index(fields=['priority', '-created_at']),
            models.Index(fields=['is_sent', '-created_at']),
        ]
    
    def __str__(self):
        return f'{self.user.username} - {self.title}'
    
    def mark_as_read(self):
        """Mark notification as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])
    
    def mark_as_sent(self, method='web'):
        """ADDED: Mark notification as sent via specific method"""
        if not self.is_sent:
            self.is_sent = True
            self.sent_at = timezone.now()
        
        if method not in self.sent_via:
            self.sent_via.append(method)
        
        self.save(update_fields=['is_sent', 'sent_at', 'sent_via'])

# ADDED: Account lockout tracking for security
class AccountLockout(models.Model):
    """Track account lockouts for security monitoring"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='lockouts')
    reason = models.CharField(
        max_length=50,
        choices=[
            ('failed_login', 'تلاش‌های ناموفق ورود'),
            ('suspicious_activity', 'فعالیت مشکوک'),
            ('admin_action', 'اقدام مدیر'),
            ('security_breach', 'نقض امنیت'),
        ],
        verbose_name='دلیل قفل'
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    locked_at = models.DateTimeField(auto_now_add=True)
    unlocked_at = models.DateTimeField(null=True, blank=True)
    duration_minutes = models.PositiveIntegerField(default=30, verbose_name='مدت قفل (دقیقه)')
    
    class Meta:
        verbose_name = 'قفل حساب'
        verbose_name_plural = 'قفل‌های حساب'
        ordering = ['-locked_at']
        indexes = [
            models.Index(fields=['user', '-locked_at']),
            models.Index(fields=['ip_address', '-locked_at']),
            models.Index(fields=['reason', '-locked_at']),
        ]
    
    def __str__(self):
        return f'{self.user.username} - {self.get_reason_display()}'