"""
Core mixins for Mall platform
Provides reusable functionality across models
"""

from django.db import models
from django.core.cache import cache
from decimal import Decimal


class PriceInheritanceMixin(models.Model):
    """
    Mixin for models that support price inheritance
    Eliminates duplication in ProductClass and Product models
    """
    
    class Meta:
        abstract = True
    
    def get_effective_price(self):
        """
        Get effective price with proper inheritance chain
        Supports both parent-child and product-class inheritance
        """
        # Current object's price (direct override)
        if hasattr(self, 'base_price') and self.base_price:
            return self.base_price
        
        # Product class inheritance (for Product model)
        if hasattr(self, 'product_class') and self.product_class:
            return self.product_class.get_effective_price()
        
        # Parent class inheritance (for ProductClass model)
        if hasattr(self, 'parent') and self.parent:
            ancestors = self.get_ancestors() if hasattr(self, 'get_ancestors') else []
            for ancestor in ancestors:
                if ancestor.base_price:
                    return ancestor.base_price
        
        # Default price
        return Decimal('0.00')
    
    def cache_effective_price(self):
        """Cache the effective price for performance"""
        cache_key = f"effective_price_{self.__class__.__name__.lower()}_{self.id}"
        price = self.get_effective_price()
        cache.set(cache_key, price, timeout=300)  # 5 minutes
        return price
    
    def get_cached_effective_price(self):
        """Get cached effective price or calculate if not cached"""
        cache_key = f"effective_price_{self.__class__.__name__.lower()}_{self.id}"
        price = cache.get(cache_key)
        if price is None:
            price = self.cache_effective_price()
        return price


class TimestampMixin(models.Model):
    """
    Mixin for adding created_at and updated_at timestamps
    """
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاریخ به‌روزرسانی')
    
    class Meta:
        abstract = True


class SlugMixin(models.Model):
    """
    Mixin for models that need slug fields with Persian support
    """
    slug = models.SlugField(max_length=255, verbose_name='نامک')
    
    class Meta:
        abstract = True
    
    def save(self, *args, **kwargs):
        if not self.slug and hasattr(self, 'name_fa'):
            from django.utils.text import slugify
            # Use transliteration for Persian to Latin
            self.slug = slugify(self.name_fa) or f"item-{self.id or 'new'}"
        super().save(*args, **kwargs)


class SoftDeleteMixin(models.Model):
    """
    Mixin for soft delete functionality
    """
    is_deleted = models.BooleanField(default=False, verbose_name='حذف شده')
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name='تاریخ حذف')
    
    class Meta:
        abstract = True
    
    def soft_delete(self):
        """Soft delete the object"""
        from django.utils import timezone
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=['is_deleted', 'deleted_at'])
    
    def restore(self):
        """Restore soft deleted object"""
        self.is_deleted = False
        self.deleted_at = None
        self.save(update_fields=['is_deleted', 'deleted_at'])


class SEOMixin(models.Model):
    """
    Mixin for SEO-related fields
    """
    meta_title = models.CharField(max_length=200, blank=True, verbose_name='عنوان متا')
    meta_description = models.TextField(blank=True, verbose_name='توضیحات متا')
    meta_keywords = models.CharField(max_length=500, blank=True, verbose_name='کلمات کلیدی متا')
    
    class Meta:
        abstract = True
    
    def get_meta_title(self):
        """Get meta title or fallback to name"""
        if self.meta_title:
            return self.meta_title
        if hasattr(self, 'name_fa'):
            return self.name_fa
        if hasattr(self, 'name'):
            return self.name
        return ''
    
    def get_meta_description(self):
        """Get meta description or fallback to description"""
        if self.meta_description:
            return self.meta_description
        if hasattr(self, 'description'):
            return self.description[:160]  # Limit to 160 chars
        return ''


class ViewCountMixin(models.Model):
    """
    Mixin for tracking view counts with caching
    """
    view_count = models.PositiveIntegerField(default=0, verbose_name='تعداد بازدید')
    
    class Meta:
        abstract = True
    
    def increment_view_count(self, user_ip=None):
        """
        Increment view count with rate limiting by IP
        """
        if user_ip:
            cache_key = f"view_count_{self.__class__.__name__.lower()}_{self.id}_{user_ip}"
            if cache.get(cache_key):
                return  # Already counted from this IP recently
            cache.set(cache_key, True, timeout=3600)  # 1 hour cooldown
        
        # Use F() expression to avoid race conditions
        from django.db.models import F
        self.__class__.objects.filter(id=self.id).update(view_count=F('view_count') + 1)
        self.refresh_from_db(fields=['view_count'])


class AnalyticsMixin(models.Model):
    """
    Mixin for analytics tracking
    """
    analytics_data = models.JSONField(default=dict, blank=True, verbose_name='داده‌های تحلیلی')
    
    class Meta:
        abstract = True
    
    def track_event(self, event_type: str, data: dict = None):
        """Track an analytics event"""
        from django.utils import timezone
        
        if not self.analytics_data:
            self.analytics_data = {}
        
        if 'events' not in self.analytics_data:
            self.analytics_data['events'] = []
        
        event = {
            'type': event_type,
            'timestamp': timezone.now().isoformat(),
            'data': data or {}
        }
        
        # Keep only last 100 events to prevent bloat
        self.analytics_data['events'].append(event)
        if len(self.analytics_data['events']) > 100:
            self.analytics_data['events'] = self.analytics_data['events'][-100:]
        
        self.save(update_fields=['analytics_data'])


class StoreOwnedMixin(models.Model):
    """
    Mixin for models that belong to a store (multi-tenancy)
    """
    store = models.ForeignKey(
        'stores.Store', 
        on_delete=models.CASCADE, 
        verbose_name='فروشگاه'
    )
    
    class Meta:
        abstract = True
    
    def save(self, *args, **kwargs):
        # Auto-assign store from context if not set
        if not self.store_id and hasattr(self, '_current_store'):
            self.store = self._current_store
        super().save(*args, **kwargs)


class ValidationMixin:
    """
    Mixin for enhanced model validation
    """
    
    def full_clean(self, exclude=None, validate_unique=True):
        """Enhanced full_clean with custom validations"""
        super().full_clean(exclude=exclude, validate_unique=validate_unique)
        
        # Call custom validation method if exists
        if hasattr(self, 'custom_validate'):
            self.custom_validate()
    
    def clean(self):
        """Enhanced clean method"""
        super().clean() if hasattr(super(), 'clean') else None
        
        # Persian text validation
        if hasattr(self, 'name_fa') and self.name_fa:
            self.validate_persian_text(self.name_fa, 'name_fa')
    
    def validate_persian_text(self, text, field_name):
        """Validate Persian text content"""
        import re
        
        # Check for Persian characters
        persian_pattern = re.compile(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]')
        if not persian_pattern.search(text):
            from django.core.exceptions import ValidationError
            raise ValidationError({
                field_name: 'متن باید شامل حروف فارسی باشد'
            })
