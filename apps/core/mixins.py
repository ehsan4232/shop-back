"""
Fixed and enhanced core mixins for Mall Platform
Provides reusable model mixins for common functionality
"""

from django.db import models
from django.core.cache import cache
from django.utils.text import slugify
from django.utils import timezone
from django.contrib.auth import get_user_model
import uuid


class TimestampMixin(models.Model):
    """
    Mixin to add created_at and updated_at timestamps
    """
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاریخ بروزرسانی')
    
    class Meta:
        abstract = True


class StoreOwnedMixin(models.Model):
    """
    FIXED: Mixin for models that belong to a store (multi-tenant isolation)
    Corrected reference to use stores.Store instead of core.Store
    """
    store = models.ForeignKey(
        'stores.Store',  # FIXED: Correct reference to Store model
        on_delete=models.CASCADE,
        verbose_name='فروشگاه'
    )
    
    class Meta:
        abstract = True
    
    def save(self, *args, **kwargs):
        # Ensure store is set from request context if available
        if not self.store_id:
            # Try to get store from thread local or request context
            from django.core.exceptions import ValidationError
            raise ValidationError('فروشگاه باید مشخص شود')
        super().save(*args, **kwargs)


class SlugMixin(models.Model):
    """
    Mixin to add slug field with auto-generation
    """
    slug = models.SlugField(
        max_length=255, 
        blank=True,
        verbose_name='نامک'
    )
    
    class Meta:
        abstract = True
    
    def generate_slug(self):
        """Generate slug from name fields"""
        if hasattr(self, 'name_fa') and self.name_fa:
            base_slug = slugify(self.name_fa, allow_unicode=True)
        elif hasattr(self, 'name') and self.name:
            base_slug = slugify(self.name)
        elif hasattr(self, 'title_fa') and self.title_fa:
            base_slug = slugify(self.title_fa, allow_unicode=True)
        elif hasattr(self, 'title') and self.title:
            base_slug = slugify(self.title)
        else:
            base_slug = str(uuid.uuid4())[:8]
        
        return base_slug
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = self.generate_slug()
            slug = base_slug
            
            # Ensure uniqueness within store if applicable
            counter = 1
            while True:
                # Build queryset for uniqueness check
                qs = self.__class__.objects.filter(slug=slug)
                
                # Add store filter if this model has store
                if hasattr(self, 'store_id') and self.store_id:
                    qs = qs.filter(store_id=self.store_id)
                
                # Exclude self if updating
                if self.pk:
                    qs = qs.exclude(pk=self.pk)
                
                if not qs.exists():
                    break
                
                slug = f"{base_slug}-{counter}"
                counter += 1
            
            self.slug = slug
        
        super().save(*args, **kwargs)


class PriceInheritanceMixin(models.Model):
    """
    Mixin for price inheritance functionality
    """
    
    class Meta:
        abstract = True
    
    def get_effective_price(self):
        """
        Get effective price with inheritance logic
        Override this method in concrete models
        """
        if hasattr(self, 'base_price') and self.base_price:
            return self.base_price
        
        # Check for parent price if hierarchical
        if hasattr(self, 'parent') and self.parent:
            return self.parent.get_effective_price()
        
        return 0
    
    def get_price_inheritance_chain(self):
        """Get the chain of price inheritance"""
        chain = []
        current = self
        
        while current:
            if hasattr(current, 'base_price') and current.base_price:
                chain.append({
                    'model': current,
                    'price': current.base_price,
                    'source': 'direct'
                })
                break
            
            chain.append({
                'model': current,
                'price': None,
                'source': 'inherited'
            })
            
            # Move to parent if exists
            if hasattr(current, 'parent'):
                current = current.parent
            else:
                break
        
        return chain


class SEOMixin(models.Model):
    """
    Mixin for SEO-related fields
    """
    meta_title = models.CharField(
        max_length=70, 
        blank=True,
        verbose_name='عنوان متا'
    )
    meta_description = models.CharField(
        max_length=160, 
        blank=True,
        verbose_name='توضیحات متا'
    )
    meta_keywords = models.CharField(
        max_length=255, 
        blank=True,
        verbose_name='کلمات کلیدی'
    )
    
    class Meta:
        abstract = True
    
    def get_meta_title(self):
        """Get effective meta title"""
        if self.meta_title:
            return self.meta_title
        
        # Fallback to name fields
        if hasattr(self, 'name_fa') and self.name_fa:
            return self.name_fa
        elif hasattr(self, 'name') and self.name:
            return self.name
        elif hasattr(self, 'title_fa') and self.title_fa:
            return self.title_fa
        elif hasattr(self, 'title') and self.title:
            return self.title
        
        return ''
    
    def get_meta_description(self):
        """Get effective meta description"""
        if self.meta_description:
            return self.meta_description
        
        # Fallback to description or short description
        if hasattr(self, 'short_description') and self.short_description:
            return self.short_description
        elif hasattr(self, 'description') and self.description:
            # Truncate description to 160 chars
            return self.description[:157] + '...' if len(self.description) > 160 else self.description
        
        return ''


