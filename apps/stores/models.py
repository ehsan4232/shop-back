from django.db import models
from django.core.exceptions import ValidationError
from django.utils.text import slugify
from django.conf import settings
import uuid

class Tenant(models.Model):
    """
    Tenant model for multi-tenancy support
    Each store operates as a separate tenant
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Schema and domain information
    schema_name = models.CharField(
        max_length=63, 
        unique=True,
        verbose_name='نام اسکیما',
        help_text='نام اسکیما پایگاه داده (حروف انگلیسی و خط تیره)'
    )
    domain_url = models.CharField(
        max_length=253, 
        unique=True,
        verbose_name='دامنه',
        help_text='دامنه فروشگاه (مثال: shop.mall.ir یا custom-domain.com)'
    )
    
    # Basic information
    name = models.CharField(max_length=100, verbose_name='نام')
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    is_custom_domain = models.BooleanField(default=False, verbose_name='دامنه اختصاصی')
    
    # Resource limits
    max_products = models.PositiveIntegerField(default=1000, verbose_name='حداکثر محصولات')
    max_customers = models.PositiveIntegerField(default=1000, verbose_name='حداکثر مشتریان')
    max_storage_mb = models.PositiveIntegerField(default=1000, verbose_name='حداکثر فضای ذخیره‌سازی (مگابایت)')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'public_tenant'  # Store in public schema
        verbose_name = 'مستأجر'
        verbose_name_plural = 'مستأجرها'
        indexes = [
            models.Index(fields=['domain_url']),
            models.Index(fields=['schema_name']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.domain_url})"
    
    def clean(self):
        # Validate schema name
        if self.schema_name:
            if not self.schema_name.replace('_', '').replace('-', '').isalnum():
                raise ValidationError('نام اسکیما باید شامل حروف انگلیسی، اعداد، خط تیره و زیرخط باشد')
            
            # Reserved schema names
            reserved_names = ['public', 'information_schema', 'pg_catalog', 'pg_toast']
            if self.schema_name.lower() in reserved_names:
                raise ValidationError('نام اسکیما رزرو شده است')
        
        # Validate domain
        if self.domain_url:
            self.domain_url = self.domain_url.lower().strip()
            if not self.domain_url.replace('.', '').replace('-', '').isalnum():
                raise ValidationError('دامنه نامعتبر است')
    
    def save(self, *args, **kwargs):
        # Auto-generate schema name from domain if not provided
        if not self.schema_name and self.domain_url:
            # Extract subdomain for schema name
            domain_parts = self.domain_url.split('.')
            if len(domain_parts) > 2 and not self.is_custom_domain:
                # Subdomain format: shop.mall.ir
                self.schema_name = slugify(domain_parts[0]).replace('-', '_')
            else:
                # Custom domain: use domain name
                self.schema_name = slugify(domain_parts[0]).replace('-', '_')
        
        self.clean()
        super().save(*args, **kwargs)
    
    @property
    def subdomain(self):
        """Extract subdomain from domain_url"""
        if self.is_custom_domain:
            return None
        parts = self.domain_url.split('.')
        return parts[0] if len(parts) > 1 else None
    
    def get_usage_stats(self):
        """Get tenant resource usage statistics"""
        try:
            store = self.store
            return {
                'products_count': store.products.count(),
                'customers_count': store.customers.count(),
                'orders_count': store.orders.count(),
                'storage_used_mb': self.calculate_storage_usage(),
                'products_usage_percent': (store.products.count() / self.max_products) * 100,
                'customers_usage_percent': (store.customers.count() / self.max_customers) * 100,
            }
        except:
            return {
                'products_count': 0,
                'customers_count': 0,
                'orders_count': 0,
                'storage_used_mb': 0,
                'products_usage_percent': 0,
                'customers_usage_percent': 0,
            }
    
    def calculate_storage_usage(self):
        """Calculate storage usage in MB"""
        # This would require file system integration
        # For now, return 0
        return 0
    
    def is_over_limits(self):
        """Check if tenant is over resource limits"""
        stats = self.get_usage_stats()
        return (
            stats['products_count'] > self.max_products or
            stats['customers_count'] > self.max_customers or
            stats['storage_used_mb'] > self.max_storage_mb
        )

class Store(models.Model):
    """
    Enhanced Store model with tenant relationship
    Represents an individual online store within the platform
    """
    STORE_TYPES = [
        ('general', 'عمومی'),
        ('fashion', 'مد و پوشاک'),
        ('jewelry', 'جواهرات'),
        ('electronics', 'الکترونیک'),
        ('home_garden', 'خانه و باغ'),
        ('beauty', 'زیبایی و بهداشت'),
        ('sports', 'ورزش'),
        ('books', 'کتاب و نشریات'),
        ('food', 'مواد غذایی'),
        ('automotive', 'خودرو'),
        ('services', 'خدمات'),
    ]
    
    SUBSCRIPTION_PLANS = [
        ('free', 'رایگان'),
        ('basic', 'پایه'),
        ('pro', 'حرفه‌ای'),
        ('enterprise', 'سازمانی'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Tenant relationship
    tenant = models.OneToOneField(
        Tenant, 
        on_delete=models.CASCADE,
        related_name='store',
        verbose_name='مستأجر'
    )
    
    # Store ownership
    owner = models.ForeignKey(
        'accounts.User', 
        on_delete=models.CASCADE,
        related_name='owned_stores',
        verbose_name='مالک فروشگاه'
    )
    
    # Basic information
    name = models.CharField(max_length=100, verbose_name='نام فروشگاه')
    name_fa = models.CharField(max_length=100, verbose_name='نام فارسی')
    slug = models.SlugField(max_length=100, verbose_name='نامک')
    description = models.TextField(blank=True, verbose_name='توضیحات')
    store_type = models.CharField(
        max_length=20, 
        choices=STORE_TYPES, 
        default='general',
        verbose_name='نوع فروشگاه'
    )
    
    # Subscription and plan
    subscription_plan = models.CharField(
        max_length=20, 
        choices=SUBSCRIPTION_PLANS, 
        default='free',
        verbose_name='پلان اشتراک'
    )
    subscription_expires_at = models.DateTimeField(
        null=True, 
        blank=True,
        verbose_name='انقضای اشتراک'
    )
    
    # Branding and appearance
    logo = models.ImageField(
        upload_to='store_logos/', 
        null=True, 
        blank=True,
        verbose_name='لوگو'
    )
    banner = models.ImageField(
        upload_to='store_banners/', 
        null=True, 
        blank=True,
        verbose_name='بنر'
    )
    primary_color = models.CharField(
        max_length=7, 
        default='#007bff',
        verbose_name='رنگ اصلی'
    )
    secondary_color = models.CharField(
        max_length=7, 
        default='#6c757d',
        verbose_name='رنگ ثانویه'
    )
    
    # Theme and layout
    theme = models.CharField(
        max_length=50, 
        default='modern',
        verbose_name='قالب',
        help_text='نام قالب انتخاب شده'
    )
    layout = models.CharField(
        max_length=50, 
        default='grid',
        verbose_name='چیدمان',
        choices=[
            ('grid', 'شبکه‌ای'),
            ('list', 'لیستی'),
            ('masonry', 'آجری'),
            ('carousel', 'کاروسل'),
        ]
    )
    custom_css = models.TextField(
        blank=True,
        verbose_name='CSS سفارشی',
        help_text='استایل‌های CSS اضافی'
    )
    
    # Domain configuration  
    custom_domain = models.CharField(
        max_length=255, 
        null=True, 
        blank=True,
        verbose_name='دامنه اختصاصی',
        help_text='دامنه شخصی فروشگاه (مثال: mystore.com)'
    )
    is_subdomain_active = models.BooleanField(
        default=True,
        verbose_name='زیردامنه فعال',
        help_text='آیا زیردامنه mall.ir فعال باشد؟'
    )
    
    # Contact information
    phone = models.CharField(max_length=15, blank=True, verbose_name='تلفن')
    email = models.EmailField(blank=True, verbose_name='ایمیل')
    address = models.TextField(blank=True, verbose_name='آدرس')
    city = models.CharField(max_length=100, blank=True, verbose_name='شهر')
    state = models.CharField(max_length=100, blank=True, verbose_name='استان')
    postal_code = models.CharField(max_length=10, blank=True, verbose_name='کد پستی')
    
    # Social media
    instagram_url = models.URLField(blank=True, verbose_name='اینستاگرام')
    telegram_url = models.URLField(blank=True, verbose_name='تلگرام')
    whatsapp_number = models.CharField(max_length=15, blank=True, verbose_name='واتساپ')
    
    # Business settings
    currency = models.CharField(
        max_length=3, 
        default='IRR',
        verbose_name='واحد پول'
    )
    tax_rate = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=0,
        verbose_name='نرخ مالیات (%)'
    )
    
    # SEO settings
    meta_title = models.CharField(max_length=200, blank=True, verbose_name='عنوان متا')
    meta_description = models.TextField(blank=True, verbose_name='توضیحات متا')
    meta_keywords = models.TextField(blank=True, verbose_name='کلمات کلیدی')
    
    # Status and analytics
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    is_verified = models.BooleanField(default=False, verbose_name='تأیید شده')
    is_featured = models.BooleanField(default=False, verbose_name='ویژه')
    
    # Analytics caching
    total_products = models.PositiveIntegerField(default=0, verbose_name='تعداد کل محصولات')
    total_orders = models.PositiveIntegerField(default=0, verbose_name='تعداد کل سفارشات')
    total_customers = models.PositiveIntegerField(default=0, verbose_name='تعداد کل مشتریان')
    monthly_revenue = models.DecimalField(
        max_digits=12, 
        decimal_places=0, 
        default=0,
        verbose_name='درآمد ماهانه'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='آخرین به‌روزرسانی')
    last_activity = models.DateTimeField(
        auto_now=True,
        verbose_name='آخرین فعالیت'
    )
    
    class Meta:
        verbose_name = 'فروشگاه'
        verbose_name_plural = 'فروشگاه‌ها'
        unique_together = ['owner', 'slug']
        indexes = [
            models.Index(fields=['tenant']),
            models.Index(fields=['owner']),
            models.Index(fields=['is_active', 'is_verified']),
            models.Index(fields=['store_type', 'is_active']),
            models.Index(fields=['subscription_plan']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return self.name_fa or self.name
    
    def save(self, *args, **kwargs):
        # Auto-generate slug from name
        if not self.slug:
            self.slug = slugify(self.name_fa or self.name)
        
        # Ensure unique slug for owner
        if not self.pk:
            original_slug = self.slug
            counter = 1
            while Store.objects.filter(owner=self.owner, slug=self.slug).exists():
                self.slug = f"{original_slug}-{counter}"
                counter += 1
        
        super().save(*args, **kwargs)
        
        # Update tenant domain if needed
        if self.tenant and not self.tenant.domain_url:
            if self.custom_domain:
                self.tenant.domain_url = self.custom_domain
                self.tenant.is_custom_domain = True
            else:
                self.tenant.domain_url = f"{self.slug}.{settings.PLATFORM_DOMAIN}"
                self.tenant.is_custom_domain = False
            self.tenant.save()
    
    @property
    def domain_url(self):
        """Get the store's accessible domain URL"""
        if self.custom_domain and self.tenant.is_custom_domain:
            return self.custom_domain
        elif self.is_subdomain_active:
            platform_domain = getattr(settings, 'PLATFORM_DOMAIN', 'mall.ir')
            return f"{self.slug}.{platform_domain}"
        return None
    
    @property
    def store_url(self):
        """Get the full store URL with protocol"""
        domain = self.domain_url
        if domain:
            protocol = 'https' if not settings.DEBUG else 'http'
            return f"{protocol}://{domain}"
        return None
    
    def get_dashboard_url(self):
        """Get admin dashboard URL for this store"""
        return f"/admin/stores/{self.id}/"
    
    def can_add_product(self):
        """Check if store can add more products"""
        if self.tenant:
            return self.total_products < self.tenant.max_products
        return True
    
    def can_add_customer(self):
        """Check if store can add more customers"""
        if self.tenant:
            return self.total_customers < self.tenant.max_customers
        return True
    
    def update_analytics_cache(self):
        """Update cached analytics data"""
        self.total_products = self.products.filter(status='published').count()
        self.total_customers = self.customers.count()
        self.total_orders = self.orders.count()
        
        # Calculate monthly revenue
        from django.utils import timezone
        from datetime import timedelta
        
        thirty_days_ago = timezone.now() - timedelta(days=30)
        monthly_orders = self.orders.filter(
            created_at__gte=thirty_days_ago,
            status='completed'
        )
        self.monthly_revenue = sum(order.total_amount for order in monthly_orders)
        
        self.save(update_fields=[
            'total_products', 
            'total_customers', 
            'total_orders', 
            'monthly_revenue'
        ])
    
    def get_subscription_limits(self):
        """Get subscription plan limits"""
        limits = {
            'free': {'products': 50, 'storage_mb': 100},
            'basic': {'products': 500, 'storage_mb': 1000},
            'pro': {'products': 2000, 'storage_mb': 5000},
            'enterprise': {'products': 10000, 'storage_mb': 20000},
        }
        return limits.get(self.subscription_plan, limits['free'])
    
    def is_subscription_active(self):
        """Check if subscription is active"""
        if self.subscription_plan == 'free':
            return True
        
        if self.subscription_expires_at:
            from django.utils import timezone
            return timezone.now() < self.subscription_expires_at
        
        return False

