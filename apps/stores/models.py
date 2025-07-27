from django.db import models
from django.conf import settings
import uuid

class Store(models.Model):
    THEME_CHOICES = [
        ('modern', 'Modern'),
        ('classic', 'Classic'),
        ('minimal', 'Minimal'),
        ('colorful', 'Colorful'),
    ]
    
    LAYOUT_CHOICES = [
        ('grid', 'Grid Layout'),
        ('list', 'List Layout'),
        ('masonry', 'Masonry Layout'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    name_fa = models.CharField(max_length=100, verbose_name='نام فارسی')
    description = models.TextField(blank=True)
    description_fa = models.TextField(blank=True, verbose_name='توضیحات فارسی')
    logo = models.ImageField(upload_to='store_logos/', null=True, blank=True)
    banner = models.ImageField(upload_to='store_banners/', null=True, blank=True)
    theme = models.CharField(max_length=50, choices=THEME_CHOICES, default='modern')
    layout = models.CharField(max_length=50, choices=LAYOUT_CHOICES, default='grid')
    domain = models.CharField(max_length=255, unique=True, null=True, blank=True)
    subdomain = models.CharField(max_length=50, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Store settings
    currency = models.CharField(max_length=10, default='تومان')
    phone_number = models.CharField(max_length=15, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    instagram_username = models.CharField(max_length=100, blank=True)
    telegram_username = models.CharField(max_length=100, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name_fa or self.name
    
    @property
    def full_domain(self):
        if self.domain:
            return self.domain
        return f'{self.subdomain}.mall.ir'

class StoreSettings(models.Model):
    store = models.OneToOneField(Store, on_delete=models.CASCADE, related_name='settings')
    
    # SEO Settings
    meta_title = models.CharField(max_length=200, blank=True)
    meta_description = models.TextField(blank=True)
    meta_keywords = models.TextField(blank=True)
    
    # Analytics
    google_analytics_id = models.CharField(max_length=50, blank=True)
    
    # Social Media
    facebook_pixel = models.CharField(max_length=100, blank=True)
    
    # Payment Settings
    zarinpal_merchant_id = models.CharField(max_length=100, blank=True)
    
    # SMS Settings
    sms_welcome_template = models.TextField(blank=True)
    sms_order_confirmation_template = models.TextField(blank=True)
    
    def __str__(self):
        return f'Settings for {self.store.name_fa}'