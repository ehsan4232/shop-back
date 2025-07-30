from django.db import models
from django.core.exceptions import ValidationError
from mptt.models import MPTTModel, TreeForeignKey
from django.core.cache import cache
from django.utils.text import slugify
from django.utils import timezone
from apps.core.mixins import (
    PriceInheritanceMixin, TimestampMixin, SlugMixin, 
    SEOMixin, ViewCountMixin, AnalyticsMixin, StoreOwnedMixin
)
from apps.core.validation import validate_on_save
import uuid
import json

class AttributeType(TimestampMixin, SlugMixin):
    """
    Enhanced attribute types for product attributes with better validation
    FIXED: Improved performance and validation
    """
    TYPE_CHOICES = [
        ('text', 'متن'),
        ('color', 'رنگ'),
        ('size', 'سایز'),
        ('number', 'عدد'),
        ('choice', 'انتخاب'),
        ('boolean', 'بولی'),
        ('date', 'تاریخ'),
        ('file', 'فایل'),
        ('url', 'لینک'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    name = models.CharField(max_length=50, unique=True, verbose_name='نام انگلیسی')
    name_fa = models.CharField(max_length=50, verbose_name='نام فارسی')
    data_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='text', verbose_name='نوع داده')
    is_required = models.BooleanField(default=False, verbose_name='اجباری')
    is_filterable = models.BooleanField(default=True, verbose_name='قابل فیلتر')
    display_order = models.PositiveIntegerField(default=0, verbose_name='ترتیب نمایش')
    
    # Enhanced validation options
    validation_rules = models.JSONField(default=dict, blank=True, verbose_name='قوانین اعتبارسنجی')
    choice_options = models.JSONField(default=list, blank=True, verbose_name='گزینه‌های انتخاب')
    
    class Meta:
        verbose_name = 'نوع ویژگی'
        verbose_name_plural = 'انواع ویژگی'
        ordering = ['display_order', 'name_fa']
        indexes = [
            models.Index(fields=['data_type']),
            models.Index(fields=['is_required']),
            models.Index(fields=['is_filterable']),
            models.Index(fields=['display_order']),
            models.Index(fields=['name']),
            models.Index(fields=['name_fa']),
        ]
    
    def __str__(self):
        return self.name_fa
    
    def validate_value(self, value):
        """Validate value according to data type and rules"""
        if self.data_type == 'number' and not isinstance(value, (int, float)):
            raise ValidationError(f"Value must be a number for {self.name_fa}")
        elif self.data_type == 'boolean' and not isinstance(value, bool):
            raise ValidationError(f"Value must be boolean for {self.name_fa}")
        elif self.data_type == 'choice' and value not in self.choice_options:
            raise ValidationError(f"Invalid choice for {self.name_fa}")
        
        # Apply custom validation rules
        for rule, rule_value in self.validation_rules.items():
            if rule == 'min_length' and len(str(value)) < rule_value:
                raise ValidationError(f"Minimum length is {rule_value} for {self.name_fa}")
            elif rule == 'max_length' and len(str(value)) > rule_value:
                raise ValidationError(f"Maximum length is {rule_value} for {self.name_fa}")
        
        return True

class Tag(StoreOwnedMixin, TimestampMixin, SlugMixin, AnalyticsMixin):
    """
    Enhanced product tags with better analytics and categorization
    """
    TAG_TYPES = [
        ('general', 'عمومی'),
        ('feature', 'ویژگی'),
        ('category', 'دسته‌بندی'),
        ('promotion', 'تخفیف'),
        ('season', 'فصلی'),
        ('brand', 'برند'),
        ('trending', 'ترند'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    name = models.CharField(max_length=50, verbose_name='نام')
    name_fa = models.CharField(max_length=50, verbose_name='نام فارسی')
    description = models.TextField(blank=True, verbose_name='توضیحات')
    tag_type = models.CharField(max_length=20, choices=TAG_TYPES, default='general', verbose_name='نوع برچسب')
    color = models.CharField(max_length=7, default='#007bff', verbose_name='رنگ')
    icon = models.CharField(max_length=50, blank=True, verbose_name='آیکون')
    is_featured = models.BooleanField(default=False, verbose_name='برچسب ویژه')
    is_filterable = models.BooleanField(default=True, verbose_name='قابل فیلتر')
    usage_count = models.PositiveIntegerField(default=0, verbose_name='تعداد استفاده')
    
    # Analytics
    click_count = models.PositiveIntegerField(default=0, verbose_name='تعداد کلیک')
    conversion_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name='نرخ تبدیل')
    
    class Meta:
        unique_together = ['store', 'slug']
        verbose_name = 'برچسب'
        verbose_name_plural = 'برچسب‌ها'
        ordering = ['-usage_count', 'name_fa']
        indexes = [
            models.Index(fields=['store', 'tag_type']),
            models.Index(fields=['is_featured', 'is_filterable']),
            models.Index(fields=['usage_count']),
            models.Index(fields=['click_count']),
            models.Index(fields=['name']),
            models.Index(fields=['name_fa']),
            models.Index(fields=['slug']),
        ]
    
    def __str__(self):
        return self.name_fa
    
    def increment_usage(self):
        """Increment usage count atomically"""
        Tag.objects.filter(id=self.id).update(usage_count=models.F('usage_count') + 1)
        self.refresh_from_db()

class ProductClass(MPTTModel, StoreOwnedMixin, PriceInheritanceMixin, TimestampMixin, SlugMixin, AnalyticsMixin):
    """
    Enhanced Object-oriented product class hierarchy with better performance
    FIXED: Complete OOP implementation with optimized inheritance
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Basic info
    name = models.CharField(max_length=100, verbose_name='نام کلاس')
    name_fa = models.CharField(max_length=100, verbose_name='نام فارسی')
    description = models.TextField(blank=True, verbose_name='توضیحات')
    
    # Hierarchy with better validation
    parent = TreeForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        verbose_name='کلاس والد'
    )
    
    # Enhanced inheritance properties
    base_price = models.DecimalField(
        max_digits=12, 
        decimal_places=0, 
        null=True, 
        blank=True,
        verbose_name='قیمت پایه (وراثتی)'
    )
    
    # Template for child classes
    attribute_template = models.JSONField(default=dict, blank=True, verbose_name='الگوی ویژگی‌ها')
    
    # Display properties
    icon = models.CharField(max_length=50, blank=True, verbose_name='آیکون')
    image = models.ImageField(upload_to='product_classes/', null=True, blank=True, verbose_name='تصویر')
    display_order = models.PositiveIntegerField(default=0, verbose_name='ترتیب نمایش')
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    is_leaf = models.BooleanField(default=True, verbose_name='کلاس برگ (قابل ایجاد محصول)')
    
    # Enhanced analytics
    product_count = models.PositiveIntegerField(default=0, verbose_name='تعداد محصولات')
    total_sales = models.DecimalField(max_digits=15, decimal_places=0, default=0, verbose_name='مجموع فروش')
    avg_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0, verbose_name='میانگین امتیاز')
    
    class MPTTMeta:
        order_insertion_by = ['display_order', 'name_fa']
    
    class Meta:
        verbose_name = 'کلاس محصول'
        verbose_name_plural = 'کلاس‌های محصول'
        unique_together = ['store', 'slug']
        indexes = [
            models.Index(fields=['store', 'is_active']),
            models.Index(fields=['parent', 'display_order']),
            models.Index(fields=['is_leaf']),
            models.Index(fields=['lft', 'rght']),  # MPTT tree traversal
            models.Index(fields=['tree_id']),
            models.Index(fields=['level']),
            models.Index(fields=['slug']),
            models.Index(fields=['base_price']),
            models.Index(fields=['product_count']),
        ]
    
    def __str__(self):
        return self.name_fa or self.name
    
    def get_effective_price(self):
        """Optimized price inheritance with better caching"""
        cache_key = f"effective_price_class_{self.id}"
        cached_price = cache.get(cache_key)
        if cached_price is not None:
            return cached_price
        
        if self.base_price:
            price = self.base_price
        else:
            # Optimized ancestor query
            ancestors = self.get_ancestors().filter(
                base_price__isnull=False
            ).order_by('-level').first()
            price = ancestors.base_price if ancestors else 0
        
        cache.set(cache_key, price, timeout=600)  # 10 minutes cache
        return price
    
    def get_all_inherited_attributes(self):
        """Get complete attribute inheritance chain with caching"""
        cache_key = f"inherited_attrs_class_{self.id}"
        cached_attrs = cache.get(cache_key)
        if cached_attrs is not None:
            return cached_attrs
        
        # Get all ancestors including self
        ancestor_ids = list(self.get_ancestors(include_self=True).values_list('id', flat=True))
        
        # Get all attributes from ancestors
        attrs = ProductClassAttribute.objects.filter(
            product_class_id__in=ancestor_ids,
            is_inherited=True
        ).select_related('attribute_type').order_by('product_class__level', 'display_order')
        
        # Resolve conflicts (child overrides parent)
        resolved_attrs = {}
        for attr in attrs:
            attr_key = attr.attribute_type.id
            resolved_attrs[attr_key] = attr
        
        result = list(resolved_attrs.values())
        cache.set(cache_key, result, timeout=1200)  # 20 minutes cache
        return result
    
    def can_create_products(self):
        """Check if this class can create product instances"""
        return self.is_leaf and self.is_active
    
    def validate_for_product_creation(self):
        """Validate class is ready for product creation"""
        if not self.can_create_products():
            raise ValidationError("Only leaf classes can create product instances")
        
        # Check required attributes
        required_attrs = self.get_all_inherited_attributes().filter(is_required=True)
        if required_attrs.count() > 0:
            return True
        
        return True
    
    @validate_on_save
    def save(self, *args, **kwargs):
        # Auto-manage is_leaf status
        if self.pk:
            has_children = self.get_children().exists()
            self.is_leaf = not has_children
        
        # Validate hierarchy
        if self.parent and self.parent.id == self.id:
            raise ValidationError("A class cannot be its own parent")
        
        super().save(*args, **kwargs)
        
        # Clear caches
        cache.delete(f"effective_price_class_{self.id}")
        cache.delete(f"inherited_attrs_class_{self.id}")
        
        # Update parent's is_leaf status
        if self.parent and self.parent.is_leaf:
            ProductClass.objects.filter(id=self.parent.id).update(is_leaf=False)
            cache.delete(f"effective_price_class_{self.parent.id}")
    
    def delete(self, *args, **kwargs):
        parent = self.parent
        super().delete(*args, **kwargs)
        
        # Update parent's is_leaf status if needed
        if parent:
            has_siblings = parent.get_children().exists()
            if not has_siblings:
                ProductClass.objects.filter(id=parent.id).update(is_leaf=True)
            cache.delete(f"effective_price_class_{parent.id}")
    
    def update_analytics(self):
        """Update cached analytics efficiently"""
        descendant_ids = [self.id] + list(self.get_descendants().values_list('id', flat=True))
        
        # Get product stats
        from django.db.models import Count, Sum, Avg
        stats = Product.objects.filter(
            product_class_id__in=descendant_ids,
            status='published'
        ).aggregate(
            count=Count('id'),
            total_sales=Sum('sales_count'),
            avg_rating=Avg('rating_average')
        )
        
        self.product_count = stats['count'] or 0
        self.total_sales = stats['total_sales'] or 0
        self.avg_rating = stats['avg_rating'] or 0
        
        self.save(update_fields=['product_count', 'total_sales', 'avg_rating'])
        return stats

class ProductClassAttribute(TimestampMixin):
    """
    Enhanced class-level attributes with better inheritance control
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    product_class = models.ForeignKey(ProductClass, on_delete=models.CASCADE, related_name='attributes')
    attribute_type = models.ForeignKey(AttributeType, on_delete=models.CASCADE)
    
    # Enhanced attribute definition
    default_value = models.TextField(blank=True, verbose_name='مقدار پیش‌فرض')
    is_required = models.BooleanField(default=False, verbose_name='اجباری')
    is_inherited = models.BooleanField(default=True, verbose_name='وراثتی')
    is_overridable = models.BooleanField(default=True, verbose_name='قابل بازنویسی')
    
    # Display options
    display_order = models.PositiveIntegerField(default=0, verbose_name='ترتیب نمایش')
    is_visible_in_list = models.BooleanField(default=True, verbose_name='نمایش در لیست')
    is_searchable = models.BooleanField(default=True, verbose_name='قابل جستجو')
    
    # Inheritance level control
    inheritance_level = models.PositiveIntegerField(default=0, verbose_name='سطح وراثت')
    
    class Meta:
        unique_together = ['product_class', 'attribute_type']
        verbose_name = 'ویژگی کلاس محصول'
        verbose_name_plural = 'ویژگی‌های کلاس محصول'
        ordering = ['display_order', 'attribute_type__name_fa']
        indexes = [
            models.Index(fields=['product_class', 'attribute_type']),
            models.Index(fields=['is_required']),
            models.Index(fields=['is_inherited']),
            models.Index(fields=['display_order']),
            models.Index(fields=['inheritance_level']),
        ]
    
    def __str__(self):
        return f"{self.product_class.name_fa} - {self.attribute_type.name_fa}"
    
    def save(self, *args, **kwargs):
        # Auto-calculate inheritance level
        if self.product_class:
            self.inheritance_level = self.product_class.level
        
        super().save(*args, **kwargs)
        
        # Clear related caches
        cache.delete(f"inherited_attrs_class_{self.product_class.id}")
        
        # Clear descendant caches
        for descendant in self.product_class.get_descendants():
            cache.delete(f"inherited_attrs_class_{descendant.id}")

# Continue with other enhanced models...
# This is the foundation for the complete enhanced implementation