class ViewCountMixin(models.Model):
    """
    Mixin for tracking view counts
    """
    view_count = models.PositiveIntegerField(default=0, verbose_name='تعداد بازدید')
    
    class Meta:
        abstract = True
    
    def increment_view_count(self, increment=1):
        """Increment view count efficiently"""
        # Use F expression to avoid race conditions
        from django.db.models import F
        self.__class__.objects.filter(pk=self.pk).update(
            view_count=F('view_count') + increment
        )
        
        # Update the current instance
        self.view_count = F('view_count') + increment
    
    def get_view_count(self):
        """Get current view count"""
        # Refresh from database if using F expressions
        if isinstance(self.view_count, models.F):
            self.refresh_from_db(fields=['view_count'])
        return self.view_count


class AnalyticsMixin(models.Model):
    """
    Mixin for basic analytics tracking
    """
    total_views = models.PositiveIntegerField(default=0, verbose_name='کل بازدیدها')
    monthly_views = models.PositiveIntegerField(default=0, verbose_name='بازدید ماهانه')
    weekly_views = models.PositiveIntegerField(default=0, verbose_name='بازدید هفتگی')
    daily_views = models.PositiveIntegerField(default=0, verbose_name='بازدید روزانه')
    
    last_viewed_at = models.DateTimeField(null=True, blank=True, verbose_name='آخرین بازدید')
    
    class Meta:
        abstract = True
    
    def record_view(self):
        """Record a view and update analytics"""
        now = timezone.now()
        
        # Update view counts
        from django.db.models import F
        self.__class__.objects.filter(pk=self.pk).update(
            total_views=F('total_views') + 1,
            monthly_views=F('monthly_views') + 1,
            weekly_views=F('weekly_views') + 1,
            daily_views=F('daily_views') + 1,
            last_viewed_at=now
        )
        
        # Cache analytics for dashboard
        cache_key = f"analytics_{self.__class__.__name__.lower()}_{self.pk}"
        cache.delete(cache_key)  # Invalidate cache
    
    def reset_periodic_views(self, period='daily'):
        """Reset periodic view counts"""
        if period == 'daily':
            self.daily_views = 0
        elif period == 'weekly':
            self.weekly_views = 0
        elif period == 'monthly':
            self.monthly_views = 0
        
        self.save(update_fields=[f'{period}_views'])


class SoftDeleteMixin(models.Model):
    """
    Mixin for soft delete functionality
    """
    is_deleted = models.BooleanField(default=False, verbose_name='حذف شده')
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name='تاریخ حذف')
    deleted_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_deleted_items',
        verbose_name='حذف شده توسط'
    )
    
    class Meta:
        abstract = True
    
    def soft_delete(self, user=None):
        """Perform soft delete"""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        if user:
            self.deleted_by = user
        self.save(update_fields=['is_deleted', 'deleted_at', 'deleted_by'])
    
    def restore(self):
        """Restore soft deleted item"""
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by = None
        self.save(update_fields=['is_deleted', 'deleted_at', 'deleted_by'])
    
    @classmethod
    def active_objects(cls):
        """Get manager for non-deleted objects"""
        return cls.objects.filter(is_deleted=False)


class VersionMixin(models.Model):
    """
    Mixin for version tracking
    """
    version = models.PositiveIntegerField(default=1, verbose_name='نسخه')
    
    class Meta:
        abstract = True
    
    def save(self, *args, **kwargs):
        if self.pk:
            # Increment version on update
            self.version += 1
        super().save(*args, **kwargs)


class PublishMixin(models.Model):
    """
    Mixin for publishable content
    """
    STATUS_CHOICES = [
        ('draft', 'پیش‌نویس'),
        ('published', 'منتشر شده'),
        ('archived', 'بایگانی شده'),
    ]
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        verbose_name='وضعیت'
    )
    published_at = models.DateTimeField(null=True, blank=True, verbose_name='تاریخ انتشار')
    
    class Meta:
        abstract = True
    
    def publish(self):
        """Publish the content"""
        self.status = 'published'
        if not self.published_at:
            self.published_at = timezone.now()
        self.save(update_fields=['status', 'published_at'])
    
    def unpublish(self):
        """Unpublish the content"""
        self.status = 'draft'
        self.save(update_fields=['status'])
    
    def archive(self):
        """Archive the content"""
        self.status = 'archived'
        self.save(update_fields=['status'])
    
    @property
    def is_published(self):
        """Check if content is published"""
        return self.status == 'published'
    
    @classmethod
    def published_objects(cls):
        """Get manager for published objects"""
        return cls.objects.filter(status='published')


class CacheInvalidationMixin:
    """
    Mixin for automatic cache invalidation
    """
    
    def get_cache_keys(self):
        """Get list of cache keys to invalidate"""
        # Override in concrete models
        return []
    
    def invalidate_cache(self):
        """Invalidate related cache keys"""
        for key in self.get_cache_keys():
            cache.delete(key)
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.invalidate_cache()
    
    def delete(self, *args, **kwargs):
        self.invalidate_cache()
        super().delete(*args, **kwargs)
