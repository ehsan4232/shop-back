from django.db import models
from django.utils.text import slugify
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from apps.core.mixins import TimestampMixin, SlugMixin, AnalyticsMixin
import uuid

class Store(TimestampMixin, SlugMixin, AnalyticsMixin):
    """
    Store model with proper theme integration and performance optimizations
    Implements ALL product description requirements:
    - Independent domains/subdomains  
    - Theme selection system via themes app
    - Multi-tenant data isolation
    - Business analytics and dashboards
    - Support for 1000+ store owners with proper indexing
    """
    
    SUBSCRIPTION_TYPES = [
        ('trial', 'آزمایشی'),
        ('basic', 'پایه'),
        ('premium', 'پریمیوم'),
        ('enterprise', 'سازمانی'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'فعال'),
        ('suspended', 'تعلیق'),
        ('pending', 'در انتظار'),
        ('expired', 'منقضی'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Store ownership (product requirement)
    owner = models.ForeignKey(
        'accounts.User', 
        on_delete=models.CASCADE,
        related_name='owned_stores',
        verbose_name='مالک فروشگاه'
    )
    
    # Basic information
    name = models.CharField(max_length=100, verbose_name='نام فروشگاه')
    name_fa = models.CharField(max_length=100, verbose_name='نام فارسی فروشگاه')
    description = models.TextField(blank=True, verbose_name='توضیحات')
    description_fa = models.TextField(blank=True, verbose_name='توضیحات فارسی')
    
    # Multi-tenant schema for data isolation
    schema_name = models.CharField(
        max_length=63, 
        unique=True, 
        verbose_name='نام schema پایگاه داده'
    )
    
    # Domain configuration (product requirement: "independent domain and address")
    domain = models.CharField(
        max_length=255, 
        null=True, 
        blank=True,
        unique=True,
        verbose_name='دامنه اختصاصی'
    )
    subdomain = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='زیردامنه'
    )
    
    # FIXED: Use proper theme system from themes app instead of duplicate choices
    # This eliminates the duplicate theme implementation
    # The themes are now managed through apps.themes models
    
    # Subscription and billing
    subscription_type = models.CharField(
        max_length=20, 
        choices=SUBSCRIPTION_TYPES, 
        default='trial',
        verbose_name='نوع اشتراک'
    )
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='pending',
        verbose_name='وضعیت'
    )
    paid_until = models.DateField(null=True, blank=True, verbose_name='انقضای پرداخت')
    on_trial = models.BooleanField(default=True, verbose_name='دوره آزمایشی')
    
    # Business limitations (scalability requirement)
    max_products = models.PositiveIntegerField(default=100, verbose_name='حداکثر محصولات')
    max_storage_mb = models.PositiveIntegerField(default=1000, verbose_name='حداکثر فضا (MB)')
    max_orders_per_month = models.PositiveIntegerField(default=1000, verbose_name='حداکثر سفارش/ماه')
    
    # Contact info
    phone_regex = RegexValidator(
        regex=r'^09\d{9}$',
        message="شماره تلفن باید به فرمت 09xxxxxxxxx باشد"
    )
    phone_number = models.CharField(
        validators=[phone_regex], 
        max_length=11, 
        blank=True, 
        verbose_name='تلفن'
    )
    email = models.EmailField(blank=True, verbose_name='ایمیل')
    address = models.TextField(blank=True, verbose_name='آدرس')
    
    # Store branding
    logo = models.ImageField(upload_to='store_logos/', null=True, blank=True, verbose_name='لوگو')
    banner = models.ImageField(upload_to='store_banners/', null=True, blank=True, verbose_name='بنر')
    primary_color = models.CharField(max_length=7, default='#007bff', verbose_name='رنگ اصلی')
    secondary_color = models.CharField(max_length=7, default='#6c757d', verbose_name='رنگ فرعی')
    
    # Business settings  
    currency = models.CharField(max_length=3, default='IRR', verbose_name='واحد پول')
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name='نرخ مالیات')
    
    # Social media integration (product requirement)
    instagram_username = models.CharField(max_length=100, blank=True, verbose_name='اینستاگرام')
    telegram_username = models.CharField(max_length=100, blank=True, verbose_name='تلگرام')
    
    # Status
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    
    # Analytics (product requirement: "dashboards of charts and info")
    total_products = models.PositiveIntegerField(default=0, verbose_name='تعداد محصولات')
    total_orders = models.PositiveIntegerField(default=0, verbose_name='تعداد سفارشات')
    total_revenue = models.DecimalField(max_digits=15, decimal_places=0, default=0, verbose_name='درآمد کل')
    total_customers = models.PositiveIntegerField(default=0, verbose_name='تعداد مشتریان')
    
    # Current usage tracking (for scalability limits)
    current_products_count = models.PositiveIntegerField(default=0)
    current_storage_mb = models.PositiveIntegerField(default=0)
    current_month_orders = models.PositiveIntegerField(default=0)
    
    # SEO and social media
    meta_title = models.CharField(max_length=200, blank=True, verbose_name='عنوان متا')
    meta_description = models.TextField(blank=True, verbose_name='توضیحات متا')
    social_media_links = models.JSONField(default=dict, blank=True, verbose_name='شبکه‌های اجتماعی')
    
    # Feature flags
    enable_sms_campaigns = models.BooleanField(default=False, verbose_name='کمپین SMS')
    enable_advanced_analytics = models.BooleanField(default=False, verbose_name='آمار پیشرفته')
    enable_custom_domain = models.BooleanField(default=False, verbose_name='دامنه اختصاصی')
    enable_api_access = models.BooleanField(default=False, verbose_name='دسترسی API')
    
    class Meta:
        verbose_name = 'فروشگاه'
        verbose_name_plural = 'فروشگاه‌ها'
        ordering = ['-created_at']
        # ENHANCED: Better indexes for 1000+ stores performance requirement
        indexes = [
            models.Index(fields=['owner', 'is_active']),
            models.Index(fields=['status', 'subscription_type']),
            models.Index(fields=['schema_name']),  # Critical for multi-tenancy
            models.Index(fields=['subdomain']),    # Critical for routing
            models.Index(fields=['domain']),       # Critical for custom domains
            models.Index(fields=['slug']),
            models.Index(fields=['is_active', 'status']),
            models.Index(fields=['-created_at']),  # For admin pagination
            models.Index(fields=['paid_until']),   # For subscription queries
            # Performance indexes for analytics queries
            models.Index(fields=['owner', '-total_revenue']),
            models.Index(fields=['subscription_type', '-total_orders']),
        ]
    
    def __str__(self):
        return self.name_fa or self.name
    
    def clean(self):
        """Enhanced validation"""
        super().clean()
        
        if self.schema_name and not self.schema_name.replace('_', '').isalnum():
            raise ValidationError({
                'schema_name': 'نام schema باید فقط شامل حروف، اعداد و _ باشد'
            })
        
        if self.subdomain and not self.subdomain.replace('-', '').isalnum():
            raise ValidationError({
                'subdomain': 'زیردامنه باید فقط شامل حروف، اعداد و - باشد'
            })
    
    def save(self, *args, **kwargs):
        # Auto-generate schema name and subdomain
        if not self.schema_name:
            self.schema_name = f"store_{self.slug}_{uuid.uuid4().hex[:8]}"
        
        if not self.subdomain:
            self.subdomain = self.slug
        
        # Ensure uniqueness for performance (avoid duplicate checks in DB)
        if not self.pk:
            original_subdomain = self.subdomain
            counter = 1
            while Store.objects.filter(subdomain=self.subdomain).exists():
                self.subdomain = f"{original_subdomain}-{counter}"
                counter += 1
        
        super().save(*args, **kwargs)
    
    @property
    def domain_url(self):
        """Get store domain (product requirement)"""
        if self.domain and self.enable_custom_domain:
            return self.domain
        else:
            platform_domain = getattr(settings, 'PLATFORM_DOMAIN', 'mall.ir')
            return f"{self.subdomain}.{platform_domain}"
    
    @property
    def store_url(self):
        """Get full store URL"""
        protocol = 'https' if not settings.DEBUG else 'http'
        return f"{protocol}://{self.domain_url}"
    
    def is_subscription_active(self):
        """Check if subscription is active"""
        from django.utils import timezone
        if self.on_trial:
            return True  # Trial is always active until expired
        return self.paid_until and timezone.now().date() <= self.paid_until
    
    def is_within_limits(self):
        """Check subscription limits (scalability requirement)"""
        return (
            self.current_products_count <= self.max_products and
            self.current_storage_mb <= self.max_storage_mb and
            self.current_month_orders <= self.max_orders_per_month
        )
    
    def can_add_product(self):
        """Check if store can add more products"""
        return self.current_products_count < self.max_products
    
    def get_active_theme(self):
        """Get currently active theme from themes app"""
        try:
            from apps.themes.models import StoreTheme
            return StoreTheme.objects.filter(store=self, is_active=True).first()
        except ImportError:
            return None
    
    def update_analytics(self):
        """Update cached analytics data for dashboard performance"""
        from django.db.models import Sum, Count
        
        # Update product count
        if hasattr(self, 'products'):
            self.current_products_count = self.products.filter(status='published').count()
            self.total_products = self.current_products_count
        
        # Update order analytics
        if hasattr(self, 'orders'):
            orders = self.orders.filter(status='completed')
            self.total_orders = orders.count()
            
            # This month's orders
            from django.utils import timezone
            now = timezone.now()
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            self.current_month_orders = orders.filter(created_at__gte=month_start).count()
            
            # Total revenue
            revenue_data = orders.aggregate(total=Sum('total_amount'))
            self.total_revenue = revenue_data['total'] or 0
        
        # Update customer count
        if hasattr(self, 'customers'):
            self.total_customers = self.customers.count()
        
        self.save(update_fields=[
            'total_products', 'total_orders', 'total_revenue', 
            'total_customers', 'current_products_count', 'current_month_orders'
        ])


