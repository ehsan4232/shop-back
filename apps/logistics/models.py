from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from apps.core.mixins import TimestampMixin, StoreOwnedMixin
import uuid
import re
import requests
import json


class LogisticsProvider(TimestampMixin):
    """
    Iranian logistics providers integration
    Product requirement: "integrated with valid big logistics providers in iran"
    """
    
    PROVIDER_TYPES = [
        ('post', 'پست ایران'),
        ('tipax', 'تیپاکس'),
        ('pishtaz', 'پیشتاز'),
        ('chapar', 'چاپار'),
        ('snapp_box', 'اسنپ باکس'),
        ('alopeyk', 'الوپیک'),
        ('miare', 'میاره'),
        ('pishro', 'پیشرو'),
        ('custom', 'سفارشی'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'فعال'),
        ('inactive', 'غیرفعال'),
        ('maintenance', 'تعمیرات'),
        ('deprecated', 'منسوخ'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Provider info
    name = models.CharField(max_length=100, verbose_name='نام ارائه‌دهنده')
    name_fa = models.CharField(max_length=100, verbose_name='نام فارسی')
    provider_type = models.CharField(max_length=20, choices=PROVIDER_TYPES, verbose_name='نوع ارائه‌دهنده')
    
    # API Configuration
    api_url = models.URLField(verbose_name='آدرس API')
    api_version = models.CharField(max_length=10, default='v1', verbose_name='نسخه API')
    requires_api_key = models.BooleanField(default=True, verbose_name='نیاز به API Key')
    
    # Documentation and support
    documentation_url = models.URLField(blank=True, verbose_name='آدرس مستندات')
    support_phone = models.CharField(max_length=15, blank=True, verbose_name='تلفن پشتیبانی')
    support_email = models.EmailField(blank=True, verbose_name='ایمیل پشتیبانی')
    
    # Service capabilities
    supports_tracking = models.BooleanField(default=True, verbose_name='پیگیری مرسوله')
    supports_cost_calculation = models.BooleanField(default=True, verbose_name='محاسبه هزینه')
    supports_pickup = models.BooleanField(default=False, verbose_name='سرویس جمع‌آوری')
    supports_express = models.BooleanField(default=False, verbose_name='ارسال فوری')
    supports_cash_on_delivery = models.BooleanField(default=False, verbose_name='پرداخت در محل')
    
    # Coverage
    coverage_cities = models.JSONField(
        default=list, 
        blank=True,
        verbose_name='شهرهای تحت پوشش'
    )
    
    # Pricing
    base_cost = models.DecimalField(
        max_digits=10, 
        decimal_places=0, 
        default=0,
        verbose_name='هزینه پایه (تومان)'
    )
    cost_per_kg = models.DecimalField(
        max_digits=8, 
        decimal_places=0, 
        default=0,
        verbose_name='هزینه هر کیلوگرم'
    )
    
    # Status and settings
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    is_default = models.BooleanField(default=False, verbose_name='پیش‌فرض')
    priority = models.PositiveIntegerField(default=0, verbose_name='اولویت')
    
    # Usage stats
    total_shipments = models.PositiveIntegerField(default=0, verbose_name='تعداد کل مرسولات')
    success_rate = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=0,
        verbose_name='نرخ موفقیت'
    )
    
    class Meta:
        verbose_name = 'ارائه‌دهنده حمل‌ونقل'
        verbose_name_plural = 'ارائه‌دهندگان حمل‌ونقل'
        ordering = ['priority', 'name_fa']
        indexes = [
            models.Index(fields=['provider_type', 'status']),
            models.Index(fields=['is_default']),
            models.Index(fields=['priority']),
        ]
    
    def __str__(self):
        return self.name_fa
    
    def calculate_shipping_cost(self, weight_kg, origin_city, destination_city):
        """Calculate shipping cost based on weight and distance"""
        base_cost = self.base_cost
        weight_cost = self.cost_per_kg * weight_kg
        
        # Add distance-based calculation if needed
        # This is a simplified version
        total_cost = base_cost + weight_cost
        
        return total_cost
    
    def is_city_supported(self, city_name):
        """Check if city is in coverage area"""
        if not self.coverage_cities:
            return True  # Assume nationwide coverage if no specific cities listed
        
        return city_name in self.coverage_cities


class StoreLogisticsConfig(StoreOwnedMixin, TimestampMixin):
    """
    Store-specific logistics configuration
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Active providers for this store
    active_providers = models.ManyToManyField(
        LogisticsProvider,
        through='StoreProviderConfig',
        verbose_name='ارائه‌دهندگان فعال'
    )
    
    # Default settings
    default_provider = models.ForeignKey(
        LogisticsProvider,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='ارائه‌دهنده پیش‌فرض'
    )
    
    # Store shipping settings
    free_shipping_threshold = models.DecimalField(
        max_digits=12,
        decimal_places=0,
        default=0,
        verbose_name='آستانه ارسال رایگان (تومان)'
    )
    
    shipping_processing_time = models.PositiveIntegerField(
        default=1,
        verbose_name='زمان آماده‌سازی (روز)'
    )
    
    # Origin settings
    origin_city = models.CharField(max_length=100, verbose_name='شهر مبدا')
    origin_address = models.TextField(verbose_name='آدرس مبدا')
    origin_postal_code = models.CharField(max_length=10, verbose_name='کد پستی مبدا')
    origin_phone = models.CharField(max_length=15, verbose_name='تلفن مبدا')
    
    # Restrictions
    max_weight_kg = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=30,
        verbose_name='حداکثر وزن (کیلوگرم)'
    )
    
    restricted_cities = models.JSONField(
        default=list,
        blank=True,
        verbose_name='شهرهای محدود'
    )
    
    # Settings
    auto_select_cheapest = models.BooleanField(
        default=True,
        verbose_name='انتخاب خودکار ارزان‌ترین'
    )
    
    require_tracking = models.BooleanField(
        default=True,
        verbose_name='الزام پیگیری'
    )
    
    class Meta:
        verbose_name = 'تنظیمات حمل‌ونقل فروشگاه'
        verbose_name_plural = 'تنظیمات حمل‌ونقل فروشگاه‌ها'
    
    def __str__(self):
        return f"تنظیمات حمل‌ونقل {self.store.name_fa}"
    
    def get_available_providers(self, destination_city=None, weight_kg=None):
        """Get available providers for specific shipment"""
        providers = self.active_providers.filter(status='active')
        
        if destination_city:
            # Filter providers that support the destination city
            supported_providers = []
            for provider in providers:
                if provider.is_city_supported(destination_city):
                    supported_providers.append(provider)
            providers = supported_providers
        
        if weight_kg and weight_kg > self.max_weight_kg:
            return []  # No providers if weight exceeds limit
        
        return providers
    
    def calculate_shipping_options(self, destination_city, weight_kg, order_total=0):
        """Calculate all available shipping options"""
        providers = self.get_available_providers(destination_city, weight_kg)
        options = []
        
        for provider in providers:
            cost = provider.calculate_shipping_cost(
                weight_kg, self.origin_city, destination_city
            )
            
            # Apply free shipping threshold
            if order_total >= self.free_shipping_threshold:
                cost = 0
            
            options.append({
                'provider': provider,
                'cost': cost,
                'estimated_delivery_days': self.shipping_processing_time + 2,  # Base estimate
                'supports_tracking': provider.supports_tracking,
                'supports_cod': provider.supports_cash_on_delivery,
            })
        
        # Sort by cost if auto_select_cheapest is enabled
        if self.auto_select_cheapest:
            options.sort(key=lambda x: x['cost'])
        
        return options


class StoreProviderConfig(TimestampMixin):
    """
    Many-to-many through model for store-provider configuration
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    store_config = models.ForeignKey(StoreLogisticsConfig, on_delete=models.CASCADE)
    provider = models.ForeignKey(LogisticsProvider, on_delete=models.CASCADE)
    
    # Provider-specific credentials
    api_key = models.CharField(max_length=255, blank=True, verbose_name='API Key')
    username = models.CharField(max_length=100, blank=True, verbose_name='نام کاربری')
    password = models.CharField(max_length=255, blank=True, verbose_name='رمز عبور')
    
    # Store-specific provider settings
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    priority = models.PositiveIntegerField(default=0, verbose_name='اولویت')
    
    # Custom pricing (overrides provider defaults)
    custom_base_cost = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        null=True,
        blank=True,
        verbose_name='هزینه پایه سفارشی'
    )
    custom_cost_per_kg = models.DecimalField(
        max_digits=8,
        decimal_places=0,
        null=True,
        blank=True,
        verbose_name='هزینه هر کیلو سفارشی'
    )
    
    # Usage tracking
    total_shipments = models.PositiveIntegerField(default=0)
    total_cost = models.DecimalField(max_digits=15, decimal_places=0, default=0)
    last_used = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = 'تنظیمات ارائه‌دهنده فروشگاه'
        verbose_name_plural = 'تنظیمات ارائه‌دهندگان فروشگاه'
        unique_together = ['store_config', 'provider']
        indexes = [
            models.Index(fields=['store_config', 'is_active', 'priority']),
        ]
    
    def __str__(self):
        return f"{self.store_config.store.name_fa} - {self.provider.name_fa}"
    
    def get_effective_cost(self, weight_kg, origin_city, destination_city):
        """Get effective cost using custom pricing if available"""
        if self.custom_base_cost is not None and self.custom_cost_per_kg is not None:
            return self.custom_base_cost + (self.custom_cost_per_kg * weight_kg)
        else:
            return self.provider.calculate_shipping_cost(weight_kg, origin_city, destination_city)


