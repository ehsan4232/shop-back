from django.db import models
from apps.core.mixins import StoreOwnedMixin, TimestampMixin
import uuid

class SocialMediaAccount(StoreOwnedMixin, TimestampMixin):
    """
    Store social media accounts
    """
    PLATFORM_CHOICES = [
        ('telegram', 'تلگرام'),
        ('instagram', 'اینستاگرام'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES, verbose_name='پلتفرم')
    username = models.CharField(max_length=100, verbose_name='نام کاربری')
    account_id = models.CharField(max_length=100, blank=True, verbose_name='شناسه حساب')
    access_token = models.TextField(blank=True, verbose_name='توکن دسترسی')
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    last_sync_at = models.DateTimeField(null=True, blank=True, verbose_name='آخرین هم‌سازی')
    
    class Meta:
        unique_together = ['store', 'platform', 'username']
        verbose_name = 'حساب شبکه اجتماعی'
        verbose_name_plural = 'حساب‌های شبکه اجتماعی'
    
    def __str__(self):
        return f"{self.get_platform_display()} - {self.username}"

class SocialMediaPost(TimestampMixin):
    """
    Imported social media posts
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    account = models.ForeignKey(SocialMediaAccount, on_delete=models.CASCADE, related_name='posts')
    external_id = models.CharField(max_length=100, verbose_name='شناسه خارجی')
    content = models.TextField(blank=True, verbose_name='محتوا')
    post_url = models.URLField(blank=True, verbose_name='لینک پست')
    published_at = models.DateTimeField(null=True, blank=True, verbose_name='تاریخ انتشار')
    media_files = models.JSONField(default=list, verbose_name='فایل‌های رسانه')
    is_processed = models.BooleanField(default=False, verbose_name='پردازش شده')
    raw_data = models.JSONField(default=dict, verbose_name='داده خام')
    
    class Meta:
        unique_together = ['account', 'external_id']
        ordering = ['-published_at']
        verbose_name = 'پست شبکه اجتماعی'
        verbose_name_plural = 'پست‌های شبکه اجتماعی'
    
    def __str__(self):
        return f"{self.account.username} - {self.external_id}"
