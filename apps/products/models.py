from django.db import models
from django.core.exceptions import ValidationError
from mptt.models import MPTTModel, TreeForeignKey
from django.core.cache import cache
import uuid

class ProductCategory(MPTTModel):
    """
    Simplified category model with inheritance support
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store = models.ForeignKey('stores.Store', on_delete=models.CASCADE, related_name='categories')
    
    # Basic info
    name = models.CharField(max_length=100, verbose_name='نام')
    name_fa = models.CharField(max_length=100, verbose_name='نام فارسی')
    slug = models.SlugField(max_length=100, verbose_name='نامک')
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
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
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

class Brand(models.Model):
    """Brand management"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store = models.ForeignKey('stores.Store', on_delete=models.CASCADE, related_name='brands')
    
    name = models.CharField(max_length=100, verbose_name='نام')
    name_fa = models.CharField(max_length=100, verbose_name='نام فارسی')
    slug = models.SlugField(max_length=100, verbose_name='نامک')
    logo = models.ImageField(upload_to='brands/', null=True, blank=True, verbose_name='لوگو')
    description = models.TextField(blank=True, verbose_name='توضیحات')
    
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    product_count = models.PositiveIntegerField(default=0, verbose_name='تعداد محصولات')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
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

class ProductAttribute(models.Model):
    """
    Simple product attributes (color, size, etc.)
    """
    ATTRIBUTE_TYPES = [
        ('text', 'متن'),
        ('color', 'رنگ'),
        ('size', 'سایز'),
        ('number', 'عدد'),
        ('choice', 'انتخاب'),
    ]
    
    name = models.CharField(max_length=50, verbose_name='نام ویژگی')
    attribute_type = models.CharField(max_length=20, choices=ATTRIBUTE_TYPES, verbose_name='نوع')
    values = models.JSONField(default=list, verbose_name='مقادیر ممکن')
    
    class Meta:
        verbose_name = 'ویژگی محصول'
        verbose_name_plural = 'ویژگی‌های محصول'
    
    def __str__(self):
        return self.name

