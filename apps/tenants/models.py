from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
import uuid


class Tenant(models.Model):
    """
    Multi-tenant model for store isolation
    Each tenant represents an independent store with complete data separation
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
    
    # Primary identification
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Tenant information
    name = models.CharField(max_length=100, verbose_name='نام فروشگاه')
    schema_name = models.CharField(
        max_length=63, 
        unique=True, 
        verbose_name='نام schema پایگاه داده',
        help_text='نام منحصر به فرد برای جداسازی داده‌ها'
    )
    
    # Subscription and billing
    subscription_type = models.CharField(
        max_length=20, 
        choices=SUBSCRIPTION_TYPES, 
        default='trial',
        verbose_name='نوع اشتراک'
    )
    paid_until = models.DateField(verbose_name='تاریخ انقضای پرداخت')
    on_trial = models.BooleanField(default=True, verbose_name='در دوره آزمایشی')
    trial_ends_at = models.DateTimeField(null=True, blank=True, verbose_name='پایان دوره آزمایشی')
    
    # Status and settings
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='pending',
        verbose_name='وضعیت'
    )
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    
    # Limitations based on subscription
    max_products = models.PositiveIntegerField(default=100, verbose_name='حداکثر محصولات')
    max_storage_mb = models.PositiveIntegerField(default=1000, verbose_name='حداکثر فضای ذخیره (MB)')
    max_orders_per_month = models.PositiveIntegerField(default=1000, verbose_name='حداکثر سفارش در ماه')
    
    # Contact information
    owner_name = models.CharField(max_length=100, verbose_name='نام مالک')
    owner_phone = models.CharField(max_length=15, verbose_name='تلفن مالک')
    owner_email = models.EmailField(blank=True, verbose_name='ایمیل مالک')
    
    # Timestamps
    created_on = models.DateField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='آخرین بروزرسانی')
    
    # Usage tracking
    current_products_count = models.PositiveIntegerField(default=0, verbose_name='تعداد محصولات فعلی')
    current_storage_mb = models.PositiveIntegerField(default=0, verbose_name='فضای استفاده شده (MB)')
    current_month_orders = models.PositiveIntegerField(default=0, verbose_name='سفارشات ماه جاری')
    
    class Meta:
        verbose_name = 'مستاجر (فروشگاه)'
        verbose_name_plural = 'مستاجران (فروشگاه‌ها)'
        ordering = ['-created_on']
        indexes = [
            models.Index(fields=['schema_name']),
            models.Index(fields=['status', 'is_active']),
            models.Index(fields=['subscription_type']),
            models.Index(fields=['paid_until']),
            models.Index(fields=['on_trial']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.schema_name})"
    
    def clean(self):
        """Validate tenant data"""
        super().clean()
        
        # Validate schema name format
        if not self.schema_name.replace('_', '').isalnum():
            raise ValidationError({
                'schema_name': 'نام schema باید فقط شامل حروف، اعداد و _ باشد'
            })
        
        # Ensure trial period is set
        if self.on_trial and not self.trial_ends_at:
            self.trial_ends_at = timezone.now() + timezone.timedelta(days=30)
    
    def is_subscription_active(self):
        """Check if subscription is active"""
        if self.on_trial:
            return self.trial_ends_at and timezone.now() < self.trial_ends_at
        return self.paid_until >= timezone.now().date()
    
    def is_within_limits(self):
        """Check if tenant is within subscription limits"""
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
    
    def update_usage_stats(self):
        """Update current usage statistics"""
        # This would be implemented based on your actual models
        # For now, it's a placeholder for the counting logic
        pass


class Domain(models.Model):
    """
    Domain management for tenants
    Supports both subdomains and custom domains
    """
    
    DOMAIN_TYPES = [
        ('subdomain', 'زیردامنه'),
        ('custom', 'دامنه اختصاصی'),
    ]
    
    # Primary identification
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Related tenant
    tenant = models.ForeignKey(
        Tenant, 
        on_delete=models.CASCADE, 
        related_name='domains',
        verbose_name='مستاجر'
    )
    
    # Domain information
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
    
    # Status
    is_primary = models.BooleanField(default=False, verbose_name='دامنه اصلی')
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    is_https = models.BooleanField(default=True, verbose_name='پشتیبانی HTTPS')
    
    # SSL Certificate information
    ssl_verified = models.BooleanField(default=False, verbose_name='گواهی SSL تایید شده')
    ssl_expires_at = models.DateTimeField(null=True, blank=True, verbose_name='انقضای SSL')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='آخرین بروزرسانی')
    verified_at = models.DateTimeField(null=True, blank=True, verbose_name='تاریخ تایید')
    
    class Meta:
        verbose_name = 'دامنه'
        verbose_name_plural = 'دامنه‌ها'
        ordering = ['-is_primary', 'domain']
        indexes = [
            models.Index(fields=['domain']),
            models.Index(fields=['tenant', 'is_primary']),
            models.Index(fields=['is_active']),
            models.Index(fields=['domain_type']),
        ]
    
    def __str__(self):
        return f"{self.domain} ({'اصلی' if self.is_primary else 'فرعی'})"
    
    def clean(self):
        """Validate domain data"""
        super().clean()
        
        # Validate domain format
        import re
        domain_pattern = re.compile(
            r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$'
        )
        if not domain_pattern.match(self.domain):
            raise ValidationError({
                'domain': 'فرمت دامنه نادرست است'
            })
    
    def save(self, *args, **kwargs):
        # Ensure only one primary domain per tenant
        if self.is_primary:
            Domain.objects.filter(
                tenant=self.tenant, 
                is_primary=True
            ).exclude(pk=self.pk).update(is_primary=False)
        
        super().save(*args, **kwargs)
    
    @property
    def full_url(self):
        """Get full URL with protocol"""
        protocol = 'https' if self.is_https else 'http'
        return f"{protocol}://{self.domain}"
    
    def is_ssl_valid(self):
        """Check if SSL certificate is valid and not expired"""
        if not self.ssl_verified:
            return False
        if self.ssl_expires_at and timezone.now() > self.ssl_expires_at:
            return False
        return True


class TenantSettings(models.Model):
    """
    Tenant-specific settings and configurations
    """
    
    # Primary identification
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Related tenant
    tenant = models.OneToOneField(
        Tenant, 
        on_delete=models.CASCADE, 
        related_name='settings',
        verbose_name='مستاجر'
    )
    
    # Theme and branding
    theme_name = models.CharField(
        max_length=50, 
        default='default',
        verbose_name='نام قالب'
    )
    primary_color = models.CharField(
        max_length=7, 
        default='#007bff',
        verbose_name='رنگ اصلی'
    )
    secondary_color = models.CharField(
        max_length=7, 
        default='#6c757d',
        verbose_name='رنگ فرعی'
    )
    logo_url = models.URLField(blank=True, verbose_name='لینک لوگو')
    
    # Business settings
    currency = models.CharField(
        max_length=3, 
        default='IRR',
        verbose_name='واحد پول'
    )
    timezone = models.CharField(
        max_length=50, 
        default='Asia/Tehran',
        verbose_name='منطقه زمانی'
    )
    language = models.CharField(
        max_length=10, 
        default='fa-IR',
        verbose_name='زبان'
    )
    
    # Feature flags
    enable_multi_language = models.BooleanField(default=False, verbose_name='چندزبانه')
    enable_reviews = models.BooleanField(default=True, verbose_name='نظرات')
    enable_wishlist = models.BooleanField(default=True, verbose_name='لیست علاقه‌مندی')
    enable_compare = models.BooleanField(default=True, verbose_name='مقایسه محصولات')
    enable_social_login = models.BooleanField(default=False, verbose_name='ورود با شبکه‌های اجتماعی')
    
    # SEO settings
    meta_title = models.CharField(max_length=200, blank=True, verbose_name='عنوان متا')
    meta_description = models.TextField(blank=True, verbose_name='توضیحات متا')
    meta_keywords = models.TextField(blank=True, verbose_name='کلمات کلیدی متا')
    
    # Contact information
    contact_email = models.EmailField(blank=True, verbose_name='ایمیل تماس')
    contact_phone = models.CharField(max_length=15, blank=True, verbose_name='تلفن تماس')
    address = models.TextField(blank=True, verbose_name='آدرس')
    
    # Social media
    social_media_links = models.JSONField(
        default=dict, 
        blank=True,
        verbose_name='لینک‌های شبکه‌های اجتماعی'
    )
    
    # Analytics
    google_analytics_id = models.CharField(max_length=50, blank=True, verbose_name='شناسه Google Analytics')
    facebook_pixel_id = models.CharField(max_length=50, blank=True, verbose_name='شناسه Facebook Pixel')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='آخرین بروزرسانی')
    
    class Meta:
        verbose_name = 'تنظیمات مستاجر'
        verbose_name_plural = 'تنظیمات مستاجران'
    
    def __str__(self):
        return f"تنظیمات {self.tenant.name}"
    
    def get_social_media_link(self, platform):
        """Get social media link for a specific platform"""
        return self.social_media_links.get(platform, '')
    
    def set_social_media_link(self, platform, url):
        """Set social media link for a specific platform"""
        if not self.social_media_links:
            self.social_media_links = {}
        self.social_media_links[platform] = url
        self.save(update_fields=['social_media_links'])


# Signal handlers for tenant management
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

@receiver(post_save, sender=Tenant)
def create_tenant_settings(sender, instance, created, **kwargs):
    """Create default settings when a new tenant is created"""
    if created:
        TenantSettings.objects.create(tenant=instance)

@receiver(post_save, sender=Tenant)
def create_default_domain(sender, instance, created, **kwargs):
    """Create default subdomain when a new tenant is created"""
    if created:
        default_domain = f"{instance.schema_name}.mall.ir"
        Domain.objects.create(
            tenant=instance,
            domain=default_domain,
            domain_type='subdomain',
            is_primary=True,
            is_active=True
        )
