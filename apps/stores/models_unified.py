from django.db import models
from django.utils.text import slugify
from django.conf import settings
from django.core.exceptions import ValidationError
import uuid

# CRITICAL FIX: Enhanced Store model integrated with Tenant functionality
# Eliminates duplication between Store and Tenant models

class Store(models.Model):
    """
    UNIFIED Store model with multi-tenant capabilities
    Combines Store and Tenant functionality to eliminate duplication
    Product Requirements: 
    - Independent domains/subdomains
    - Theme selection  
    - 1000+ store owners support
    - Complete tenant isolation
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
    slug = models.SlugField(max_length=100, unique=True, verbose_name='نامک')
    description = models.TextField(blank=True, verbose_name='توضیحات')
    
    # UNIFIED: Multi-tenant schema name for complete data isolation
    schema_name = models.CharField(
        max_length=63, 
        unique=True, 
        verbose_name='نام schema پایگاه داده',
        help_text='نام منحصر به فرد برای جداسازی داده‌ها'
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
        verbose_name='زیردامنه',
        help_text='نام زیردامنه (مثال: mystore.mall.ir)'
    )
    
    # Theme system (product requirement: "various fancy and modern designs and layouts and themes")
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
    
    # ADDED: Subscription and billing (from Tenant model)
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
    paid_until = models.DateField(null=True, blank=True, verbose_name='تاریخ انقضای پرداخت')
    on_trial = models.BooleanField(default=True, verbose_name='در دوره آزمایشی')
    trial_ends_at = models.DateTimeField(null=True, blank=True, verbose_name='پایان دوره آزمایشی')
    
    # ADDED: Business limitations based on subscription
    max_products = models.PositiveIntegerField(default=100, verbose_name='حداکثر محصولات')
    max_storage_mb = models.PositiveIntegerField(default=1000, verbose_name='حداکثر فضای ذخیره (MB)')
    max_orders_per_month = models.PositiveIntegerField(default=1000, verbose_name='حداکثر سفارش در ماه')
    
    # Contact info
    phone = models.CharField(max_length=15, blank=True, verbose_name='تلفن')
    email = models.EmailField(blank=True, verbose_name='ایمیل')
    address = models.TextField(blank=True, verbose_name='آدرس')
    
    # ADDED: Store branding and appearance
    logo = models.ImageField(upload_to='store_logos/', null=True, blank=True, verbose_name='لوگو')
    primary_color = models.CharField(max_length=7, default='#007bff', verbose_name='رنگ اصلی')
    secondary_color = models.CharField(max_length=7, default='#6c757d', verbose_name='رنگ فرعی')
    
    # ADDED: Business settings  
    currency = models.CharField(max_length=3, default='IRR', verbose_name='واحد پول')
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name='نرخ مالیات (%)')
    
    # Status
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    
    # ENHANCED: Analytics cache (product requirement: "dashboards of charts and info")
    total_products = models.PositiveIntegerField(default=0, verbose_name='تعداد محصولات')
    total_orders = models.PositiveIntegerField(default=0, verbose_name='تعداد سفارشات')
    total_revenue = models.DecimalField(max_digits=15, decimal_places=0, default=0, verbose_name='درآمد کل')
    total_customers = models.PositiveIntegerField(default=0, verbose_name='تعداد مشتریان')
    
    # ADDED: Usage tracking for subscription limits
    current_products_count = models.PositiveIntegerField(default=0, verbose_name='تعداد محصولات فعلی')
    current_storage_mb = models.PositiveIntegerField(default=0, verbose_name='فضای استفاده شده (MB)')
    current_month_orders = models.PositiveIntegerField(default=0, verbose_name='سفارشات ماه جاری')
    
    # ADDED: SEO and social media
    meta_title = models.CharField(max_length=200, blank=True, verbose_name='عنوان متا')
    meta_description = models.TextField(blank=True, verbose_name='توضیحات متا')
    social_media_links = models.JSONField(default=dict, blank=True, verbose_name='لینک‌های شبکه‌های اجتماعی')
    
    # ADDED: Feature flags based on subscription
    enable_sms_campaigns = models.BooleanField(default=False, verbose_name='کمپین‌های SMS')
    enable_advanced_analytics = models.BooleanField(default=False, verbose_name='آمار پیشرفته')
    enable_custom_domain = models.BooleanField(default=False, verbose_name='دامنه اختصاصی')
    enable_api_access = models.BooleanField(default=False, verbose_name='دسترسی API')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='آخرین بروزرسانی')
    
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
        """Enhanced validation for unified model"""
        super().clean()
        
        # Validate schema name format
        if self.schema_name and not self.schema_name.replace('_', '').isalnum():
            raise ValidationError({
                'schema_name': 'نام schema باید فقط شامل حروف، اعداد و _ باشد'
            })
        
        # Ensure subdomain is valid
        if self.subdomain and not self.subdomain.replace('-', '').isalnum():
            raise ValidationError({
                'subdomain': 'نام زیردامنه باید فقط شامل حروف، اعداد و - باشد'
            })
    
    def save(self, *args, **kwargs):
        # Auto-generate slug if not provided
        if not self.slug:
            self.slug = slugify(self.name_fa or self.name)
        
        # Auto-generate schema name if not provided
        if not self.schema_name:
            self.schema_name = f"store_{self.slug}_{uuid.uuid4().hex[:8]}"
        
        # Auto-generate subdomain if not provided
        if not self.subdomain:
            self.subdomain = self.slug
        
        # Ensure unique slug, schema_name, and subdomain
        if not self.pk:
            # Make slug unique
            original_slug = self.slug
            counter = 1
            while Store.objects.filter(slug=self.slug).exists():
                self.slug = f"{original_slug}-{counter}"
                counter += 1
            
            # Make subdomain unique
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
            return self.trial_ends_at and timezone.now() < self.trial_ends_at
        return self.paid_until and timezone.now().date() <= self.paid_until
    
    def is_within_limits(self):
        """Check if store is within subscription limits"""
        return (
            self.current_products_count <= self.max_products and
            self.current_storage_mb <= self.max_storage_mb and
            self.current_month_orders <= self.max_orders_per_month
        )
    
    def get_usage_percentage(self, resource_type):
        """Get usage percentage for a specific resource"""
        if resource_type == 'products':
            return (self.current_products_count / self.max_products) * 100 if self.max_products > 0 else 0
        elif resource_type == 'storage':
            return (self.current_storage_mb / self.max_storage_mb) * 100 if self.max_storage_mb > 0 else 0
        elif resource_type == 'orders':
            return (self.current_month_orders / self.max_orders_per_month) * 100 if self.max_orders_per_month > 0 else 0
        return 0
    
    def can_add_product(self):
        """Check if store can add more products"""
        return self.current_products_count < self.max_products
    
    def can_create_order(self):
        """Check if store can create more orders this month"""
        return self.current_month_orders < self.max_orders_per_month
    
    def update_analytics(self):
        """Update cached analytics data"""
        # Update product count
        self.total_products = self.products.filter(status='published').count()
        self.current_products_count = self.total_products
        
        # Update order stats
        self.total_orders = self.orders.count()
        
        # Update revenue
        from django.db.models import Sum
        total_revenue = self.orders.filter(
            payment_status='paid'
        ).aggregate(Sum('total_amount'))['total_amount__sum'] or 0
        self.total_revenue = total_revenue
        
        # Update customer count
        self.total_customers = self.orders.values('customer').distinct().count()
        
        # Update current month orders
        from django.utils import timezone
        current_month = timezone.now().replace(day=1)
        self.current_month_orders = self.orders.filter(
            created_at__gte=current_month
        ).count()
        
        self.save(update_fields=[
            'total_products', 'total_orders', 'total_revenue', 'total_customers',
            'current_products_count', 'current_month_orders'
        ])
    
    def get_social_media_link(self, platform):
        """Get social media link for a specific platform"""
        return self.social_media_links.get(platform, '')
    
    def set_social_media_link(self, platform, url):
        """Set social media link for a specific platform"""
        if not self.social_media_links:
            self.social_media_links = {}
        self.social_media_links[platform] = url
        self.save(update_fields=['social_media_links'])

# ADDED: Store Domain management (previously separate Domain model)
class StoreDomain(models.Model):
    """
    Domain management for stores
    Supports both subdomains and custom domains
    """
    
    DOMAIN_TYPES = [
        ('subdomain', 'زیردامنه'),
        ('custom', 'دامنه اختصاصی'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    store = models.ForeignKey(
        Store, 
        on_delete=models.CASCADE, 
        related_name='domains',
        verbose_name='فروشگاه'
    )
    
    domain = models.CharField(
        max_length=255, 
        unique=True,
        verbose_name='دامنه',
        help_text='مثال: mystore.mall.ir یا mystore.com'
    )
    domain_type = models.CharField(
        max_length=20, 
        choices=DOMAIN_TYPES, 
        default='subdomain',
        verbose_name='نوع دامنه'
    )
    
    is_primary = models.BooleanField(default=False, verbose_name='دامنه اصلی')
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    is_https = models.BooleanField(default=True, verbose_name='پشتیبانی HTTPS')
    
    # SSL Certificate information
    ssl_verified = models.BooleanField(default=False, verbose_name='گواهی SSL تایید شده')
    ssl_expires_at = models.DateTimeField(null=True, blank=True, verbose_name='انقضای SSL')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='آخرین بروزرسانی')
    
    class Meta:
        verbose_name = 'دامنه فروشگاه'
        verbose_name_plural = 'دامنه‌های فروشگاه'
        ordering = ['-is_primary', 'domain']
        indexes = [
            models.Index(fields=['domain']),
            models.Index(fields=['store', 'is_primary']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.domain} ({'اصلی' if self.is_primary else 'فرعی'})"
    
    def save(self, *args, **kwargs):
        # Ensure only one primary domain per store
        if self.is_primary:
            StoreDomain.objects.filter(
                store=self.store, 
                is_primary=True
            ).exclude(pk=self.pk).update(is_primary=False)
        
        super().save(*args, **kwargs)

# Signal handlers for maintaining data consistency
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

@receiver(post_save, sender=Store)
def create_default_domain(sender, instance, created, **kwargs):
    """Create default domain when a new store is created"""
    if created:
        StoreDomain.objects.create(
            store=instance,
            domain=instance.domain_url,
            domain_type='subdomain',
            is_primary=True,
            is_active=True
        )