class StoreSettings(models.Model):
    """Store-specific settings and configurations"""
    
    store = models.OneToOneField(Store, on_delete=models.CASCADE, related_name='settings')
    
    # SEO Settings
    google_analytics_id = models.CharField(max_length=20, blank=True, verbose_name='Google Analytics ID')
    google_tag_manager_id = models.CharField(max_length=20, blank=True, verbose_name='Google Tag Manager ID')
    facebook_pixel_id = models.CharField(max_length=20, blank=True, verbose_name='Facebook Pixel ID')
    
    # Business Settings
    enable_reviews = models.BooleanField(default=True, verbose_name='فعال‌سازی نظرات')
    enable_wishlist = models.BooleanField(default=True, verbose_name='فعال‌سازی لیست علاقه‌مندی')
    enable_comparison = models.BooleanField(default=True, verbose_name='فعال‌سازی مقایسه محصولات')
    
    # Notification Settings
    notify_new_orders = models.BooleanField(default=True, verbose_name='اطلاع‌رسانی سفارش جدید')
    notify_low_stock = models.BooleanField(default=True, verbose_name='اطلاع‌رسانی موجودی کم')
    notify_new_reviews = models.BooleanField(default=True, verbose_name='اطلاع‌رسانی نظر جدید')
    
    # Shipping Settings
    free_shipping_threshold = models.DecimalField(
        max_digits=10, 
        decimal_places=0, 
        default=0, 
        verbose_name='حد آستانه ارسال رایگان'
    )
    default_shipping_cost = models.DecimalField(
        max_digits=10, 
        decimal_places=0, 
        default=0, 
        verbose_name='هزینه پیش‌فرض ارسال'
    )
    
    # Additional configurations
    maintenance_mode = models.BooleanField(default=False, verbose_name='حالت تعمیر')
    custom_css = models.TextField(blank=True, verbose_name='CSS سفارشی')
    custom_js = models.TextField(blank=True, verbose_name='JavaScript سفارشی')
    
    class Meta:
        verbose_name = 'تنظیمات فروشگاه'
        verbose_name_plural = 'تنظیمات فروشگاه‌ها'


class StoreDomain(models.Model):
    """Domain management for stores"""
    
    DOMAIN_TYPES = [
        ('subdomain', 'زیردامنه'),
        ('custom', 'دامنه اختصاصی'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='domains')
    domain = models.CharField(max_length=255, unique=True, verbose_name='دامنه')
    domain_type = models.CharField(max_length=20, choices=DOMAIN_TYPES, default='subdomain')
    is_primary = models.BooleanField(default=False, verbose_name='دامنه اصلی')
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    is_https = models.BooleanField(default=True, verbose_name='HTTPS')
    ssl_verified = models.BooleanField(default=False, verbose_name='SSL تایید شده')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'دامنه فروشگاه'
        verbose_name_plural = 'دامنه‌های فروشگاه'
        indexes = [
            models.Index(fields=['domain']),
            models.Index(fields=['store', 'is_primary']),
            models.Index(fields=['domain_type', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.domain} ({'اصلی' if self.is_primary else 'فرعی'})"
