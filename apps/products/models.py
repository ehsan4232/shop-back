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
        indexes = [
            models.Index(fields=['store', 'tag_type']),
            models.Index(fields=['is_featured', 'is_filterable']),
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
        indexes = [
            models.Index(fields=['store', 'is_active']),
            models.Index(fields=['parent', 'display_order']),
            models.Index(fields=['is_leaf']),
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
        indexes = [
            models.Index(fields=['store', 'is_active']),
            models.Index(fields=['parent', 'display_order']),
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
        indexes = [
            models.Index(fields=['store', 'is_active']),
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
    
    def __str__(self):
        return f"{self.category.name_fa} - {self.attribute_type.name_fa}"

class Product(StoreOwnedMixin, PriceInheritanceMixin, TimestampMixin, SlugMixin, SEOMixin, ViewCountMixin, AnalyticsMixin):
    """
    Enhanced product model with object-oriented class support and comprehensive features
    """
    STATUS_CHOICES = [
        ('draft', 'پیش‌نویس'),
        ('published', 'منتشر شده'),
        ('archived', 'بایگانی شده'),
        ('out_of_stock', 'ناموجود'),
    ]
    
    PRODUCT_TYPES = [
        ('simple', 'ساده'),
        ('variable', 'متغیر'),
        ('grouped', 'گروهی'),
        ('external', 'خارجی'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product_class = models.ForeignKey(ProductClass, on_delete=models.CASCADE, related_name='products', verbose_name='کلاس محصول')
    category = models.ForeignKey(ProductCategory, on_delete=models.CASCADE, related_name='products')
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    tags = models.ManyToManyField(Tag, blank=True, related_name='products', verbose_name='برچسب‌ها')
    
    # Basic information
    name = models.CharField(max_length=200, verbose_name='نام')
    name_fa = models.CharField(max_length=200, verbose_name='نام فارسی')
    description = models.TextField(blank=True, verbose_name='توضیحات')
    short_description = models.CharField(max_length=500, blank=True, verbose_name='توضیحات کوتاه')
    
    # Product type and structure
    product_type = models.CharField(max_length=20, choices=PRODUCT_TYPES, default='simple', verbose_name='نوع محصول')
    
    # Pricing (inherits from class if not set)
    base_price = models.DecimalField(
        max_digits=12, 
        decimal_places=0, 
        null=True,
        blank=True,
        verbose_name='قیمت پایه (تومان)'
    )
    compare_price = models.DecimalField(
        max_digits=12, 
        decimal_places=0, 
        null=True, 
        blank=True,
        verbose_name='قیمت قبل از تخفیف'
    )
    cost_price = models.DecimalField(
        max_digits=12, 
        decimal_places=0, 
        null=True, 
        blank=True,
        verbose_name='قیمت تمام شده'
    )
    
    # Inventory
    sku = models.CharField(max_length=100, null=True, blank=True, verbose_name='کد محصول')
    stock_quantity = models.PositiveIntegerField(default=0, verbose_name='موجودی انبار')
    manage_stock = models.BooleanField(default=True, verbose_name='مدیریت موجودی')
    low_stock_threshold = models.PositiveIntegerField(default=5, verbose_name='حد هشدار موجودی')
    
    # Media
    featured_image = models.ImageField(upload_to='products/', null=True, blank=True, verbose_name='تصویر اصلی')
    
    # Physical properties
    weight = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name='وزن (گرم)')
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', verbose_name='وضعیت')
    is_featured = models.BooleanField(default=False, verbose_name='محصول ویژه')
    
    # Additional analytics (beyond ViewCountMixin)
    sales_count = models.PositiveIntegerField(default=0, verbose_name='تعداد فروش')
    rating_average = models.DecimalField(max_digits=3, decimal_places=2, default=0, verbose_name='میانگین امتیاز')
    rating_count = models.PositiveIntegerField(default=0, verbose_name='تعداد امتیاز')
    
    # Social media integration
    imported_from_social = models.BooleanField(default=False, verbose_name='وارد شده از شبکه اجتماعی')
    social_media_source = models.CharField(
        max_length=20, 
        choices=[('telegram', 'تلگرام'), ('instagram', 'اینستاگرام')],
        null=True, 
        blank=True,
        verbose_name='منبع شبکه اجتماعی'
    )
    social_media_post_id = models.CharField(max_length=100, null=True, blank=True, verbose_name='شناسه پست')
    
    # Timestamps (from TimestampMixin, but need to override for published_at)
    published_at = models.DateTimeField(null=True, blank=True, verbose_name='تاریخ انتشار')
    
    class Meta:
        unique_together = ['store', 'slug']
        ordering = ['-created_at']
        verbose_name = 'محصول'
        verbose_name_plural = 'محصولات'
        indexes = [
            models.Index(fields=['store', 'status', '-created_at']),
            models.Index(fields=['product_class', 'status']),
            models.Index(fields=['category', 'status']),
            models.Index(fields=['brand', 'status']),
            models.Index(fields=['status', 'is_featured']),
            models.Index(fields=['base_price']),
            models.Index(fields=['sku']),
            models.Index(fields=['-view_count']),
            models.Index(fields=['-sales_count']),
            models.Index(fields=['-rating_average']),
        ]
    
    def __str__(self):
        return self.name_fa or self.name
    
    @validate_on_save
    def save(self, *args, **kwargs):
        # Auto-generate SKU if not provided
        if not self.sku:
            self.sku = f"P{uuid.uuid4().hex[:8].upper()}"
        
        # Set published date on first publish
        if self.status == 'published' and not self.published_at:
            from django.utils import timezone
            self.published_at = timezone.now()
        
        super().save(*args, **kwargs)
    
    def get_inherited_attributes(self):
        """Get all attributes inherited from product class"""
        return self.product_class.get_inherited_attributes()
    
    @property
    def price(self):
        """Computed property for final price"""
        return self.get_effective_price()
    
    @property
    def in_stock(self):
        """Check if product is in stock"""
        if self.product_type == 'simple':
            return self.stock_quantity > 0
        elif self.product_type == 'variable':
            return self.variants.filter(stock_quantity__gt=0).exists()
        return True
    
    @property
    def discount_percentage(self):
        """Calculate discount percentage"""
        if self.compare_price and self.compare_price > self.price:
            return round(((self.compare_price - self.price) / self.compare_price) * 100)
        return 0
    
    @property
    def is_low_stock(self):
        """Check if product is low in stock"""
        if self.product_type == 'simple':
            return self.stock_quantity <= self.low_stock_threshold
        elif self.product_type == 'variable':
            return all(
                variant.stock_quantity <= self.low_stock_threshold 
                for variant in self.variants.all()
            )
        return False
    
    def increment_sales_count(self, quantity=1):
        """Increment sales count"""
        self.sales_count += quantity
        self.save(update_fields=['sales_count'])

class ProductAttributeValue(TimestampMixin):
    """
    Attribute values for products and variants with multi-type support
    """
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True, blank=True, related_name='attribute_values')
    variant = models.ForeignKey('ProductVariant', on_delete=models.CASCADE, null=True, blank=True, related_name='attribute_values')
    attribute = models.ForeignKey(ProductAttribute, on_delete=models.CASCADE)
    
    # Different value types
    value_text = models.TextField(blank=True, verbose_name='مقدار متنی')
    value_number = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='مقدار عددی')
    value_boolean = models.BooleanField(null=True, blank=True, verbose_name='مقدار بولی')
    value_date = models.DateField(null=True, blank=True, verbose_name='مقدار تاریخ')
    
    class Meta:
        verbose_name = 'مقدار ویژگی محصول'
        verbose_name_plural = 'مقادیر ویژگی محصول'
        unique_together = [
            ['product', 'attribute'],
            ['variant', 'attribute']
        ]
        indexes = [
            models.Index(fields=['product', 'attribute']),
            models.Index(fields=['variant', 'attribute']),
        ]
    
    def __str__(self):
        target = self.product or self.variant
        return f"{target} - {self.attribute.attribute_type.name_fa}: {self.get_value()}"
    
    def get_value(self):
        """Get the appropriate value based on attribute type"""
        if self.attribute.attribute_type.data_type == 'number':
            return self.value_number
        elif self.attribute.attribute_type.data_type == 'boolean':
            return self.value_boolean
        elif self.attribute.attribute_type.data_type == 'date':
            return self.value_date
        else:
            return self.value_text
    
    def set_value(self, value):
        """Set the appropriate value based on attribute type"""
        if self.attribute.attribute_type.data_type == 'number':
            self.value_number = value
        elif self.attribute.attribute_type.data_type == 'boolean':
            self.value_boolean = value
        elif self.attribute.attribute_type.data_type == 'date':
            self.value_date = value
        else:
            self.value_text = str(value)

class ProductVariant(PriceInheritanceMixin, TimestampMixin, AnalyticsMixin):
    """
    Product variants for different attribute combinations
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    
    # Identification
    sku = models.CharField(max_length=100, unique=True, verbose_name='کد محصول')
    
    # Pricing
    price = models.DecimalField(max_digits=12, decimal_places=0, verbose_name='قیمت (تومان)')
    compare_price = models.DecimalField(max_digits=12, decimal_places=0, null=True, blank=True, verbose_name='قیمت قبل از تخفیف')
    
    # Inventory
    stock_quantity = models.PositiveIntegerField(default=0, verbose_name='موجودی انبار')
    
    # Variant-specific media
    image = models.ImageField(upload_to='variants/', null=True, blank=True, verbose_name='تصویر نوع محصول')
    
    # Status
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    is_default = models.BooleanField(default=False, verbose_name='پیش‌فرض')
    
    class Meta:
        ordering = ['price']
        verbose_name = 'نوع محصول'
        verbose_name_plural = 'انواع محصول'
        indexes = [
            models.Index(fields=['product', 'is_active']),
            models.Index(fields=['sku']),
            models.Index(fields=['price']),
        ]
    
    def __str__(self):
        attrs = ", ".join([
            f"{attr_val.attribute.attribute_type.name_fa}: {attr_val.get_value()}" 
            for attr_val in self.attribute_values.all()
        ])
        return f"{self.product.name_fa} - {attrs}"
    
    def save(self, *args, **kwargs):
        # Auto-generate SKU if not provided
        if not self.sku:
            base_sku = self.product.sku or f"P{self.product.id.hex[:8]}"
            variant_suffix = f"V{uuid.uuid4().hex[:4].upper()}"
            self.sku = f"{base_sku}-{variant_suffix}"
        super().save(*args, **kwargs)
    
    @property
    def in_stock(self):
        return self.stock_quantity > 0
    
    @property
    def discount_percentage(self):
        """Calculate discount percentage"""
        if self.compare_price and self.compare_price > self.price:
            return round(((self.compare_price - self.price) / self.compare_price) * 100)
        return 0

class ProductImage(TimestampMixin):
    """Product images with social media import tracking"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, null=True, blank=True, related_name='images')
    
    image = models.ImageField(upload_to='products/', verbose_name='تصویر')
    alt_text = models.CharField(max_length=200, blank=True, verbose_name='متن جایگزین')
    is_featured = models.BooleanField(default=False, verbose_name='تصویر اصلی')
    display_order = models.PositiveIntegerField(default=0, verbose_name='ترتیب نمایش')
    
    # Social media import tracking
    imported_from_social = models.BooleanField(default=False, verbose_name='وارد شده از شبکه اجتماعی')
    social_media_url = models.URLField(null=True, blank=True, verbose_name='لینک اصلی')
    
    class Meta:
        ordering = ['display_order', 'created_at']
        verbose_name = 'تصویر محصول'
        verbose_name_plural = 'تصاویر محصول'
    
    def __str__(self):
        target = f"{self.product.name_fa}"
        if self.variant:
            target += f" - {self.variant}"
        return f"تصویر {target}"

class Collection(StoreOwnedMixin, TimestampMixin, SlugMixin, AnalyticsMixin):
    """Product collections for marketing"""
    name = models.CharField(max_length=100, verbose_name='نام مجموعه')
    name_fa = models.CharField(max_length=100, verbose_name='نام فارسی')
    description = models.TextField(blank=True, verbose_name='توضیحات')
    
    # Display
    featured_image = models.ImageField(upload_to='collections/', null=True, blank=True, verbose_name='تصویر شاخص')
    is_featured = models.BooleanField(default=False, verbose_name='مجموعه ویژه')
    display_order = models.PositiveIntegerField(default=0, verbose_name='ترتیب نمایش')
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    
    # Products
    products = models.ManyToManyField(Product, blank=True, related_name='collections', verbose_name='محصولات')
    
    class Meta:
        unique_together = ['store', 'slug']
        ordering = ['display_order', 'name_fa']
        verbose_name = 'مجموعه محصولات'
        verbose_name_plural = 'مجموعه‌های محصولات'
    
    def __str__(self):
        return self.name_fa or self.name

# Signal handlers for maintaining data consistency
from django.db.models.signals import post_save, pre_delete, m2m_changed
from django.dispatch import receiver

@receiver(post_save, sender=Product)
def update_category_product_count(sender, instance, **kwargs):
    """Update category product count when product is saved"""
    instance.category.update_product_count()
    instance.product_class.update_product_count()

@receiver(post_save, sender=Product)
def update_brand_product_count(sender, instance, **kwargs):
    """Update brand product count when product is saved"""
    if instance.brand:
        instance.brand.update_product_count()

@receiver(pre_delete, sender=Product)
def update_counts_on_delete(sender, instance, **kwargs):
    """Update counts when product is deleted"""
    instance.category.update_product_count()
    instance.product_class.update_product_count()
    if instance.brand:
        instance.brand.update_product_count()

@receiver(m2m_changed, sender=Product.tags.through)
def update_tag_usage_count(sender, instance, action, pk_set, **kwargs):
    """Update tag usage count when tags are added/removed"""
    if action in ['post_add', 'post_remove']:
        for tag_id in pk_set or []:
            try:
                tag = Tag.objects.get(id=tag_id)
                tag.usage_count = tag.products.count()
                tag.save(update_fields=['usage_count'])
            except Tag.DoesNotExist:
                pass

@receiver(post_save, sender=ProductClass)
def update_leaf_status(sender, instance, **kwargs):
    """Update is_leaf status for product classes"""
    if instance.parent:
        instance.parent.is_leaf = False
        instance.parent.save(update_fields=['is_leaf'])
