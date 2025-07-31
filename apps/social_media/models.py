from django.db import models
from django.core.exceptions import ValidationError
from apps.core.mixins import TimestampMixin, StoreOwnedMixin
import uuid
import json


class SocialMediaAccount(StoreOwnedMixin, TimestampMixin):
    """
    Social media account integration for stores
    Product requirement: "Get from social media" functionality
    """
    
    PLATFORM_CHOICES = [
        ('telegram', 'تلگرام'),
        ('instagram', 'اینستاگرام'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES, verbose_name='پلتفرم')
    username = models.CharField(max_length=100, verbose_name='نام کاربری')
    display_name = models.CharField(max_length=100, blank=True, verbose_name='نام نمایشی')
    
    # Authentication tokens (encrypted in production)
    access_token = models.TextField(blank=True, verbose_name='توکن دسترسی')
    refresh_token = models.TextField(blank=True, verbose_name='توکن تازه‌سازی')
    token_expires_at = models.DateTimeField(null=True, blank=True, verbose_name='انقضای توکن')
    
    # Account info
    followers_count = models.PositiveIntegerField(default=0, verbose_name='تعداد دنبال‌کنندگان')
    posts_count = models.PositiveIntegerField(default=0, verbose_name='تعداد پست‌ها')
    
    # Sync settings
    auto_import_enabled = models.BooleanField(default=False, verbose_name='وارد کردن خودکار')
    import_images = models.BooleanField(default=True, verbose_name='وارد کردن تصاویر')
    import_videos = models.BooleanField(default=False, verbose_name='وارد کردن ویدیوها')
    import_captions = models.BooleanField(default=True, verbose_name='وارد کردن متن‌ها')
    
    # Status
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    is_verified = models.BooleanField(default=False, verbose_name='تأیید شده')
    last_sync_at = models.DateTimeField(null=True, blank=True, verbose_name='آخرین همگام‌سازی')
    last_error = models.TextField(blank=True, verbose_name='آخرین خطا')
    
    class Meta:
        unique_together = ['store', 'platform', 'username']
        verbose_name = 'حساب شبکه اجتماعی'
        verbose_name_plural = 'حساب‌های شبکه اجتماعی'
        indexes = [
            models.Index(fields=['store', 'platform']),
            models.Index(fields=['username', 'platform']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.get_platform_display()} - @{self.username}"
    
    def clean(self):
        super().clean()
        if self.username:
            self.username = self.username.lstrip('@').lower()


class SocialMediaPost(StoreOwnedMixin, TimestampMixin):
    """
    Imported social media posts for product creation
    Product requirement: "gets 5 last posts and stories"
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    account = models.ForeignKey(
        SocialMediaAccount, 
        on_delete=models.CASCADE,
        related_name='posts',
        verbose_name='حساب'
    )
    
    # Post identification
    external_id = models.CharField(max_length=100, verbose_name='شناسه خارجی')
    post_type = models.CharField(
        max_length=20,
        choices=[
            ('post', 'پست'),
            ('story', 'استوری'),
            ('reel', 'ریل'),
            ('video', 'ویدیو'),
        ],
        default='post',
        verbose_name='نوع پست'
    )
    
    # Content
    caption = models.TextField(blank=True, verbose_name='متن پست')
    hashtags = models.JSONField(default=list, blank=True, verbose_name='هشتگ‌ها')
    mentions = models.JSONField(default=list, blank=True, verbose_name='منشن‌ها')
    
    # Media files
    media_files = models.JSONField(default=list, blank=True, verbose_name='فایل‌های رسانه')
    # Format: [{'type': 'image|video', 'url': 'https://...', 'local_path': '/media/...'}]
    
    # Engagement metrics
    likes_count = models.PositiveIntegerField(default=0, verbose_name='تعداد لایک')
    comments_count = models.PositiveIntegerField(default=0, verbose_name='تعداد کامنت')
    views_count = models.PositiveIntegerField(default=0, verbose_name='تعداد بازدید')
    
    # Post metadata
    post_url = models.URLField(blank=True, verbose_name='لینک پست')
    published_at = models.DateTimeField(verbose_name='تاریخ انتشار')
    
    # Import status
    is_processed = models.BooleanField(default=False, verbose_name='پردازش شده')
    is_imported = models.BooleanField(default=False, verbose_name='وارد شده')
    imported_at = models.DateTimeField(null=True, blank=True, verbose_name='تاریخ وارد کردن')
    
    # Product creation
    created_product = models.OneToOneField(
        'products.Product',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='source_post',
        verbose_name='محصول ایجاد شده'
    )
    
    # Raw data from API
    raw_data = models.JSONField(default=dict, blank=True, verbose_name='داده‌های خام')
    
    class Meta:
        unique_together = ['account', 'external_id']
        ordering = ['-published_at']
        verbose_name = 'پست شبکه اجتماعی'
        verbose_name_plural = 'پست‌های شبکه اجتماعی'
        indexes = [
            models.Index(fields=['store', 'account']),
            models.Index(fields=['external_id']),
            models.Index(fields=['is_processed', 'is_imported']),
            models.Index(fields=['-published_at']),
            models.Index(fields=['post_type']),
        ]
    
    def __str__(self):
        return f"{self.account.username} - {self.external_id}"
    
    def extract_suggested_product_info(self):
        """
        Extract suggested product information from post content
        Product requirement: AI-like suggestion for product creation
        """
        import re
        
        suggestions = {
            'name': '',
            'description': '',
            'price': None,
            'hashtags': self.hashtags,
            'images': [],
            'videos': []
        }
        
        # Extract name from caption (first line or first sentence)
        if self.caption:
            lines = self.caption.split('\n')
            if lines:
                suggestions['name'] = lines[0][:100]  # First line as name
                suggestions['description'] = self.caption
        
        # Extract price from caption using Persian and Arabic numerals
        price_patterns = [
            r'(\d+)\s*تومان',
            r'(\d+)\s*ریال',
            r'قیمت[:\s]*(\d+)',
            r'price[:\s]*(\d+)',
        ]
        
        for pattern in price_patterns:
            match = re.search(pattern, self.caption, re.IGNORECASE)
            if match:
                try:
                    suggestions['price'] = int(match.group(1))
                    break
                except ValueError:
                    continue
        
        # Categorize media files
        for media in self.media_files:
            if media.get('type') == 'image':
                suggestions['images'].append(media)
            elif media.get('type') == 'video':
                suggestions['videos'].append(media)
        
        return suggestions
    
    def create_product_from_post(self, product_class, category, additional_data=None):
        """
        Create a product from this social media post
        Product requirement: Convert social media content to product
        """
        from apps.products.models import Product
        
        if self.created_product:
            return self.created_product
        
        suggestions = self.extract_suggested_product_info()
        
        # Create product
        product_data = {
            'store': self.store,
            'product_class': product_class,
            'category': category,
            'name': suggestions['name'] or f"محصول از {self.account.username}",
            'name_fa': suggestions['name'] or f"محصول از {self.account.username}",
            'description': suggestions['description'] or self.caption,
            'short_description': self.caption[:200] if self.caption else '',
            'base_price': suggestions['price'],
            'status': 'draft',  # Start as draft for review
            'imported_from_social': True,
            'social_media_source': self.account.platform,
            'social_media_post_id': self.external_id,
            'social_media_data': {
                'post_url': self.post_url,
                'likes_count': self.likes_count,
                'comments_count': self.comments_count,
                'hashtags': self.hashtags,
                'original_caption': self.caption,
            }
        }
        
        # Apply additional data if provided
        if additional_data:
            product_data.update(additional_data)
        
        product = Product.objects.create(**product_data)
        
        # Import media files as product images
        self._import_media_to_product(product)
        
        # Mark as imported
        self.created_product = product
        self.is_imported = True
        from django.utils import timezone
        self.imported_at = timezone.now()
        self.save(update_fields=['created_product', 'is_imported', 'imported_at'])
        
        return product
    
    def _import_media_to_product(self, product):
        """Import media files as product images"""
        from apps.products.models import ProductImage
        
        for i, media in enumerate(self.media_files):
            if media.get('type') == 'image' and media.get('local_path'):
                ProductImage.objects.create(
                    product=product,
                    image=media['local_path'],
                    alt_text=f"تصویر وارد شده از {self.account.get_platform_display()}",
                    is_featured=(i == 0),  # First image as featured
                    display_order=i,
                    imported_from_social=True,
                    social_media_url=media.get('url')
                )


class SocialMediaImportJob(StoreOwnedMixin, TimestampMixin):
    """
    Background job for importing social media content
    """
    
    STATUS_CHOICES = [
        ('pending', 'در انتظار'),
        ('running', 'در حال اجرا'),
        ('completed', 'تکمیل شده'),
        ('failed', 'ناموفق'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    account = models.ForeignKey(
        SocialMediaAccount,
        on_delete=models.CASCADE,
        related_name='import_jobs'
    )
    
    job_type = models.CharField(
        max_length=20,
        choices=[
            ('posts', 'پست‌ها'),
            ('stories', 'استوری‌ها'),
            ('both', 'هر دو'),
        ],
        default='posts'
    )
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Configuration
    max_items = models.PositiveIntegerField(default=5, verbose_name='حداکثر تعداد')
    since_date = models.DateTimeField(null=True, blank=True, verbose_name='از تاریخ')
    
    # Results
    total_found = models.PositiveIntegerField(default=0, verbose_name='تعداد یافت شده')
    total_imported = models.PositiveIntegerField(default=0, verbose_name='تعداد وارد شده')
    total_skipped = models.PositiveIntegerField(default=0, verbose_name='تعداد رد شده')
    
    # Progress tracking
    progress_percentage = models.PositiveIntegerField(default=0, verbose_name='درصد پیشرفت')
    current_step = models.CharField(max_length=100, blank=True, verbose_name='مرحله فعلی')
    
    # Error handling
    error_message = models.TextField(blank=True, verbose_name='پیام خطا')
    error_details = models.JSONField(default=dict, blank=True, verbose_name='جزئیات خطا')
    
    # Completion
    started_at = models.DateTimeField(null=True, blank=True, verbose_name='شروع در')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='تکمیل در')
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'کار وارد کردن شبکه اجتماعی'
        verbose_name_plural = 'کارهای وارد کردن شبکه اجتماعی'
        indexes = [
            models.Index(fields=['store', 'status']),
            models.Index(fields=['account', '-created_at']),
        ]
    
    def __str__(self):
        return f"وارد کردن {self.get_job_type_display()} از {self.account.username}"


# Signal handlers for social media integration
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=SocialMediaPost)
def auto_process_post(sender, instance, created, **kwargs):
    """Auto-process new social media posts if enabled"""
    if created and instance.account.auto_import_enabled:
        # Queue background job for processing
        from apps.social_media.tasks import process_social_media_post
        process_social_media_post.delay(instance.id)
