from django.db import models
from django.utils.text import slugify
from django.conf import settings
import uuid

class Store(models.Model):
    """
    Simple store model focused on product requirements:
    - Store websites with independent domains/subdomains
    - Theme selection
    - Basic info for store management
    """
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
    slug = models.SlugField(max_length=100, verbose_name='نامک')
    description = models.TextField(blank=True, verbose_name='توضیحات')
    
    # Domain configuration (product requirement: "independent domain and address")
    custom_domain = models.CharField(
        max_length=255, 
        null=True, 
        blank=True,
        verbose_name='دامنه اختصاصی'
    )
    
    # Theme system (product requirement: "various fancy and modern designs and layouts and themes")
    theme = models.CharField(
        max_length=50, 
        default='modern',
        verbose_name='قالب'
    )
    layout = models.CharField(
        max_length=50, 
        default='grid',
        verbose_name='چیدمان',
        choices=[
            ('grid', 'شبکه‌ای'),
            ('list', 'لیستی'),
        ]
    )
    
    # Contact info
    phone = models.CharField(max_length=15, blank=True, verbose_name='تلفن')
    email = models.EmailField(blank=True, verbose_name='ایمیل')
    
    # Status
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    
    # Basic analytics cache (product requirement: "dashboards of charts and info")
    total_products = models.PositiveIntegerField(default=0)
    total_orders = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'فروشگاه'
        verbose_name_plural = 'فروشگاه‌ها'
        unique_together = ['owner', 'slug']
        indexes = [
            models.Index(fields=['owner']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        
        # Ensure unique slug for owner
        if not self.pk:
            original_slug = self.slug
            counter = 1
            while Store.objects.filter(owner=self.owner, slug=self.slug).exists():
                self.slug = f"{original_slug}-{counter}"
                counter += 1
        
        super().save(*args, **kwargs)
    
    @property
    def domain_url(self):
        """Get store domain (product requirement)"""
        if self.custom_domain:
            return self.custom_domain
        else:
            platform_domain = getattr(settings, 'PLATFORM_DOMAIN', 'mall.ir')
            return f"{self.slug}.{platform_domain}"
    
    @property
    def store_url(self):
        """Get full store URL"""
        protocol = 'https' if not settings.DEBUG else 'http'
        return f"{protocol}://{self.domain_url}"