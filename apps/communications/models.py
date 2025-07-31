from django.db import models
from apps.core.mixins import StoreOwnedMixin, TimestampMixin
from apps.accounts.models import UserProfile
from apps.products.models import Product, ProductCategory, Brand
import uuid


class SMSCampaign(StoreOwnedMixin, TimestampMixin):
    """
    SMS Marketing Campaigns for stores
    Product description: "Shops can send promotion campaigns through SMS"
    """
    CAMPAIGN_TYPES = [
        ('promotion', 'تبلیغات'),
        ('discount', 'تخفیف'),
        ('new_product', 'محصول جدید'),
        ('restock', 'تجدید موجودی'),
        ('event', 'رویداد'),
        ('newsletter', 'خبرنامه'),
        ('custom', 'سفارشی'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'پیش‌نویس'),
        ('scheduled', 'زمان‌بندی شده'),
        ('sending', 'در حال ارسال'),
        ('sent', 'ارسال شده'),
        ('failed', 'ناموفق'),
        ('cancelled', 'لغو شده'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Campaign details
    name = models.CharField(max_length=100, verbose_name='نام کمپین')
    campaign_type = models.CharField(max_length=20, choices=CAMPAIGN_TYPES, verbose_name='نوع کمپین')
    
    # Message content
    message_text = models.TextField(max_length=500, verbose_name='متن پیام')  # SMS limit consideration
    sender_name = models.CharField(max_length=11, verbose_name='نام فرستنده')  # SMS sender number/name
    
    # Targeting
    target_all_customers = models.BooleanField(default=False, verbose_name='ارسال به همه مشتریان')
    target_phone_numbers = models.JSONField(default=list, blank=True, verbose_name='شماره‌های هدف')
    
    # Product/Category targeting
    target_by_purchase_history = models.BooleanField(default=False, verbose_name='بر اساس تاریخچه خرید')
    target_categories = models.ManyToManyField(
        ProductCategory, 
        blank=True, 
        verbose_name='دسته‌های هدف'
    )
    target_products = models.ManyToManyField(
        Product, 
        blank=True, 
        verbose_name='محصولات هدف'
    )
    target_brands = models.ManyToManyField(
        Brand, 
        blank=True, 
        verbose_name='برندهای هدف'
    )
    
    # Customer segmentation
    min_purchase_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=0, 
        null=True, 
        blank=True,
        verbose_name='حداقل مبلغ خرید'
    )
    max_purchase_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=0, 
        null=True, 
        blank=True,
        verbose_name='حداکثر مبلغ خرید'
    )
    days_since_last_purchase = models.PositiveIntegerField(
        null=True, 
        blank=True,
        verbose_name='روز از آخرین خرید'
    )
    
    # Scheduling
    send_immediately = models.BooleanField(default=False, verbose_name='ارسال فوری')
    scheduled_send_time = models.DateTimeField(null=True, blank=True, verbose_name='زمان ارسال')
    
    # Campaign status and analytics
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', verbose_name='وضعیت')
    total_recipients = models.PositiveIntegerField(default=0, verbose_name='تعداد مخاطبان')
    messages_sent = models.PositiveIntegerField(default=0, verbose_name='پیام‌های ارسالی')
    messages_delivered = models.PositiveIntegerField(default=0, verbose_name='پیام‌های تحویل شده')
    messages_failed = models.PositiveIntegerField(default=0, verbose_name='پیام‌های ناموفق')
    
    # Cost tracking
    estimated_cost = models.DecimalField(
        max_digits=10, 
        decimal_places=0, 
        default=0,
        verbose_name='هزینه تخمینی'
    )
    actual_cost = models.DecimalField(
        max_digits=10, 
        decimal_places=0, 
        default=0,
        verbose_name='هزینه واقعی'
    )
    
    # Performance tracking
    clicks_count = models.PositiveIntegerField(default=0, verbose_name='تعداد کلیک')
    conversions_count = models.PositiveIntegerField(default=0, verbose_name='تعداد تبدیل')
    
    # Timestamps
    sent_at = models.DateTimeField(null=True, blank=True, verbose_name='زمان ارسال')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='زمان تکمیل')
    
    class Meta:
        verbose_name = 'کمپین پیامکی'
        verbose_name_plural = 'کمپین‌های پیامکی'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['store', 'status']),
            models.Index(fields=['campaign_type']),
            models.Index(fields=['scheduled_send_time']),
            models.Index(fields=['sent_at']),
        ]
    
    def __str__(self):
        return f"{self.store.name} - {self.name}"
    
    def calculate_estimated_cost(self):
        """Calculate estimated cost based on recipient count"""
        # Iranian SMS cost per message (approximate)
        cost_per_sms = 200  # Tomans
        self.estimated_cost = self.total_recipients * cost_per_sms
        return self.estimated_cost
    
    def get_target_recipients(self):
        """Get list of target phone numbers based on campaign settings"""
        phone_numbers = []
        
        if self.target_all_customers:
            # Get all customers of the store
            from apps.orders.models import Order
            customer_orders = Order.objects.filter(
                store=self.store
            ).values_list('customer__phone_number', flat=True).distinct()
            phone_numbers.extend(customer_orders)
        
        # Add manually specified phone numbers
        if self.target_phone_numbers:
            phone_numbers.extend(self.target_phone_numbers)
        
        # Filter by purchase history if specified
        if self.target_by_purchase_history:
            from apps.orders.models import Order
            from django.db.models import Sum, Q
            from datetime import datetime, timedelta
            
            filters = Q(store=self.store)
            
            # Filter by purchase amount
            if self.min_purchase_amount or self.max_purchase_amount:
                orders = Order.objects.filter(filters).values(
                    'customer__phone_number'
                ).annotate(
                    total_spent=Sum('total_amount')
                )
                
                if self.min_purchase_amount:
                    orders = orders.filter(total_spent__gte=self.min_purchase_amount)
                if self.max_purchase_amount:
                    orders = orders.filter(total_spent__lte=self.max_purchase_amount)
                
                phone_numbers.extend(orders.values_list('customer__phone_number', flat=True))
            
            # Filter by days since last purchase
            if self.days_since_last_purchase:
                cutoff_date = datetime.now() - timedelta(days=self.days_since_last_purchase)
                recent_customers = Order.objects.filter(
                    filters,
                    created_at__gte=cutoff_date
                ).values_list('customer__phone_number', flat=True).distinct()
                phone_numbers.extend(recent_customers)
        
        # Filter by category/product/brand purchases
        if self.target_categories.exists() or self.target_products.exists() or self.target_brands.exists():
            from apps.orders.models import OrderItem
            
            category_customers = []
            if self.target_categories.exists():
                category_customers = OrderItem.objects.filter(
                    order__store=self.store,
                    product__category__in=self.target_categories.all()
                ).values_list('order__customer__phone_number', flat=True).distinct()
            
            product_customers = []
            if self.target_products.exists():
                product_customers = OrderItem.objects.filter(
                    order__store=self.store,
                    product__in=self.target_products.all()
                ).values_list('order__customer__phone_number', flat=True).distinct()
            
            brand_customers = []
            if self.target_brands.exists():
                brand_customers = OrderItem.objects.filter(
                    order__store=self.store,
                    product__brand__in=self.target_brands.all()
                ).values_list('order__customer__phone_number', flat=True).distinct()
            
            phone_numbers.extend(category_customers)
            phone_numbers.extend(product_customers)
            phone_numbers.extend(brand_customers)
        
        # Remove duplicates and None values
        unique_phone_numbers = list(set(filter(None, phone_numbers)))
        
        # Validate phone numbers
        from apps.core.utils import validate_iranian_phone, format_iranian_phone
        valid_phone_numbers = []
        for phone in unique_phone_numbers:
            formatted = format_iranian_phone(phone)
            if formatted and validate_iranian_phone(formatted):
                valid_phone_numbers.append(formatted)
        
        return valid_phone_numbers
    
    def update_recipient_count(self):
        """Update total recipients count"""
        self.total_recipients = len(self.get_target_recipients())
        self.calculate_estimated_cost()
        self.save(update_fields=['total_recipients', 'estimated_cost'])


