from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
import uuid

class SocialMediaAccount(models.Model):
    """
    Social media account management for content import
    """
    PLATFORM_CHOICES = [
        ('telegram', 'تلگرام'),
        ('instagram', 'اینستاگرام'),
    ]
    
    store = models.ForeignKey('stores.Store', on_delete=models.CASCADE, related_name='social_accounts')
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES, verbose_name='پلتفرم')
    username = models.CharField(max_length=100, verbose_name='نام کاربری')
    account_id = models.CharField(max_length=100, blank=True, verbose_name='شناسه حساب')
    access_token = models.TextField(blank=True, verbose_name='توکن دسترسی')
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    last_sync = models.DateTimeField(null=True, blank=True, verbose_name='آخرین همگام‌سازی')
    
    # Configuration
    auto_import = models.BooleanField(default=False, verbose_name='واردات خودکار')
    import_hashtags = models.JSONField(default=list, verbose_name='هشتگ‌های واردات')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['store', 'platform', 'username']
        verbose_name = 'حساب شبکه اجتماعی'
        verbose_name_plural = 'حساب‌های شبکه‌های اجتماعی'
        indexes = [
            models.Index(fields=['store', 'platform']),
            models.Index(fields=['is_active', 'auto_import']),
        ]
    
    def __str__(self):
        return f'{self.store.name_fa} - {self.get_platform_display()}: @{self.username}'

