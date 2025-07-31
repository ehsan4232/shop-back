from django_tenants.models import TenantMixin, DomainMixin
from django.db import models
from django.core.validators import RegexValidator
import uuid

class Tenant(TenantMixin):
    """
    Tenant model for multi-tenancy support
    Each store gets its own schema
    """
    # Basic info
    name = models.CharField(max_length=100, verbose_name='نام فروشگاه')
    display_name = models.CharField(max_length=100, verbose_name='نام نمایشی')
    description = models.TextField(blank=True, verbose_name='توضیحات')
    
    # Business info
    business_type = models.CharField(
        max_length=50,
        choices=[
            ('clothing', 'پوشاک'),
            ('jewelry', 'جواهرات'),
            ('electronics', 'الکترونیک'),
            ('pet_shop', 'حیوانات خانگی'),
            ('services', 'خدمات'),
            ('accessories', 'لوازم جانبی'),
            ('other', 'سایر'),
        ],
        default='other',
        verbose_name='نوع کسب‌وکار'
    )
    
    # Contact info
    phone_regex = RegexValidator(
        regex=r'^09\d{9}$',
        message="شماره تلفن باید به فرمت 09xxxxxxxxx باشد"
    )
    owner_phone = models.CharField(
        validators=[phone_regex], 
        max_length=11,
        verbose_name='شماره تلفن مالک'
    )
    email = models.EmailField(blank=True, verbose_name='ایمیل')
    
    # Subscription
    paid_until = models.DateField(verbose_name='پرداخت تا تاریخ')
    on_trial = models.BooleanField(default=True, verbose_name='دوره آزمایشی')
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    
    # Timestamps
    created_on = models.DateField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    
    # Platform settings
    theme = models.CharField(
        max_length=50,
        default='modern',
        choices=[
            ('modern', 'مدرن'),
            ('classic', 'کلاسیک'),
            ('minimal', 'مینیمال'),
            ('elegant', 'شیک'),
        ],
        verbose_name='قالب'
    )
    
    # Analytics
    total_products = models.PositiveIntegerField(default=0, verbose_name='تعداد محصولات')
    total_orders = models.PositiveIntegerField(default=0, verbose_name='تعداد سفارشات')
    
    class Meta:
        verbose_name = 'فروشگاه'
        verbose_name_plural = 'فروشگاه‌ها'
    
    def __str__(self):
        return self.display_name or self.name
    
    def auto_create_schema(self):
        """
        Auto-create schema name based on business name
        Product description: "Shops can have their own independent domain"
        """
        if not self.schema_name:
            # Create schema name from display name
            import re
            from unidecode import unidecode
            
            # Convert Persian to English
            name = unidecode(self.display_name or self.name)
            # Remove special characters and spaces
            name = re.sub(r'[^a-zA-Z0-9]', '', name).lower()
            # Ensure it starts with a letter
            if name and not name[0].isalpha():
                name = 'shop' + name
            # Truncate to fit database constraints
            name = name[:50]
            # Add unique suffix if needed
            if Tenant.objects.filter(schema_name=name).exists():
                name = f"{name}{uuid.uuid4().hex[:6]}"
            
            self.schema_name = name
    
    def save(self, *args, **kwargs):
        if not self.schema_name:
            self.auto_create_schema()
        super().save(*args, **kwargs)

class Domain(DomainMixin):
    """
    Domain model for tenant routing
    Product description: "Shops can have their own independent domain and address. 
    It might or might not be a subdomain of my platform."
    """
    # Additional domain-specific fields
    is_custom_domain = models.BooleanField(
        default=False, 
        verbose_name='دامنه سفارشی'
    )
    ssl_enabled = models.BooleanField(
        default=False,
        verbose_name='SSL فعال'
    )
    dns_verified = models.BooleanField(
        default=False,
        verbose_name='DNS تأیید شده'
    )
    
    class Meta:
        verbose_name = 'دامنه'
        verbose_name_plural = 'دامنه‌ها'
    
    def __str__(self):
        return self.domain
    
    @property
    def is_subdomain(self):
        """Check if this is a subdomain of the platform"""
        return '.mall.ir' in self.domain
    
    @property
    def full_url(self):
        """Get full URL with proper protocol"""
        protocol = 'https' if self.ssl_enabled else 'http'
        return f"{protocol}://{self.domain}"

# Signal handlers for tenant management
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

@receiver(post_save, sender=Tenant)
def create_default_domain(sender, instance, created, **kwargs):
    """Create default subdomain when tenant is created"""
    if created and not instance.domains.exists():
        # Create default subdomain
        default_domain = f"{instance.schema_name}.mall.ir"
        Domain.objects.create(
            domain=default_domain,
            tenant=instance,
            is_primary=True,
            is_custom_domain=False
        )

@receiver(pre_delete, sender=Tenant)
def cleanup_tenant_data(sender, instance, **kwargs):
    """Cleanup when tenant is deleted"""
    # Additional cleanup logic can be added here
    pass