class SMSMessage(TimestampMixin):
    """
    Individual SMS messages sent as part of campaigns
    """
    STATUS_CHOICES = [
        ('pending', 'در انتظار'),
        ('sent', 'ارسال شده'),
        ('delivered', 'تحویل شده'),
        ('failed', 'ناموفق'),
        ('clicked', 'کلیک شده'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    campaign = models.ForeignKey(SMSCampaign, on_delete=models.CASCADE, related_name='messages')
    recipient_phone = models.CharField(max_length=11, verbose_name='شماره گیرنده')
    message_text = models.TextField(verbose_name='متن پیام')
    
    # Status tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='وضعیت')
    sent_at = models.DateTimeField(null=True, blank=True, verbose_name='زمان ارسال')
    delivered_at = models.DateTimeField(null=True, blank=True, verbose_name='زمان تحویل')
    clicked_at = models.DateTimeField(null=True, blank=True, verbose_name='زمان کلیک')
    
    # Provider tracking
    provider_message_id = models.CharField(max_length=100, blank=True, verbose_name='شناسه پیام از ارائه‌دهنده')
    provider_response = models.JSONField(default=dict, blank=True, verbose_name='پاسخ ارائه‌دهنده')
    
    # Cost
    cost = models.DecimalField(max_digits=6, decimal_places=0, default=0, verbose_name='هزینه')
    
    # Error tracking
    error_message = models.TextField(blank=True, verbose_name='پیام خطا')
    retry_count = models.PositiveIntegerField(default=0, verbose_name='تعداد تلاش مجدد')
    
    class Meta:
        verbose_name = 'پیام پیامکی'
        verbose_name_plural = 'پیام‌های پیامکی'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['campaign', 'status']),
            models.Index(fields=['recipient_phone']),
            models.Index(fields=['sent_at']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.campaign.name} - {self.recipient_phone}"


class SMSTemplate(StoreOwnedMixin, TimestampMixin):
    """
    Reusable SMS message templates
    """
    TEMPLATE_TYPES = [
        ('welcome', 'خوش‌آمدگویی'),
        ('order_confirm', 'تأیید سفارش'),
        ('shipping', 'ارسال کالا'),
        ('delivery', 'تحویل کالا'),
        ('promotion', 'تبلیغات'),
        ('discount', 'تخفیف'),
        ('birthday', 'تولد'),
        ('reminder', 'یادآوری'),
        ('survey', 'نظرسنجی'),
        ('custom', 'سفارشی'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    name = models.CharField(max_length=100, verbose_name='نام قالب')
    template_type = models.CharField(max_length=20, choices=TEMPLATE_TYPES, verbose_name='نوع قالب')
    message_template = models.TextField(max_length=500, verbose_name='قالب پیام')
    
    # Template variables - for dynamic content
    available_variables = models.JSONField(default=list, verbose_name='متغیرهای قابل استفاده')
    
    # Usage tracking
    usage_count = models.PositiveIntegerField(default=0, verbose_name='تعداد استفاده')
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    
    class Meta:
        verbose_name = 'قالب پیامک'
        verbose_name_plural = 'قالب‌های پیامک'
        ordering = ['template_type', 'name']
        indexes = [
            models.Index(fields=['store', 'template_type']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.store.name} - {self.name}"
    
    def render_message(self, context: dict = None) -> str:
        """Render template with provided context variables"""
        if not context:
            context = {}
        
        # Simple template rendering - replace {variable} with values
        message = self.message_template
        for key, value in context.items():
            placeholder = f"{{{key}}}"
            message = message.replace(placeholder, str(value))
        
        return message
    
    def increment_usage(self):
        """Increment usage count"""
        self.usage_count += 1
        self.save(update_fields=['usage_count'])


# Signal handlers for campaign management
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

@receiver(pre_save, sender=SMSCampaign)
def update_campaign_recipients(sender, instance, **kwargs):
    """Update recipient count when campaign is saved"""
    if instance.pk is None:  # New campaign
        return
    
    # Update recipient count if targeting has changed
    instance.update_recipient_count()

@receiver(post_save, sender=SMSMessage)
def update_campaign_stats(sender, instance, **kwargs):
    """Update campaign statistics when message status changes"""
    campaign = instance.campaign
    
    # Recalculate campaign stats
    messages = campaign.messages.all()
    campaign.messages_sent = messages.filter(status__in=['sent', 'delivered', 'clicked']).count()
    campaign.messages_delivered = messages.filter(status__in=['delivered', 'clicked']).count()
    campaign.messages_failed = messages.filter(status='failed').count()
    campaign.clicks_count = messages.filter(status='clicked').count()
    
    # Calculate actual cost
    campaign.actual_cost = messages.aggregate(
        total_cost=models.Sum('cost')
    )['total_cost'] or 0
    
    campaign.save(update_fields=[
        'messages_sent', 'messages_delivered', 'messages_failed', 
        'clicks_count', 'actual_cost'
    ])