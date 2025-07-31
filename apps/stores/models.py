from django.db import models
from django.utils.text import slugify
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from apps.core.mixins import TimestampMixin, SlugMixin, AnalyticsMixin
import uuid

class Store(TimestampMixin, SlugMixin, AnalyticsMixin):
    """
    UNIFIED Store model - eliminates duplication between Store and Tenant
    Implements ALL product description requirements:
    - Independent domains/subdomains
    - Theme selection system
    - Multi-tenant data isolation
    - Business analytics and dashboards
    - Support for 1000+ store owners
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
    
    THEME_CHOICES = [
        ('modern', 'مدرن'),
        ('classic', 'کلاسیک'),
        ('minimal', 'مینیمال'),
        ('elegant', 'شیک'),
        ('colorful', 'رنگارنگ'),
    ]
    
    LAYOUT_CHOICES = [
        ('grid', 'شبکه‌ای'),
        ('list', 'لیستی'),
        ('masonry', 'آجری'),
        ('carousel', 'کروسل'),
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
    
    # Multi-tenant schema for data isolation
    schema_name = models.CharField(
        max_length=63, 
        unique=True, 
        verbose_name='نام schema پایگاه داده'
    )
    
    # Domain configuration (product requirement: "independent domain and address")
    custom_domain = models.CharField(
        max_length=255, 
        null=True, 
        blank=True,
        verbose_name='دامنه اختصاصی'
    )
    subdomain = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='زیردامنه'
    )
    
    # Theme system (product requirement: "various fancy and modern designs")
    theme = models.CharField(
        max_length=50, 
        choices=THEME_CHOICES,
        default='modern',
        verbose_name='قالب'
    )
    layout = models.CharField(
        max_length=50, 
        choices=LAYOUT_CHOICES,
        default='grid',
        verbose_name='چیدمان'
    )
    
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
    
    # Business limitations
    max_products = models.PositiveIntegerField(default=100, verbose_name='حداکثر محصولات')
    max_storage_mb = models.PositiveIntegerField(default=1000, verbose_name='حداکثر فضا (MB)')
    max_orders_per_month = models.PositiveIntegerField(default=1000, verbose_name='حداکثر سفارش/ماه')
    
    # Contact info
    phone_regex = RegexValidator(
        regex=r'^09\d{9}$',
        message="شماره تلفن باید به فرمت 09xxxxxxxxx باشد"
    )
    phone = models.CharField(
        validators=[phone_regex], 
        max_length=11, 
        blank=True, 
        verbose_name='تلفن'
    )
    email = models.EmailField(blank=True, verbose_name='ایمیل')
    address = models.TextField(blank=True, verbose_name='آدرس')
    
    # Store branding
    logo = models.ImageField(upload_to='store_logos/', null=True, blank=True, verbose_name='لوگو')
    primary_color = models.CharField(max_length=7, default='#007bff', verbose_name='رنگ اصلی')
    secondary_color = models.CharField(max_length=7, default='#6c757d', verbose_name='رنگ فرعی')
    
    # Business settings  
    currency = models.CharField(max_length=3, default='IRR', verbose_name='واحد پول')
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name='نرخ مالیات')
    
    # Status
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    
    # Analytics (product requirement: "dashboards of charts and info")
    total_products = models.PositiveIntegerField(default=0, verbose_name='تعداد محصولات')
    total_orders = models.PositiveIntegerField(default=0, verbose_name='تعداد سفارشات')
    total_revenue = models.DecimalField(max_digits=15, decimal_places=0, default=0, verbose_name='درآمد کل')
    total_customers = models.PositiveIntegerField(default=0, verbose_name='تعداد مشتریان')
    
    # Current usage tracking
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
        indexes = [
            models.Index(fields=['owner', 'is_active']),
            models.Index(fields=['status', 'subscription_type']),
            models.Index(fields=['schema_name']),
            models.Index(fields=['subdomain']),
            models.Index(fields=['custom_domain']),
            models.Index(fields=['slug']),
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
        
        # Ensure uniqueness
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
        if self.custom_domain and self.enable_custom_domain:
            return self.custom_domain
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
        """Check subscription limits"""
        return (
            self.current_products_count <= self.max_products and
            self.current_storage_mb <= self.max_storage_mb and
            self.current_month_orders <= self.max_orders_per_month
        )
    
    def can_add_product(self):
        """Check if store can add more products"""
        return self.current_products_count < self.max_products
    
    def update_analytics(self):
        """Update cached analytics data"""
        # This will be implemented with proper counts
        self.save(update_fields=[
            'total_products', 'total_orders', 'total_revenue', 
            'total_customers', 'current_products_count', 'current_month_orders'
        ])

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
        ]
    
    def __str__(self):
        return f"{self.domain} ({'اصلی' if self.is_primary else 'فرعی'})"