class Shipment(TimestampMixin):
    """
    Individual shipment tracking
    """
    
    SHIPMENT_STATUS = [
        ('pending', 'در انتظار'),
        ('processing', 'در حال پردازش'),
        ('picked_up', 'جمع‌آوری شده'),
        ('in_transit', 'در حال حمل'),
        ('out_for_delivery', 'در حال تحویل'),
        ('delivered', 'تحویل داده شده'),
        ('failed', 'ناموفق'),
        ('returned', 'برگشت داده شده'),
        ('cancelled', 'لغو شده'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Reference to order
    order = models.ForeignKey(
        'orders.Order',
        on_delete=models.CASCADE,
        related_name='shipments',
        verbose_name='سفارش'
    )
    
    # Provider and tracking
    provider_config = models.ForeignKey(
        StoreProviderConfig,
        on_delete=models.CASCADE,
        verbose_name='تنظیمات ارائه‌دهنده'
    )
    
    tracking_number = models.CharField(max_length=100, verbose_name='شماره پیگیری')
    provider_reference = models.CharField(max_length=100, blank=True, verbose_name='مرجع ارائه‌دهنده')
    
    # Shipment details
    weight_kg = models.DecimalField(max_digits=6, decimal_places=2, verbose_name='وزن (کیلوگرم)')
    
    # Addresses
    origin_address = models.TextField(verbose_name='آدرس مبدا')
    destination_address = models.TextField(verbose_name='آدرس مقصد')
    
    # Cost and payment
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=0, verbose_name='هزینه حمل')
    cod_amount = models.DecimalField(
        max_digits=12,
        decimal_places=0,
        default=0,
        verbose_name='مبلغ پرداخت در محل'
    )
    
    # Status and timing
    status = models.CharField(max_length=20, choices=SHIPMENT_STATUS, default='pending')
    
    estimated_delivery = models.DateTimeField(null=True, blank=True, verbose_name='تحویل تخمینی')
    actual_delivery = models.DateTimeField(null=True, blank=True, verbose_name='تحویل واقعی')
    
    # Tracking events
    tracking_events = models.JSONField(default=list, blank=True, verbose_name='رویدادهای پیگیری')
    last_tracking_update = models.DateTimeField(null=True, blank=True)
    
    # Additional data
    notes = models.TextField(blank=True, verbose_name='یادداشت‌ها')
    special_instructions = models.TextField(blank=True, verbose_name='دستورالعمل‌های ویژه')
    
    class Meta:
        verbose_name = 'مرسوله'
        verbose_name_plural = 'مرسولات'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order']),
            models.Index(fields=['tracking_number']),
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['provider_config', 'status']),
        ]
    
    def __str__(self):
        return f"مرسوله {self.tracking_number}"
    
    def update_tracking(self):
        """Update tracking information from provider"""
        # This would integrate with actual provider APIs
        # Implementation depends on specific provider APIs
        pass
    
    def add_tracking_event(self, status, description, timestamp=None):
        """Add a tracking event"""
        if timestamp is None:
            timestamp = timezone.now()
        
        event = {
            'status': status,
            'description': description,
            'timestamp': timestamp.isoformat(),
        }
        
        self.tracking_events.append(event)
        self.last_tracking_update = timestamp
        self.save(update_fields=['tracking_events', 'last_tracking_update'])
    
    def mark_as_delivered(self, timestamp=None):
        """Mark shipment as delivered"""
        if timestamp is None:
            timestamp = timezone.now()
        
        self.status = 'delivered'
        self.actual_delivery = timestamp
        self.add_tracking_event('delivered', 'مرسوله تحویل داده شد', timestamp)
        self.save(update_fields=['status', 'actual_delivery'])


# Signal handlers for automatic updates
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=Shipment)
def update_provider_stats(sender, instance, created, **kwargs):
    """Update provider usage statistics"""
    if created:
        # Update provider config stats
        config = instance.provider_config
        config.total_shipments += 1
        config.total_cost += instance.shipping_cost
        config.last_used = timezone.now()
        config.save(update_fields=['total_shipments', 'total_cost', 'last_used'])
        
        # Update provider stats
        provider = config.provider
        provider.total_shipments += 1
        provider.save(update_fields=['total_shipments'])
