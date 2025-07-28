from django.db import models
from django.conf import settings
import uuid

class SMSTemplate(models.Model):
    """
    SMS message templates for different purposes
    """
    TEMPLATE_TYPES = [
        ('welcome', 'خوش‌آمدگویی'),
        ('otp', 'کد تأیید'),
        ('order_confirmation', 'تأیید سفارش'),
        ('order_status', 'وضعیت سفارش'),
        ('shipping', 'ارسال سفارش'),
        ('delivery', 'تحویل سفارش'),
        ('payment_success', 'موفقیت پرداخت'),
        ('payment_failed', 'ناموفق پرداخت'),
        ('promotion', 'تبلیغات'),
        ('reminder', 'یادآوری'),
        ('low_stock', 'کمبود موجودی'),
    ]
    
    store = models.ForeignKey('stores.Store', on_delete=models.CASCADE, related_name='sms_templates')
    name = models.CharField(max_length=100, verbose_name='نام قالب')
    template_type = models.CharField(max_length=20, choices=TEMPLATE_TYPES, verbose_name='نوع قالب')
    content = models.TextField(
        verbose_name='متن پیام', 
        help_text='متغیرها: {name}, {store_name}, {order_id}, {code}, {amount}, {product_name}'
    )
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    usage_count = models.PositiveIntegerField(default=0, verbose_name='تعداد استفاده')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['store', 'template_type']
        verbose_name = 'قالب پیامک'
        verbose_name_plural = 'قالب‌های پیامک'
    
    def __str__(self):
        return f'{self.store.name_fa} - {self.get_template_type_display()}'

class SMSMessage(models.Model):
    """
    SMS messages sent to users
    """
    STATUS_CHOICES = [
        ('pending', 'در انتظار'),
        ('sent', 'ارسال شده'),
        ('delivered', 'تحویل داده شده'),
        ('failed', 'ناموفق'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store = models.ForeignKey('stores.Store', on_delete=models.CASCADE, related_name='sms_messages')
    recipient = models.CharField(max_length=15, verbose_name='گیرنده')
    content = models.TextField(verbose_name='متن پیام')
    template = models.ForeignKey(SMSTemplate, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    provider_message_id = models.CharField(max_length=100, blank=True)
    provider_response = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    cost = models.DecimalField(max_digits=8, decimal_places=2, default=0, verbose_name='هزینه')
    
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'پیامک'
        verbose_name_plural = 'پیامک‌ها'
    
    def __str__(self):
        return f'{self.recipient} - {self.created_at.strftime("%Y/%m/%d %H:%M")}'

class EmailTemplate(models.Model):
    """
    Email templates for different purposes
    """
    TEMPLATE_TYPES = [
        ('welcome', 'خوش‌آمدگویی'),
        ('order_confirmation', 'تأیید سفارش'),
        ('shipping', 'ارسال سفارش'),
        ('invoice', 'فاکتور'),
        ('newsletter', 'خبرنامه'),
    ]
    
    store = models.ForeignKey('stores.Store', on_delete=models.CASCADE, related_name='email_templates')
    name = models.CharField(max_length=100, verbose_name='نام قالب')
    template_type = models.CharField(max_length=20, choices=TEMPLATE_TYPES, verbose_name='نوع قالب')
    subject = models.CharField(max_length=200, verbose_name='موضوع')
    html_content = models.TextField(verbose_name='محتوای HTML')
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['store', 'template_type']
        verbose_name = 'قالب ایمیل'
        verbose_name_plural = 'قالب‌های ایمیل'
    
    def __str__(self):
        return f'{self.store.name_fa} - {self.get_template_type_display()}'

class PushNotification(models.Model):
    """
    Push notifications
    """
    STATUS_CHOICES = [
        ('pending', 'در انتظار'),
        ('sent', 'ارسال شده'),
        ('failed', 'ناموفق'),
    ]
    
    TARGET_TYPES = [
        ('all_users', 'همه کاربران'),
        ('customers', 'مشتریان'),
        ('store_owners', 'مالکان فروشگاه'),
        ('specific_users', 'کاربران خاص'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store = models.ForeignKey('stores.Store', on_delete=models.CASCADE, related_name='push_notifications')
    title = models.CharField(max_length=100, verbose_name='عنوان')
    body = models.TextField(verbose_name='متن')
    target_type = models.CharField(max_length=20, choices=TARGET_TYPES, verbose_name='مخاطب')
    target_users = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, verbose_name='کاربران هدف')
    action_url = models.URLField(null=True, blank=True, verbose_name='لینک عمل')
    image_url = models.URLField(null=True, blank=True, verbose_name='لینک تصویر')
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    sent_count = models.PositiveIntegerField(default=0, verbose_name='تعداد ارسال')
    
    scheduled_at = models.DateTimeField(null=True, blank=True, verbose_name='زمان ارسال')
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'اعلان فوری'
        verbose_name_plural = 'اعلانات فوری'
    
    def __str__(self):
        return f'{self.store.name_fa} - {self.title}'
