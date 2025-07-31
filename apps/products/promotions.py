from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.core.mixins import TimestampMixin, StoreOwnedMixin
from apps.products.models import Product, ProductCategory, ProductClass
import uuid
from datetime import timedelta


class PromotionCampaign(StoreOwnedMixin, TimestampMixin):
    """
    Promotion campaigns system
    Product requirement: "they can also define promotions and discounts on their products"
    """
    
    DISCOUNT_TYPE_CHOICES = [
        ('percentage', 'درصدی'),
        ('fixed_amount', 'مبلغ ثابت'),
        ('buy_x_get_y', 'خرید X دریافت Y'),
        ('free_shipping', 'ارسال رایگان'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'پیش‌نویس'),
        ('active', 'فعال'),
        ('paused', 'متوقف شده'),
        ('expired', 'منقضی شده'),
        ('completed', 'تکمیل شده'),
    ]
    
    TARGET_TYPE_CHOICES = [
        ('all_products', 'همه محصولات'),
        ('specific_products', 'محصولات خاص'),
        ('categories', 'دسته‌بندی‌ها'),
        ('product_classes', 'کلاس‌های محصول'),
        ('minimum_purchase', 'حداقل خرید'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Basic Information
    name = models.CharField(max_length=200, verbose_name='نام کمپین')
    description = models.TextField(blank=True, verbose_name='توضیحات')
    
    # Discount Configuration
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPE_CHOICES, verbose_name='نوع تخفیف')
    discount_value = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=[MinValueValidator(0)],
        verbose_name='مقدار تخفیف'
    )
    max_discount_amount = models.PositiveIntegerField(
        null=True, 
        blank=True,
        verbose_name='حداکثر مبلغ تخفیف (تومان)'
    )
    
    # Targeting
    target_type = models.CharField(max_length=20, choices=TARGET_TYPE_CHOICES, verbose_name='هدف‌گیری')
    target_products = models.ManyToManyField(Product, blank=True, verbose_name='محصولات هدف')
    target_categories = models.ManyToManyField(ProductCategory, blank=True, verbose_name='دسته‌بندی‌های هدف')
    target_product_classes = models.ManyToManyField(ProductClass, blank=True, verbose_name='کلاس‌های محصول هدف')
    
    # Conditions
    minimum_purchase_amount = models.PositiveIntegerField(
        default=0,
        verbose_name='حداقل مبلغ خرید (تومان)'
    )
    minimum_quantity = models.PositiveIntegerField(default=1, verbose_name='حداقل تعداد')
    
    # Usage Limits
    usage_limit_per_customer = models.PositiveIntegerField(
        null=True, 
        blank=True,
        verbose_name='محدودیت استفاده به ازای هر مشتری'
    )
    total_usage_limit = models.PositiveIntegerField(
        null=True, 
        blank=True,
        verbose_name='محدودیت کل استفاده'
    )
    current_usage_count = models.PositiveIntegerField(default=0, verbose_name='تعداد استفاده فعلی')
    
    # Timing
    start_date = models.DateTimeField(verbose_name='تاریخ شروع')
    end_date = models.DateTimeField(verbose_name='تاریخ پایان')
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', verbose_name='وضعیت')
    is_featured = models.BooleanField(default=False, verbose_name='کمپین ویژه')
    
    # Buy X Get Y specific fields
    buy_quantity = models.PositiveIntegerField(null=True, blank=True, verbose_name='تعداد خرید')
    get_quantity = models.PositiveIntegerField(null=True, blank=True, verbose_name='تعداد دریافت')
    get_products = models.ManyToManyField(
        Product, 
        blank=True, 
        related_name='get_promotion_campaigns',
        verbose_name='محصولات دریافتی'
    )
    
    class Meta:
        verbose_name = 'کمپین تبلیغاتی'
        verbose_name_plural = 'کمپین‌های تبلیغاتی'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['store', 'status']),
            models.Index(fields=['start_date', 'end_date']),
            models.Index(fields=['discount_type']),
        ]
    
    def __str__(self):
        return f"{self.store.name_fa} - {self.name}"
    
    def clean(self):
        super().clean()
        
        # Validate date range
        if self.start_date and self.end_date and self.start_date >= self.end_date:
            raise ValidationError({'end_date': 'تاریخ پایان باید بعد از تاریخ شروع باشد'})
        
        # Validate discount value based on type
        if self.discount_type == 'percentage' and self.discount_value > 100:
            raise ValidationError({'discount_value': 'درصد تخفیف نمی‌تواند بیشتر از 100 باشد'})
        
        # Validate Buy X Get Y fields
        if self.discount_type == 'buy_x_get_y':
            if not self.buy_quantity or not self.get_quantity:
                raise ValidationError('برای تخفیف خرید X دریافت Y باید تعداد خرید و دریافت مشخص شود')
    
    def is_active(self):
        """Check if promotion is currently active"""
        now = timezone.now()
        return (
            self.status == 'active' and
            self.start_date <= now <= self.end_date and
            (self.total_usage_limit is None or self.current_usage_count < self.total_usage_limit)
        )
    
    def can_be_used_by_customer(self, customer, current_usage=None):
        """Check if promotion can be used by specific customer"""
        if not self.is_active():
            return False, 'کمپین فعال نیست'
        
        if self.usage_limit_per_customer is not None:
            if current_usage is None:
                current_usage = PromotionUsage.objects.filter(
                    promotion=self,
                    customer=customer
                ).count()
            
            if current_usage >= self.usage_limit_per_customer:
                return False, 'محدودیت استفاده برای این مشتری تمام شده'
        
        return True, 'قابل استفاده'
    
    def calculate_discount(self, cart_items, customer=None):
        """Calculate discount amount for given cart items"""
        if not self.is_active():
            return 0, 'کمپین فعال نیست'
        
        # Check customer usage limit
        if customer:
            can_use, message = self.can_be_used_by_customer(customer)
            if not can_use:
                return 0, message
        
        # Filter applicable items
        applicable_items = []
        for item in cart_items:
            if self._is_product_applicable(item.product):
                applicable_items.append(item)
        
        if not applicable_items:
            return 0, 'هیچ محصول قابل تخفیفی در سبد خرید نیست'
        
        # Calculate based on discount type
        if self.discount_type == 'percentage':
            return self._calculate_percentage_discount(applicable_items)
        elif self.discount_type == 'fixed_amount':
            return self._calculate_fixed_amount_discount(applicable_items)
        elif self.discount_type == 'buy_x_get_y':
            return self._calculate_buy_x_get_y_discount(applicable_items)
        elif self.discount_type == 'free_shipping':
            return self._calculate_free_shipping_discount(applicable_items)
        
        return 0, 'نوع تخفیف نامعلوم'
    
    def _is_product_applicable(self, product):
        """Check if product is applicable for this promotion"""
        if self.target_type == 'all_products':
            return True
        elif self.target_type == 'specific_products':
            return self.target_products.filter(id=product.id).exists()
        elif self.target_type == 'categories':
            return self.target_categories.filter(id=product.category_id).exists()
        elif self.target_type == 'product_classes':
            return self.target_product_classes.filter(id=product.product_class_id).exists()
        
        return False
    
    def _calculate_percentage_discount(self, items):
        """Calculate percentage discount"""
        total_amount = sum(item.total_price for item in items)
        
        if total_amount < self.minimum_purchase_amount:
            return 0, f'حداقل مبلغ خرید {self.minimum_purchase_amount:,} تومان است'
        
        discount_amount = (total_amount * self.discount_value) / 100
        
        if self.max_discount_amount and discount_amount > self.max_discount_amount:
            discount_amount = self.max_discount_amount
        
        return discount_amount, 'تخفیف اعمال شد'
    
    def _calculate_fixed_amount_discount(self, items):
        """Calculate fixed amount discount"""
        total_amount = sum(item.total_price for item in items)
        
        if total_amount < self.minimum_purchase_amount:
            return 0, f'حداقل مبلغ خرید {self.minimum_purchase_amount:,} تومان است'
        
        discount_amount = min(self.discount_value, total_amount)
        return discount_amount, 'تخفیف اعمال شد'