class SocialMediaPost(models.Model):
    """
    Social media posts for import
    """
    POST_TYPES = [
        ('post', 'پست'),
        ('story', 'استوری'),
        ('reel', 'ریل'),
        ('photo', 'عکس'),
        ('video', 'ویدیو'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    account = models.ForeignKey(SocialMediaAccount, on_delete=models.CASCADE, related_name='posts')
    post_id = models.CharField(max_length=100, verbose_name='شناسه پست')
    post_type = models.CharField(max_length=20, choices=POST_TYPES, verbose_name='نوع پست')
    caption = models.TextField(blank=True, verbose_name='متن پست')
    media_urls = models.JSONField(default=list, verbose_name='لینک‌های رسانه')
    hashtags = models.JSONField(default=list, verbose_name='هشتگ‌ها')
    
    # Import status
    is_imported = models.BooleanField(default=False, verbose_name='وارد شده')
    imported_to_product = models.ForeignKey(
        'products.Product', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name='محصول وارد شده'
    )
    
    # Analytics
    likes_count = models.PositiveIntegerField(default=0, verbose_name='تعداد لایک')
    comments_count = models.PositiveIntegerField(default=0, verbose_name='تعداد کامنت')
    views_count = models.PositiveIntegerField(default=0, verbose_name='تعداد بازدید')
    
    posted_at = models.DateTimeField(verbose_name='تاریخ انتشار')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['account', 'post_id']
        ordering = ['-posted_at']
        verbose_name = 'پست شبکه اجتماعی'
        verbose_name_plural = 'پست‌های شبکه‌های اجتماعی'
        indexes = [
            models.Index(fields=['account', '-posted_at']),
            models.Index(fields=['is_imported']),
            models.Index(fields=['post_type']),
        ]
    
    def __str__(self):
        return f'{self.account.username} - {self.post_id}'
    
    @property
    def engagement_rate(self):
        """Calculate engagement rate"""
        if self.views_count > 0:
            return round(((self.likes_count + self.comments_count) / self.views_count) * 100, 2)
        return 0

class ImportSession(models.Model):
    """
    Social media import session tracking
    """
    STATUS_CHOICES = [
        ('pending', 'در انتظار'),
        ('processing', 'در حال پردازش'),
        ('completed', 'تکمیل شده'),
        ('failed', 'ناموفق'),
        ('cancelled', 'لغو شده'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store = models.ForeignKey('stores.Store', on_delete=models.CASCADE, related_name='import_sessions')
    account = models.ForeignKey(SocialMediaAccount, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Import statistics
    posts_found = models.PositiveIntegerField(default=0, verbose_name='پست‌های پیدا شده')
    posts_imported = models.PositiveIntegerField(default=0, verbose_name='پست‌های وارد شده')
    products_created = models.PositiveIntegerField(default=0, verbose_name='محصولات ایجاد شده')
    
    # Error handling
    error_message = models.TextField(blank=True, verbose_name='پیام خطا')
    error_count = models.PositiveIntegerField(default=0, verbose_name='تعداد خطا')
    
    # Configuration
    import_limit = models.PositiveIntegerField(default=50, verbose_name='حد واردات')
    import_media = models.BooleanField(default=True, verbose_name='واردات رسانه')
    create_products = models.BooleanField(default=False, verbose_name='ایجاد محصول')
    
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'جلسه واردات'
        verbose_name_plural = 'جلسات واردات'
        indexes = [
            models.Index(fields=['store', '-created_at']),
            models.Index(fields=['account', 'status']),
        ]
    
    def __str__(self):
        return f'واردات {self.account.username} - {self.created_at.strftime("%Y/%m/%d")}'
    
    @property
    def success_rate(self):
        """Calculate import success rate"""
        if self.posts_found > 0:
            return round((self.posts_imported / self.posts_found) * 100, 2)
        return 0
    
    @property
    def duration(self):
        """Calculate session duration"""
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        return None

class MediaDownload(models.Model):
    """
    Downloaded media files from social media
    """
    STATUS_CHOICES = [
        ('pending', 'در انتظار'),
        ('downloading', 'در حال دانلود'),
        ('completed', 'تکمیل شده'),
        ('failed', 'ناموفق'),
    ]
    
    MEDIA_TYPES = [
        ('image', 'تصویر'),
        ('video', 'ویدیو'),
        ('carousel', 'کاروسل'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    post = models.ForeignKey(SocialMediaPost, on_delete=models.CASCADE, related_name='downloads')
    original_url = models.URLField(verbose_name='لینک اصلی')
    local_file = models.FileField(upload_to='social_media/', null=True, blank=True, verbose_name='فایل محلی')
    media_type = models.CharField(max_length=20, choices=MEDIA_TYPES, verbose_name='نوع رسانه')
    file_size = models.PositiveIntegerField(null=True, blank=True, verbose_name='اندازه فایل (بایت)')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    error_message = models.TextField(blank=True, verbose_name='پیام خطا')
    
    # Metadata
    width = models.PositiveIntegerField(null=True, blank=True, verbose_name='عرض')
    height = models.PositiveIntegerField(null=True, blank=True, verbose_name='ارتفاع')
    duration = models.PositiveIntegerField(null=True, blank=True, verbose_name='مدت (ثانیه)')
    
    created_at = models.DateTimeField(auto_now_add=True)
    downloaded_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = 'دانلود رسانه'
        verbose_name_plural = 'دانلودهای رسانه'
        indexes = [
            models.Index(fields=['post', 'media_type']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f'{self.post.post_id} - {self.get_media_type_display()}'
    
    @property
    def file_size_mb(self):
        """Get file size in MB"""
        if self.file_size:
            return round(self.file_size / (1024 * 1024), 2)
        return 0

# Signal handlers for automatic processing
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=SocialMediaPost)
def process_new_post(sender, instance, created, **kwargs):
    """
    Process new social media posts
    """
    if created and instance.account.auto_import:
        # Check if post matches import criteria
        hashtags = instance.hashtags
        target_hashtags = instance.account.import_hashtags
        
        if not target_hashtags or any(tag in hashtags for tag in target_hashtags):
            # Create import session if needed
            session, created = ImportSession.objects.get_or_create(
                account=instance.account,
                status='pending',
                defaults={
                    'store': instance.account.store,
                    'posts_found': 1,
                }
            )
            if not created:
                session.posts_found += 1
                session.save()

@receiver(post_save, sender=ImportSession)
def update_import_statistics(sender, instance, **kwargs):
    """
    Update store statistics when import session completes
    """
    if instance.status == 'completed' and instance.products_created > 0:
        # Update store product count or other statistics as needed
        pass
