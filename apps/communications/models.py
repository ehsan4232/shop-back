from django.db import models
from django.utils import timezone
import uuid

class NotificationTemplate(models.Model):
    """
    Template for notifications (SMS, Email, Push)
    """
    TEMPLATE_TYPES = [
        ('sms', 'پیامک'),
        ('email', 'ایمیل'),
        ('push', 'اعلان موبایل'),
    ]
    
    EVENT_TYPES = [
        ('order_created', 'ایجاد سفارش'),
        ('order_paid', 'پرداخت سفارش'),
        ('order_shipped', 'ارسال سفارش'),
        ('order_delivered', 'تحویل سفارش'),
        ('order_cancelled', 'لغو سفارش'),
        ('payment_completed', 'تکمیل پرداخت'),
        ('payment_failed', 'خطا در پرداخت'),
        ('low_stock', 'موجودی کم'),
        ('welcome', 'خوش‌آمدگویی'),
        ('otp', 'کد تأیید'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store = models.ForeignKey('stores.Store', on_delete=models.CASCADE, related_name='notification_templates')
    
    name = models.CharField(max_length=100, verbose_name='نام قالب')
    template_type = models.CharField(max_length=20, choices=TEMPLATE_TYPES, verbose_name='نوع قالب')
    event_type = models.CharField(max_length=50, choices=EVENT_TYPES, verbose_name='نوع رویداد')
    
    # Template content
    subject = models.CharField(max_length=200, blank=True, verbose_name='موضوع')
    content = models.TextField(verbose_name='محتوا')
    html_content = models.TextField(blank=True, verbose_name='محتوای HTML')
    
    # Settings
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    is_default = models.BooleanField(default=False, verbose_name='پیش‌فرض')
    
    # Variables help
    available_variables = models.JSONField(
        default=list,
        verbose_name='متغیرهای قابل استفاده',
        help_text='لیست متغیرهایی که در قالب قابل استفاده هستند'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'قالب اعلان'
        verbose_name_plural = 'قالب‌های اعلان'
        unique_together = ['store', 'template_type', 'event_type', 'is_default']
    
    def __str__(self):
        return f"{self.name} - {self.get_template_type_display()}"

class Notification(models.Model):
    """
    Base notification model
    """
    NOTIFICATION_TYPES = [
        ('sms', 'پیامک'),
        ('email', 'ایمیل'),
        ('push', 'اعلان موبایل'),
        ('in_app', 'اعلان درون‌برنامه‌ای'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'در انتظار ارسال'),
        ('sent', 'ارسال شده'),
        ('failed', 'ناموفق'),
        ('delivered', 'تحویل داده شده'),
        ('read', 'خوانده شده'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store = models.ForeignKey('stores.Store', on_delete=models.CASCADE, related_name='notifications')
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='received_notifications')
    
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES, verbose_name='نوع اعلان')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='وضعیت')
    
    # Content
    title = models.CharField(max_length=200, verbose_name='عنوان')
    message = models.TextField(verbose_name='پیام')
    
    # Recipient info
    recipient_phone = models.CharField(max_length=15, blank=True, verbose_name='شماره گیرنده')
    recipient_email = models.EmailField(blank=True, verbose_name='ایمیل گیرنده')
    
    # Metadata
    template = models.ForeignKey(
        NotificationTemplate, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name='قالب استفاده شده'
    )
    event_type = models.CharField(max_length=50, blank=True, verbose_name='نوع رویداد')
    reference_id = models.CharField(max_length=100, blank=True, verbose_name='شناسه مرجع')
    
    # Delivery tracking
    sent_at = models.DateTimeField(null=True, blank=True, verbose_name='زمان ارسال')
    delivered_at = models.DateTimeField(null=True, blank=True, verbose_name='زمان تحویل')
    read_at = models.DateTimeField(null=True, blank=True, verbose_name='زمان خواندن')
    
    # Provider response
    provider_response = models.JSONField(default=dict, blank=True, verbose_name='پاسخ ارائه‌دهنده')
    error_message = models.TextField(blank=True, verbose_name='پیام خطا')
    
    # Cost tracking
    cost = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='هزینه')
    
    # Retry logic
    retry_count = models.PositiveIntegerField(default=0, verbose_name='تعداد تلاش مجدد')
    max_retries = models.PositiveIntegerField(default=3, verbose_name='حداکثر تلاش مجدد')
    next_retry_at = models.DateTimeField(null=True, blank=True, verbose_name='زمان تلاش مجدد بعدی')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'اعلان'
        verbose_name_plural = 'اعلانات'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['store', 'status', '-created_at']),
            models.Index(fields=['user', 'notification_type', '-created_at']),
            models.Index(fields=['status', 'next_retry_at']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.get_notification_type_display()}"
    
    def mark_as_sent(self):
        """Mark notification as sent"""
        self.status = 'sent'
        self.sent_at = timezone.now()
        self.save(update_fields=['status', 'sent_at'])
    
    def mark_as_delivered(self):
        """Mark notification as delivered"""
        self.status = 'delivered'
        self.delivered_at = timezone.now()
        self.save(update_fields=['status', 'delivered_at'])
    
    def mark_as_read(self):
        """Mark notification as read"""
        self.status = 'read'
        self.read_at = timezone.now()
        self.save(update_fields=['status', 'read_at'])
    
    def mark_as_failed(self, error_message: str = ""):
        """Mark notification as failed"""
        self.status = 'failed'
        self.error_message = error_message
        self.save(update_fields=['status', 'error_message'])
    
    def can_retry(self) -> bool:
        """Check if notification can be retried"""
        return (
            self.status == 'failed' and 
            self.retry_count < self.max_retries and
            (not self.next_retry_at or timezone.now() >= self.next_retry_at)
        )
    
    def schedule_retry(self, delay_minutes: int = 5):
        """Schedule notification for retry"""
        if self.retry_count < self.max_retries:
            self.retry_count += 1
            self.next_retry_at = timezone.now() + timezone.timedelta(minutes=delay_minutes)
            self.status = 'pending'
            self.save(update_fields=['retry_count', 'next_retry_at', 'status'])

