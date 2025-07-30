"""
Core models for Mall Platform
Provides base models and mixins for multi-tenant architecture
"""

from django.db import models
from django.core.cache import cache
from django.utils.text import slugify
from django.utils import timezone
import uuid


class Store(models.Model):
    """
    Central store model for multi-tenant architecture
    Each store represents a separate shop with isolated data
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Basic store information
    name = models.CharField(max_length=100, verbose_name='نام فروشگاه')
    name_fa = models.CharField(max_length=100, verbose_name='نام فارسی')
    description = models.TextField(blank=True, verbose_name='توضیحات')
    
    # Owner
    owner = models.ForeignKey(
        'accounts.User', 
        on_delete=models.CASCADE, 
        related_name='owned_stores',
        verbose_name='مالک فروشگاه'
    )
    
    # Domain and branding
    subdomain = models.CharField(max_length=63, unique=True, verbose_name='زیردامنه')
    custom_domain = models.CharField(max_length=255, null=True, blank=True, verbose_name='دامنه اختصاصی')
    logo = models.ImageField(upload_to='store_logos/', null=True, blank=True, verbose_name='لوگو')
    
    # Theme and layout
    theme = models.CharField(max_length=50, default='default', verbose_name='قالب')
    layout = models.CharField(max_length=50, default='grid', verbose_name='چیدمان')
    
    # Settings
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    is_verified = models.BooleanField(default=False, verbose_name='تایید شده')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاریخ بروزرسانی')
    
    class Meta:
        verbose_name = 'فروشگاه'
        verbose_name_plural = 'فروشگاه‌ها'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['subdomain']),
            models.Index(fields=['custom_domain']),
            models.Index(fields=['owner', 'is_active']),
            models.Index(fields=['is_active', 'is_verified']),
        ]
    
    def __str__(self):
        return self.name_fa or self.name
    
    @property
    def domain(self):
        """Get the primary domain for this store"""
        if self.custom_domain:
            return self.custom_domain
        return f"{self.subdomain}.mall.ir"
    
    def get_absolute_url(self):
        """Get the full URL for this store"""
        protocol = 'https' if not settings.DEBUG else 'http'
        return f"{protocol}://{self.domain}"


class Tenant(models.Model):
    """
    Tenant model for advanced multi-tenancy
    Maps to stores for schema-based isolation if needed
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    store = models.OneToOneField(Store, on_delete=models.CASCADE, related_name='tenant')
    schema_name = models.CharField(max_length=63, unique=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'مستاجر'
        verbose_name_plural = 'مستاجران'
    
    def __str__(self):
        return f"Tenant: {self.store.name}"


class PlatformSetting(models.Model):
    """
    Platform-wide settings
    """
    key = models.CharField(max_length=100, unique=True, verbose_name='کلید')
    value = models.TextField(verbose_name='مقدار')
    description = models.TextField(blank=True, verbose_name='توضیحات')
    is_public = models.BooleanField(default=False, verbose_name='عمومی')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'تنظیمات پلتفرم'
        verbose_name_plural = 'تنظیمات پلتفرم'
    
    def __str__(self):
        return self.key
    
    @classmethod
    def get_setting(cls, key, default=None):
        """Get a platform setting value"""
        try:
            setting = cls.objects.get(key=key)
            return setting.value
        except cls.DoesNotExist:
            return default
    
    @classmethod
    def set_setting(cls, key, value, description=''):
        """Set a platform setting value"""
        setting, created = cls.objects.get_or_create(
            key=key,
            defaults={'value': value, 'description': description}
        )
        if not created:
            setting.value = value
            setting.description = description
            setting.save()
        return setting