class Product(models.Model):
    """
    Simplified product model - focusing on core functionality
    """
    STATUS_CHOICES = [
        ('draft', 'پیش‌نویس'),
        ('published', 'منتشر شده'),
        ('archived', 'بایگانی شده'),
        ('out_of_stock', 'ناموجود'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store = models.ForeignKey('stores.Store', on_delete=models.CASCADE, related_name='products')
    category = models.ForeignKey(ProductCategory, on_delete=models.CASCADE, related_name='products')
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    
    # Basic information
    name = models.CharField(max_length=200, verbose_name='نام')
    name_fa = models.CharField(max_length=200, verbose_name='نام فارسی')
    slug = models.SlugField(max_length=200, verbose_name='نامک')
    description = models.TextField(blank=True, verbose_name='توضیحات')
    short_description = models.CharField(max_length=500, blank=True, verbose_name='توضیحات کوتاه')
    
    # Pricing
    price = models.DecimalField(max_digits=12, decimal_places=0, verbose_name='قیمت (تومان)')
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
    
    # SEO
    meta_title = models.CharField(max_length=200, blank=True, verbose_name='عنوان متا')
    meta_description = models.TextField(blank=True, verbose_name='توضیحات متا')
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', verbose_name='وضعیت')
    is_featured = models.BooleanField(default=False, verbose_name='محصول ویژه')
    
    # Analytics
    view_count = models.PositiveIntegerField(default=0, verbose_name='تعداد بازدید')
    sales_count = models.PositiveIntegerField(default=0, verbose_name='تعداد فروش')
    
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
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاریخ به‌روزرسانی')
    published_at = models.DateTimeField(null=True, blank=True, verbose_name='تاریخ انتشار')
    
    class Meta:
        unique_together = ['store', 'slug']
        ordering = ['-created_at']
        verbose_name = 'محصول'
        verbose_name_plural = 'محصولات'
        indexes = [
            models.Index(fields=['store', 'status', '-created_at']),
            models.Index(fields=['category', 'status']),
            models.Index(fields=['brand', 'status']),
            models.Index(fields=['status', 'is_featured']),
            models.Index(fields=['price']),
            models.Index(fields=['sku']),
            models.Index(fields=['-view_count']),
            models.Index(fields=['-sales_count']),
        ]
    
    def __str__(self):
        return self.name_fa or self.name
    
    def save(self, *args, **kwargs):
        # Auto-generate SKU if not provided
        if not self.sku:
            self.sku = f"P{uuid.uuid4().hex[:8].upper()}"
        
        # Set published date on first publish
        if self.status == 'published' and not self.published_at:
            from django.utils import timezone
            self.published_at = timezone.now()
        
        super().save(*args, **kwargs)
    
    @property
    def in_stock(self):
        """Check if product is in stock"""
        return self.stock_quantity > 0
    
    @property
    def discount_percentage(self):
        """Calculate discount percentage"""
        if self.compare_price and self.compare_price > self.price:
            return round(((self.compare_price - self.price) / self.compare_price) * 100)
        return 0
    
    @property
    def is_low_stock(self):
        """Check if product is low in stock"""
        return self.stock_quantity <= self.low_stock_threshold
    
    def increment_view_count(self):
        """Increment view count"""
        self.view_count += 1
        self.save(update_fields=['view_count'])
    
    def increment_sales_count(self, quantity=1):
        """Increment sales count"""
        self.sales_count += quantity
        self.save(update_fields=['sales_count'])

class ProductVariant(models.Model):
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
    
    # Attributes as JSON for simplicity
    attributes = models.JSONField(default=dict, verbose_name='ویژگی‌ها')
    
    # Status
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    is_default = models.BooleanField(default=False, verbose_name='پیش‌فرض')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
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
        attrs = ", ".join([f"{k}: {v}" for k, v in self.attributes.items()])
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

class ProductImage(models.Model):
    """Product images"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, null=True, blank=True, related_name='images')
    
    image = models.ImageField(upload_to='products/', verbose_name='تصویر')
    alt_text = models.CharField(max_length=200, blank=True, verbose_name='متن جایگزین')
    is_featured = models.BooleanField(default=False, verbose_name='تصویر اصلی')
    display_order = models.PositiveIntegerField(default=0, verbose_name='ترتیب نمایش')
    
    # Social media import tracking
    imported_from_social = models.BooleanField(default=False, verbose_name='وارد شده از شبکه اجتماعی')
    social_media_url = models.URLField(null=True, blank=True, verbose_name='لینک اصلی')
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['display_order', 'created_at']
        verbose_name = 'تصویر محصول'
        verbose_name_plural = 'تصاویر محصول'
    
    def __str__(self):
        target = f"{self.product.name_fa}"
        if self.variant:
            target += f" - {self.variant}"
        return f"تصویر {target}"

class Collection(models.Model):
    """Product collections for marketing"""
    store = models.ForeignKey('stores.Store', on_delete=models.CASCADE, related_name='collections')
    name = models.CharField(max_length=100, verbose_name='نام مجموعه')
    name_fa = models.CharField(max_length=100, verbose_name='نام فارسی')
    slug = models.SlugField(max_length=100, verbose_name='نامک')
    description = models.TextField(blank=True, verbose_name='توضیحات')
    
    # Display
    featured_image = models.ImageField(upload_to='collections/', null=True, blank=True, verbose_name='تصویر شاخص')
    is_featured = models.BooleanField(default=False, verbose_name='مجموعه ویژه')
    display_order = models.PositiveIntegerField(default=0, verbose_name='ترتیب نمایش')
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    
    # Products
    products = models.ManyToManyField(Product, blank=True, related_name='collections', verbose_name='محصولات')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['store', 'slug']
        ordering = ['display_order', 'name_fa']
        verbose_name = 'مجموعه محصولات'
        verbose_name_plural = 'مجموعه‌های محصولات'
    
    def __str__(self):
        return self.name_fa or self.name

# Signal handlers
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

@receiver(post_save, sender=Product)
def update_category_product_count(sender, instance, **kwargs):
    """Update category product count when product is saved"""
    instance.category.update_product_count()

@receiver(post_save, sender=Product)
def update_brand_product_count(sender, instance, **kwargs):
    """Update brand product count when product is saved"""
    if instance.brand:
        instance.brand.update_product_count()

@receiver(pre_delete, sender=Product)
def update_counts_on_delete(sender, instance, **kwargs):
    """Update counts when product is deleted"""
    instance.category.update_product_count()
    if instance.brand:
        instance.brand.update_product_count()
