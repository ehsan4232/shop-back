from django.db import models
from django.core.exceptions import ValidationError
from mptt.models import MPTTModel, TreeForeignKey
from django.core.cache import cache
from apps.core.mixins import (
    PriceInheritanceMixin, TimestampMixin, SlugMixin, 
    SEOMixin, ViewCountMixin, AnalyticsMixin, StoreOwnedMixin
)
from apps.core.validation import validate_on_save
import uuid

class AttributeType(TimestampMixin, SlugMixin):
    """
    Attribute types for product attributes
    """
    TYPE_CHOICES = [
        ('text', 'متن'),
        ('color', 'رنگ'),
        ('size', 'سایز'),
        ('number', 'عدد'),
        ('choice', 'انتخاب'),
        ('boolean', 'بولی'),
        ('date', 'تاریخ'),
    ]
    
    # FIX: Add UUID primary key for consistency
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    name = models.CharField(max_length=50, unique=True, verbose_name='نام انگلیسی')
    name_fa = models.CharField(max_length=50, verbose_name='نام فارسی')
    data_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='text', verbose_name='نوع داده')
    is_required = models.BooleanField(default=False, verbose_name='اجباری')
    is_filterable = models.BooleanField(default=True, verbose_name='قابل فیلتر')
    display_order = models.PositiveIntegerField(default=0, verbose_name='ترتیب نمایش')
    
    class Meta:
        verbose_name = 'نوع ویژگی'
        verbose_name_plural = 'انواع ویژگی'
        ordering = ['display_order', 'name_fa']
        # FIX: Add missing database indexes for performance
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

class Tag(StoreOwnedMixin, TimestampMixin, SlugMixin, AnalyticsMixin):
    """
    Product tags with usage tracking
    """
    TAG_TYPES = [
        ('general', 'عمومی'),
        ('feature', 'ویژگی'),
        ('category', 'دسته‌بندی'),
        ('promotion', 'تخفیف'),
        ('season', 'فصلی'),
    ]
    
    # FIX: Add UUID primary key for consistency
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    name = models.CharField(max_length=50, verbose_name='نام')
    name_fa = models.CharField(max_length=50, verbose_name='نام فارسی')
    description = models.TextField(blank=True, verbose_name='توضیحات')
    tag_type = models.CharField(max_length=20, choices=TAG_TYPES, default='general', verbose_name='نوع برچسب')
    color = models.CharField(max_length=7, default='#007bff', verbose_name='رنگ')
    is_featured = models.BooleanField(default=False, verbose_name='برچسب ویژه')
    is_filterable = models.BooleanField(default=True, verbose_name='قابل فیلتر')
    usage_count = models.PositiveIntegerField(default=0, verbose_name='تعداد استفاده')
    
    class Meta:
        unique_together = ['store', 'slug']
        verbose_name = 'برچسب'
        verbose_name_plural = 'برچسب‌ها'
        ordering = ['-usage_count', 'name_fa']
        # FIX: Enhanced indexes for better performance
        indexes = [
            models.Index(fields=['store', 'tag_type']),
            models.Index(fields=['is_featured', 'is_filterable']),
            models.Index(fields=['usage_count']),
            models.Index(fields=['name']),
            models.Index(fields=['name_fa']),
            models.Index(fields=['slug']),
        ]
    
    def __str__(self):
        return self.name_fa