class CouponCode(StoreOwnedMixin, TimestampMixin):
    """
    Coupon codes for promotions
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    promotion = models.ForeignKey(
        PromotionCampaign, 
        on_delete=models.CASCADE,
        related_name='coupon_codes',
        verbose_name='کمپین'
    )
    
    code = models.CharField(max_length=50, verbose_name='کد تخفیف')
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    
    # Usage tracking
    usage_count = models.PositiveIntegerField(default=0, verbose_name='تعداد استفاده')
    max_usage = models.PositiveIntegerField(null=True, blank=True, verbose_name='حداکثر استفاده')
    
    class Meta:
        unique_together = ['store', 'code']
        verbose_name = 'کد تخفیف'
        verbose_name_plural = 'کدهای تخفیف'
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['store', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.code} - {self.promotion.name}"
    
    def can_be_used(self):
        """Check if coupon can be used"""
        return (
            self.is_active and
            self.promotion.is_active() and
            (self.max_usage is None or self.usage_count < self.max_usage)
        )


class PromotionUsage(TimestampMixin):
    """
    Track promotion usage by customers
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    promotion = models.ForeignKey(PromotionCampaign, on_delete=models.CASCADE, related_name='usages')
    coupon_code = models.ForeignKey(CouponCode, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Customer info (can be guest)
    customer = models.ForeignKey(
        'accounts.User', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name='مشتری'
    )
    customer_phone = models.CharField(max_length=15, blank=True, verbose_name='شماره مشتری')
    customer_email = models.EmailField(blank=True, verbose_name='ایمیل مشتری')
    
    # Order info
    order = models.ForeignKey(
        'orders.Order', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name='سفارش'
    )
    
    # Discount applied
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='مبلغ تخفیف')
    original_amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='مبلغ اصلی')
    
    class Meta:
        verbose_name = 'استفاده از تخفیف'
        verbose_name_plural = 'استفاده‌های تخفیف'
        indexes = [
            models.Index(fields=['promotion', 'customer']),
            models.Index(fields=['coupon_code']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"استفاده از {self.promotion.name} - {self.discount_amount:,} تومان"


class SMSCampaign(StoreOwnedMixin, TimestampMixin):
    """
    SMS marketing campaigns
    Product requirement: "Shops can send promotion campaigns through SMS"
    """
    
    STATUS_CHOICES = [
        ('draft', 'پیش‌نویس'),
        ('scheduled', 'زمان‌بندی شده'),
        ('sending', 'در حال ارسال'),
        ('sent', 'ارسال شده'),
        ('failed', 'ناموفق'),
    ]
    
    TARGET_CHOICES = [
        ('all_customers', 'همه مشتریان'),
        ('recent_customers', 'مشتریان اخیر'),
        ('high_value_customers', 'مشتریان پرارزش'),
        ('inactive_customers', 'مشتریان غیرفعال'),
        ('custom_list', 'لیست سفارشی'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Campaign details
    name = models.CharField(max_length=200, verbose_name='نام کمپین')
    message = models.TextField(max_length=160, verbose_name='متن پیام')  # SMS character limit
    
    # Targeting
    target_audience = models.CharField(max_length=20, choices=TARGET_CHOICES, verbose_name='مخاطبان هدف')
    custom_phone_list = models.JSONField(default=list, blank=True, verbose_name='لیست شماره‌های سفارشی')
    
    # Promotion link
    promotion = models.ForeignKey(
        PromotionCampaign, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name='کمپین تبلیغاتی'
    )
    
    # Scheduling
    send_immediately = models.BooleanField(default=True, verbose_name='ارسال فوری')
    scheduled_at = models.DateTimeField(null=True, blank=True, verbose_name='زمان‌بندی ارسال')
    
    # Status and results
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', verbose_name='وضعیت')
    total_recipients = models.PositiveIntegerField(default=0, verbose_name='تعداد گیرندگان')
    sent_count = models.PositiveIntegerField(default=0, verbose_name='تعداد ارسال شده')
    failed_count = models.PositiveIntegerField(default=0, verbose_name='تعداد ناموفق')
    
    # Costs
    estimated_cost = models.PositiveIntegerField(default=0, verbose_name='هزینه تخمینی (تومان)')
    actual_cost = models.PositiveIntegerField(default=0, verbose_name='هزینه واقعی (تومان)')
    
    class Meta:
        verbose_name = 'کمپین پیامکی'
        verbose_name_plural = 'کمپین‌های پیامکی'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['store', 'status']),
            models.Index(fields=['scheduled_at']),
        ]
    
    def __str__(self):
        return f"{self.store.name_fa} - {self.name}"
    
    def get_target_phone_numbers(self):
        """Get list of phone numbers based on targeting"""
        phone_numbers = []
        
        if self.target_audience == 'custom_list':
            return self.custom_phone_list
        
        # Get customers based on target audience
        from apps.accounts.models import User
        from apps.orders.models import Order
        
        if self.target_audience == 'all_customers':
            customers = User.objects.filter(
                orders__store=self.store,
                is_customer=True
            ).distinct()
        elif self.target_audience == 'recent_customers':
            recent_date = timezone.now() - timedelta(days=30)
            customers = User.objects.filter(
                orders__store=self.store,
                orders__created_at__gte=recent_date,
                is_customer=True
            ).distinct()
        elif self.target_audience == 'high_value_customers':
            # Customers with orders above average
            customers = User.objects.filter(
                orders__store=self.store,
                is_customer=True
            ).annotate(
                total_spent=models.Sum('orders__total_amount')
            ).filter(total_spent__gte=1000000).distinct()  # 1M+ toman
        elif self.target_audience == 'inactive_customers':
            inactive_date = timezone.now() - timedelta(days=90)
            customers = User.objects.filter(
                orders__store=self.store,
                orders__created_at__lt=inactive_date,
                is_customer=True
            ).distinct()
        else:
            customers = User.objects.none()
        
        return [customer.phone for customer in customers if customer.phone]
    
    def estimate_cost(self):
        """Estimate SMS campaign cost"""
        phone_numbers = self.get_target_phone_numbers()
        cost_per_sms = 50  # 50 toman per SMS (approximate)
        return len(phone_numbers) * cost_per_sms


# Signal handlers
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=PromotionUsage)
def update_promotion_usage_count(sender, instance, created, **kwargs):
    """Update promotion usage count when new usage is recorded"""
    if created:
        instance.promotion.current_usage_count += 1
        instance.promotion.save(update_fields=['current_usage_count'])
        
        if instance.coupon_code:
            instance.coupon_code.usage_count += 1
            instance.coupon_code.save(update_fields=['usage_count'])
