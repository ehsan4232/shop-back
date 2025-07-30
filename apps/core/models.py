"""Core models for Mall Platform - Support models only"""

from django.db import models
import uuid

class PlatformSetting(models.Model):
    """Platform-wide settings"""
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

# Note: Store model moved to apps.stores to eliminate duplication