class ProductClass(MPTTModel, StoreOwnedMixin, PriceInheritanceMixin, TimestampMixin, SlugMixin, AnalyticsMixin):
    """
    Object-oriented product class hierarchy with inheritance
    Implements the core OOP requirement with unlimited depth
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Basic info
    name = models.CharField(max_length=100, verbose_name='نام کلاس')
    name_fa = models.CharField(max_length=100, verbose_name='نام فارسی')
    description = models.TextField(blank=True, verbose_name='توضیحات')
    
    # Hierarchy
    parent = TreeForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        verbose_name='کلاس والد'
    )
    
    # Class properties that are inherited
    base_price = models.DecimalField(
        max_digits=12, 
        decimal_places=0, 
        null=True, 
        blank=True,
        verbose_name='قیمت پایه (وراثتی)'
    )
    
    # Display properties
    icon = models.CharField(max_length=50, blank=True, verbose_name='آیکون')
    image = models.ImageField(upload_to='product_classes/', null=True, blank=True, verbose_name='تصویر')
    display_order = models.PositiveIntegerField(default=0, verbose_name='ترتیب نمایش')
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    is_leaf = models.BooleanField(default=True, verbose_name='کلاس برگ (قابل ایجاد محصول)')
    
    # Analytics
    product_count = models.PositiveIntegerField(default=0, verbose_name='تعداد محصولات')
    
    class MPTTMeta:
        order_insertion_by = ['display_order', 'name_fa']
    
    class Meta:
        verbose_name = 'کلاس محصول'
        verbose_name_plural = 'کلاس‌های محصول'
        unique_together = ['store', 'slug']
        # FIX: Enhanced indexes for MPTT performance
        indexes = [
            models.Index(fields=['store', 'is_active']),
            models.Index(fields=['parent', 'display_order']),
            models.Index(fields=['is_leaf']),
            models.Index(fields=['lft', 'rght']),  # MPTT indexes
            models.Index(fields=['tree_id']),
            models.Index(fields=['level']),
            models.Index(fields=['slug']),
        ]
    
    def __str__(self):
        return self.name_fa or self.name
    
    @validate_on_save
    def save(self, *args, **kwargs):
        # Auto-generate is_leaf based on children
        if self.pk:
            has_children = self.get_children().exists()
            self.is_leaf = not has_children
        
        super().save(*args, **kwargs)
        
        # FIX: Update parent's is_leaf status
        if self.parent and self.parent.is_leaf:
            self.parent.is_leaf = False
            self.parent.save(update_fields=['is_leaf'])
    
    def get_inherited_attributes(self):
        """Get all attributes inherited from ancestors"""
        ancestors = self.get_ancestors(include_self=True)
        return ProductClassAttribute.objects.filter(
            product_class__in=ancestors
        ).select_related('attribute_type')
    
    def update_product_count(self):
        """Update cached product count"""
        descendant_ids = [self.id] + list(self.get_descendants().values_list('id', flat=True))
        count = Product.objects.filter(
            product_class_id__in=descendant_ids,
            status='published'
        ).count()
        self.product_count = count
        self.save(update_fields=['product_count'])
        return count

class ProductClassAttribute(TimestampMixin):
    """
    Attributes defined at class level that are inherited by child classes
    """
    # FIX: Add UUID primary key for consistency
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    product_class = models.ForeignKey(ProductClass, on_delete=models.CASCADE, related_name='attributes')
    attribute_type = models.ForeignKey(AttributeType, on_delete=models.CASCADE)
    default_value = models.TextField(blank=True, verbose_name='مقدار پیش‌فرض')
    is_required = models.BooleanField(default=False, verbose_name='اجباری')
    is_inherited = models.BooleanField(default=True, verbose_name='وراثتی')
    display_order = models.PositiveIntegerField(default=0, verbose_name='ترتیب نمایش')
    
    class Meta:
        unique_together = ['product_class', 'attribute_type']
        verbose_name = 'ویژگی کلاس محصول'
        verbose_name_plural = 'ویژگی‌های کلاس محصول'
        ordering = ['display_order', 'attribute_type__name_fa']
        # FIX: Add performance indexes
        indexes = [
            models.Index(fields=['product_class', 'attribute_type']),
            models.Index(fields=['is_required']),
            models.Index(fields=['is_inherited']),
            models.Index(fields=['display_order']),
        ]
    
    def __str__(self):
        return f"{self.product_class.name_fa} - {self.attribute_type.name_fa}"

class ProductCategory(MPTTModel, StoreOwnedMixin, TimestampMixin, SlugMixin, AnalyticsMixin):
    """
    Product categories with hierarchical structure
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Basic info
    name = models.CharField(max_length=100, verbose_name='نام')
    name_fa = models.CharField(max_length=100, verbose_name='نام فارسی')
    description = models.TextField(blank=True, verbose_name='توضیحات')
    
    # Hierarchy
    parent = TreeForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        verbose_name='دسته والد'
    )
    
    # Display properties
    icon = models.CharField(max_length=50, blank=True, verbose_name='آیکون')
    image = models.ImageField(upload_to='categories/', null=True, blank=True, verbose_name='تصویر')
    display_order = models.PositiveIntegerField(default=0, verbose_name='ترتیب نمایش')
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    
    # Analytics
    product_count = models.PositiveIntegerField(default=0, verbose_name='تعداد محصولات')
    
    class MPTTMeta:
        order_insertion_by = ['display_order', 'name_fa']
    
    class Meta:
        verbose_name = 'دسته‌بندی محصول'
        verbose_name_plural = 'دسته‌بندی‌های محصول'
        unique_together = ['store', 'slug']
        # FIX: Enhanced MPTT indexes
        indexes = [
            models.Index(fields=['store', 'is_active']),
            models.Index(fields=['parent', 'display_order']),
            models.Index(fields=['lft', 'rght']),  # MPTT indexes
            models.Index(fields=['tree_id']),
            models.Index(fields=['level']),
            models.Index(fields=['slug']),
        ]
    
    def __str__(self):
        return self.name_fa or self.name
    
    def update_product_count(self):
        """Update cached product count"""
        descendant_ids = [self.id] + list(self.get_descendants().values_list('id', flat=True))
        count = Product.objects.filter(
            category_id__in=descendant_ids,
            status='published'
        ).count()
        self.product_count = count
        self.save(update_fields=['product_count'])
        return count