class SMSLog(models.Model):
    """
    SMS sending log
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    notification = models.OneToOneField(
        Notification, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='sms_log'
    )
    
    phone = models.CharField(max_length=15, verbose_name='شماره تلفن')
    message = models.TextField(verbose_name='پیام')
    template_name = models.CharField(max_length=100, blank=True, verbose_name='نام قالب')
    
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'در انتظار'),
            ('sent', 'ارسال شده'),
            ('failed', 'ناموفق'),
            ('delivered', 'تحویل داده شده')
        ],
        default='pending',
        verbose_name='وضعیت'
    )
    
    # Provider details
    provider = models.CharField(max_length=50, default='kavenegar', verbose_name='ارائه‌دهنده')
    provider_message_id = models.CharField(max_length=100, blank=True, verbose_name='شناسه پیام ارائه‌دهنده')
    provider_response = models.JSONField(default=dict, blank=True, verbose_name='پاسخ ارائه‌دهنده')
    
    # Cost and delivery tracking
    cost = models.DecimalField(max_digits=8, decimal_places=2, default=0, verbose_name='هزینه')
    parts_count = models.PositiveIntegerField(default=1, verbose_name='تعداد بخش')
    
    # Error handling
    error_message = models.TextField(blank=True, verbose_name='پیام خطا')
    retry_count = models.PositiveIntegerField(default=0, verbose_name='تعداد تلاش مجدد')
    
    sent_at = models.DateTimeField(null=True, blank=True, verbose_name='زمان ارسال')
    delivered_at = models.DateTimeField(null=True, blank=True, verbose_name='زمان تحویل')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'لاگ پیامک'
        verbose_name_plural = 'لاگ‌های پیامک'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['phone', '-created_at']),
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['provider_message_id']),
        ]
    
    def __str__(self):
        return f"SMS to {self.phone} - {self.status}"

class EmailLog(models.Model):
    """
    Email sending log
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    notification = models.OneToOneField(
        Notification, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='email_log'
    )
    
    to_email = models.EmailField(verbose_name='ایمیل گیرنده')
    from_email = models.EmailField(verbose_name='ایمیل فرستنده')
    subject = models.CharField(max_length=200, verbose_name='موضوع')
    template_name = models.CharField(max_length=100, blank=True, verbose_name='نام قالب')
    
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'در انتظار'),
            ('sent', 'ارسال شده'),
            ('failed', 'ناموفق'),
            ('delivered', 'تحویل داده شده'),
            ('opened', 'باز شده'),
            ('clicked', 'کلیک شده')
        ],
        default='pending',
        verbose_name='وضعیت'
    )
    
    # Provider details
    provider = models.CharField(max_length=50, default='smtp', verbose_name='ارائه‌دهنده')
    provider_message_id = models.CharField(max_length=200, blank=True, verbose_name='شناسه پیام')
    
    # Tracking
    opened_at = models.DateTimeField(null=True, blank=True, verbose_name='زمان باز کردن')
    clicked_at = models.DateTimeField(null=True, blank=True, verbose_name='زمان کلیک')
    
    # Error handling
    error_message = models.TextField(blank=True, verbose_name='پیام خطا')
    retry_count = models.PositiveIntegerField(default=0, verbose_name='تعداد تلاش مجدد')
    
    sent_at = models.DateTimeField(null=True, blank=True, verbose_name='زمان ارسال')
    delivered_at = models.DateTimeField(null=True, blank=True, verbose_name='زمان تحویل')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'لاگ ایمیل'
        verbose_name_plural = 'لاگ‌های ایمیل'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['to_email', '-created_at']),
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['provider_message_id']),
        ]
    
    def __str__(self):
        return f"Email to {self.to_email} - {self.subject}"