# Store staff management
class StoreStaff(models.Model):
    """Store staff members with role-based permissions"""
    ROLES = [
        ('admin', 'مدیر'),
        ('manager', 'مدیر فروش'),
        ('editor', 'ویرایشگر'),
        ('viewer', 'بازدیدکننده'),
    ]
    
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='staff')
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLES, verbose_name='نقش')
    permissions = models.JSONField(
        default=dict,
        verbose_name='مجوزها',
        help_text='مجوزهای اضافی برای این کاربر'
    )
    
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    invited_by = models.ForeignKey(
        'accounts.User', 
        on_delete=models.SET_NULL,
        null=True,
        related_name='invited_staff',
        verbose_name='دعوت‌کننده'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['store', 'user']
        verbose_name = 'کارمند فروشگاه'
        verbose_name_plural = 'کارمندان فروشگاه'
    
    def __str__(self):
        return f"{self.user.full_name} - {self.store.name} ({self.get_role_display()})"

# Store settings for different configurations
class StoreSetting(models.Model):
    """Flexible store settings storage"""
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='settings')
    key = models.CharField(max_length=100, verbose_name='کلید')
    value = models.TextField(verbose_name='مقدار')
    value_type = models.CharField(
        max_length=20,
        choices=[
            ('string', 'متن'),
            ('integer', 'عدد صحیح'),
            ('float', 'عدد اعشاری'),
            ('boolean', 'بولی'),
            ('json', 'JSON'),
        ],
        default='string',
        verbose_name='نوع مقدار'
    )
    description = models.TextField(blank=True, verbose_name='توضیحات')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['store', 'key']
        verbose_name = 'تنظیم فروشگاه'
        verbose_name_plural = 'تنظیمات فروشگاه'
    
    def get_typed_value(self):
        """Get value in appropriate type"""
        if self.value_type == 'integer':
            return int(self.value)
        elif self.value_type == 'float':
            return float(self.value)
        elif self.value_type == 'boolean':
            return self.value.lower() in ['true', '1', 'yes']
        elif self.value_type == 'json':
            import json
            return json.loads(self.value)
        else:
            return self.value