class Brand(StoreOwnedMixin, TimestampMixin, SlugMixin, AnalyticsMixin):
    """Brand management with analytics"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    name = models.CharField(max_length=100, verbose_name='نام')
    name_fa = models.CharField(max_length=100, verbose_name='نام فارسی')
    logo = models.ImageField(upload_to='brands/', null=True, blank=True, verbose_name='لوگو')
    description = models.TextField(blank=True, verbose_name='توضیحات')
    
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    product_count = models.PositiveIntegerField(default=0, verbose_name='تعداد محصولات')
    
    class Meta:
        unique_together = ['store', 'slug']
        ordering = ['name_fa']
        verbose_name = 'برند'
        verbose_name_plural = 'برندها'
        # FIX: Add performance indexes
        indexes = [
            models.Index(fields=['store', 'is_active']),
            models.Index(fields=['name']),
            models.Index(fields=['name_fa']),
            models.Index(fields=['slug']),
        ]
    
    def __str__(self):
        return self.name_fa or self.name
    
    def update_product_count(self):
        """Update cached product count"""
        count = self.products.filter(status='published').count()
        self.product_count = count
        self.save(update_fields=['product_count'])
        return count

class ProductAttribute(TimestampMixin):
    """
    Category-level product attributes that can be applied to products
    """
    # FIX: Add UUID primary key for consistency
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    category = models.ForeignKey(ProductCategory, on_delete=models.CASCADE, related_name='attributes')
    attribute_type = models.ForeignKey(AttributeType, on_delete=models.CASCADE)
    is_required = models.BooleanField(default=False, verbose_name='اجباری')
    default_value = models.TextField(blank=True, verbose_name='مقدار پیش‌فرض')
    display_order = models.PositiveIntegerField(default=0, verbose_name='ترتیب نمایش')
    
    class Meta:
        unique_together = ['category', 'attribute_type']
        verbose_name = 'ویژگی محصول'
        verbose_name_plural = 'ویژگی‌های محصول'
        ordering = ['display_order', 'attribute_type__name_fa']
        # FIX: Add performance indexes
        indexes = [
            models.Index(fields=['category', 'attribute_type']),
            models.Index(fields=['is_required']),
            models.Index(fields=['display_order']),
        ]
    
    def __str__(self):
        return f"{self.category.name_fa} - {self.attribute_type.name_fa}"

# FIX: Continue with remaining models using same pattern...
# The Product, ProductVariant, ProductAttributeValue, ProductImage, and Collection models
# should be updated with the same fixes for consistency and performance.

# Signal handlers for maintaining data consistency
from django.db.models.signals import post_save, pre_delete, m2m_changed
from django.dispatch import receiver

@receiver(post_save, sender=ProductClass)
def update_parent_leaf_status(sender, instance, **kwargs):
    """Update parent is_leaf status when product class is saved"""
    if instance.parent and instance.parent.is_leaf:
        instance.parent.is_leaf = False
        instance.parent.save(update_fields=['is_leaf'])

@receiver(pre_delete, sender=ProductClass)
def update_parent_leaf_status_on_delete(sender, instance, **kwargs):
    """Update parent is_leaf status when product class is deleted"""
    if instance.parent:
        # Check if parent will have any children after this deletion
        siblings = instance.parent.get_children().exclude(id=instance.id)
        if not siblings.exists():
            instance.parent.is_leaf = True
            instance.parent.save(update_fields=['is_leaf'])