class NewsletterSubscription(models.Model):
    """
    Newsletter subscription management
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store = models.ForeignKey('stores.Store', on_delete=models.CASCADE, related_name='newsletter_subscriptions')
    
    email = models.EmailField(verbose_name='ایمیل')
    first_name = models.CharField(max_length=100, blank=True, verbose_name='نام')
    last_name = models.CharField(max_length=100, blank=True, verbose_name='نام خانوادگی')
    
    # Subscription preferences
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    subscribed_categories = models.ManyToManyField(
        'products.ProductCategory',
        blank=True,
        verbose_name='دسته‌بندی‌های عضویت'
    )
    
    # Tracking
    source = models.CharField(
        max_length=50,
        choices=[
            ('website', 'وب‌سایت'),
            ('popup', 'پاپ‌آپ'),
            ('checkout', 'فرآیند خرید'),
            ('social', 'شبکه‌های اجتماعی'),
            ('manual', 'دستی')
        ],
        default='website',
        verbose_name='منبع عضویت'
    )
    
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name='آدرس IP')
    user_agent = models.TextField(blank=True, verbose_name='User Agent')
    
    # Confirmation
    is_confirmed = models.BooleanField(default=False, verbose_name='تأیید شده')
    confirmation_token = models.CharField(max_length=100, blank=True, verbose_name='توکن تأیید')
    confirmed_at = models.DateTimeField(null=True, blank=True, verbose_name='زمان تأیید')
    
    # Unsubscribe
    unsubscribe_token = models.CharField(max_length=100, blank=True, verbose_name='توکن لغو عضویت')
    unsubscribed_at = models.DateTimeField(null=True, blank=True, verbose_name='زمان لغو عضویت')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['store', 'email']
        verbose_name = 'عضویت خبرنامه'
        verbose_name_plural = 'عضویت‌های خبرنامه'
        indexes = [
            models.Index(fields=['store', 'is_active', 'is_confirmed']),
            models.Index(fields=['email']),
            models.Index(fields=['confirmation_token']),
            models.Index(fields=['unsubscribe_token']),
        ]
    
    def __str__(self):
        return f"{self.email} - {self.store.name_fa}"
    
    def save(self, *args, **kwargs):
        # Generate tokens if not provided
        if not self.confirmation_token:
            import secrets
            self.confirmation_token = secrets.token_urlsafe(32)
        
        if not self.unsubscribe_token:
            import secrets
            self.unsubscribe_token = secrets.token_urlsafe(32)
        
        super().save(*args, **kwargs)
    
    def confirm_subscription(self):
        """Confirm newsletter subscription"""
        self.is_confirmed = True
        self.confirmed_at = timezone.now()
        self.save(update_fields=['is_confirmed', 'confirmed_at'])
    
    def unsubscribe(self):
        """Unsubscribe from newsletter"""
        self.is_active = False
        self.unsubscribed_at = timezone.now()
        self.save(update_fields=['is_active', 'unsubscribed_at'])

class Campaign(models.Model):
    """
    Marketing campaign management
    """
    CAMPAIGN_TYPES = [
        ('newsletter', 'خبرنامه'),
        ('promotion', 'تبلیغات'),
        ('announcement', 'اطلاعیه'),
        ('welcome', 'خوش‌آمدگویی'),
        ('abandoned_cart', 'سبد خرید رها شده'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'پیش‌نویس'),
        ('scheduled', 'زمان‌بندی شده'),
        ('sending', 'در حال ارسال'),
        ('sent', 'ارسال شده'),
        ('paused', 'متوقف شده'),
        ('cancelled', 'لغو شده'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store = models.ForeignKey('stores.Store', on_delete=models.CASCADE, related_name='campaigns')
    
    name = models.CharField(max_length=200, verbose_name='نام کمپین')
    campaign_type = models.CharField(max_length=50, choices=CAMPAIGN_TYPES, verbose_name='نوع کمپین')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', verbose_name='وضعیت')
    
    # Content
    subject = models.CharField(max_length=200, verbose_name='موضوع')
    content = models.TextField(verbose_name='محتوا')
    html_content = models.TextField(blank=True, verbose_name='محتوای HTML')
    
    # Targeting
    target_all_subscribers = models.BooleanField(default=True, verbose_name='ارسال به همه مشترکین')
    target_categories = models.ManyToManyField(
        'products.ProductCategory',
        blank=True,
        verbose_name='دسته‌بندی‌های هدف'
    )
    target_customer_segments = models.JSONField(
        default=list,
        blank=True,
        verbose_name='بخش‌های مشتری هدف'
    )
    
    # Scheduling
    scheduled_at = models.DateTimeField(null=True, blank=True, verbose_name='زمان‌بندی شده')
    send_immediately = models.BooleanField(default=False, verbose_name='ارسال فوری')
    
    # Tracking
    total_recipients = models.PositiveIntegerField(default=0, verbose_name='تعداد کل گیرندگان')
    sent_count = models.PositiveIntegerField(default=0, verbose_name='تعداد ارسال شده')
    delivered_count = models.PositiveIntegerField(default=0, verbose_name='تعداد تحویل داده شده')
    opened_count = models.PositiveIntegerField(default=0, verbose_name='تعداد باز شده')
    clicked_count = models.PositiveIntegerField(default=0, verbose_name='تعداد کلیک شده')
    
    # Metrics
    open_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name='نرخ باز کردن')
    click_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name='نرخ کلیک')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    sent_at = models.DateTimeField(null=True, blank=True, verbose_name='زمان ارسال')
    
    class Meta:
        verbose_name = 'کمپین'
        verbose_name_plural = 'کمپین‌ها'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['store', 'status', '-created_at']),
            models.Index(fields=['campaign_type', 'status']),
            models.Index(fields=['scheduled_at']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.get_campaign_type_display()}"
    
    def calculate_metrics(self):
        """Calculate campaign metrics"""
        if self.sent_count > 0:
            self.open_rate = (self.opened_count / self.sent_count) * 100
            self.click_rate = (self.clicked_count / self.sent_count) * 100
        else:
            self.open_rate = 0
            self.click_rate = 0
        
        self.save(update_fields=['open_rate', 'click_rate'])
