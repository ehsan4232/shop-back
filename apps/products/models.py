from django.db import models
from mptt.models import MPTTModel, TreeForeignKey
import uuid

class ProductClass(MPTTModel):
    """
    Product Class with unlimited tree structure as per product description.
    Represents categories and subcategories that can be marked as categorizers.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store = models.ForeignKey('stores.Store', on_delete=models.CASCADE, related_name='product_classes')
    name = models.CharField(max_length=100, verbose_name='نام')
    name_fa = models.CharField(max_length=100, verbose_name='نام فارسی')
    slug = models.SlugField(max_length=100, verbose_name='نامک')
    description = models.TextField(blank=True, verbose_name='توضیحات')
    parent = TreeForeignKey(
        'self', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='children',
        verbose_name='والد'
    )
    is_categorizer = models.BooleanField(
        default=False, 
        help_text='آیا این کلاس برای دسته‌بندی استفاده شود؟ (Level 1 children)'
    )
    image = models.ImageField(upload_to='product_classes/', null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class MPTTMeta:
        order_insertion_by = ['name_fa']
    
    class Meta:
        verbose_name = 'کلاس محصول'
        verbose_name_plural = 'کلاس‌های محصول'
        unique_together = ['store', 'slug']
    
    def __str__(self):
        return self.name_fa or self.name
    
    @property
    def is_leaf(self):
        """Only leaf nodes can have product instances"""
        return not self.children.exists()
    
    def get_attributes(self):
        """Get all attributes for this class including inherited ones"""
        attrs = list(self.attributes.all())
        if self.parent:
            attrs.extend(self.parent.get_attributes())
        return attrs

class ProductAttribute(models.Model):
    """
    Product attributes as described: Color, Description, and Custom types
    """
    ATTRIBUTE_TYPES = [
        ('color', 'رنگ'),
        ('description', 'توضیحات'),
        ('text', 'متن'),
        ('number', 'عدد'),
        ('boolean', 'بولی'),
        ('choice', 'انتخاب'),
        ('custom', 'سفارشی'),
    ]
    
    product_class = models.ForeignKey(
        ProductClass, 
        on_delete=models.CASCADE, 
        related_name='attributes'
    )
    name = models.CharField(max_length=50, verbose_name='نام')
    name_fa = models.CharField(max_length=50, verbose_name='نام فارسی')
    attribute_type = models.CharField(max_length=20, choices=ATTRIBUTE_TYPES)
    is_required = models.BooleanField(default=False, verbose_name='اجباری')
    is_price_attribute = models.BooleanField(
        default=False, 
        help_text='آیا این ویژگی روی قیمت تأثیر دارد؟'
    )
    choices = models.JSONField(
        default=list, 
        blank=True, 
        help_text='برای نوع انتخاب، گزینه‌ها را وارد کنید'
    )
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['order', 'name_fa']
        verbose_name = 'ویژگی محصول'
        verbose_name_plural = 'ویژگی‌های محصول'
        unique_together = ['product_class', 'name']
    
    def __str__(self):
        return f'{self.product_class.name_fa} - {self.name_fa}'

class Product(models.Model):
    """
    Product with price attribute and media lists as per description
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product_class = models.ForeignKey(
        ProductClass, 
        on_delete=models.CASCADE, 
        related_name='products',
        limit_choices_to={'children__isnull': True}  # Only leaf nodes
    )
    name = models.CharField(max_length=200, verbose_name='نام')
    name_fa = models.CharField(max_length=200, verbose_name='نام فارسی')
    slug = models.SlugField(max_length=200, verbose_name='نامک')
    description = models.TextField(blank=True, verbose_name='توضیحات')
    description_fa = models.TextField(blank=True, verbose_name='توضیحات فارسی')
    base_price = models.DecimalField(
        max_digits=12, 
        decimal_places=0, 
        verbose_name='قیمت پایه (تومان)'
    )
    
    # Media lists as mentioned in description
    images = models.JSONField(default=list, verbose_name='تصاویر')
    videos = models.JSONField(default=list, verbose_name='ویدیوها')
    
    # Social media integration fields
    imported_from_social = models.BooleanField(default=False)
    social_media_source = models.CharField(
        max_length=20, 
        choices=[('telegram', 'تلگرام'), ('instagram', 'اینستاگرام')],
        null=True, blank=True
    )
    social_media_post_id = models.CharField(max_length=100, null=True, blank=True)
    
    # Status and metrics
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False, verbose_name='محصول ویژه')
    view_count = models.PositiveIntegerField(default=0, verbose_name='تعداد بازدید')
    purchase_count = models.PositiveIntegerField(default=0, verbose_name='تعداد خرید')
    
    # SEO
    meta_title = models.CharField(max_length=200, blank=True)
    meta_description = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'محصول'
        verbose_name_plural = 'محصولات'
        unique_together = ['product_class', 'slug']
    
    def __str__(self):
        return self.name_fa or self.name
    
    @property
    def store(self):
        return self.product_class.store
    
    def increment_view_count(self):
        self.view_count += 1
        self.save(update_fields=['view_count'])
    
    def increment_purchase_count(self):
        self.purchase_count += 1
        self.save(update_fields=['purchase_count'])

class ProductInstance(models.Model):
    """
    Product instances created from leaf products only, with varying attributes
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='instances')
    sku = models.CharField(max_length=100, unique=True, verbose_name='کد محصول')
    price = models.DecimalField(
        max_digits=12, 
        decimal_places=0, 
        null=True, 
        blank=True,
        verbose_name='قیمت (تومان)'
    )
    stock_quantity = models.PositiveIntegerField(default=0, verbose_name='موجودی انبار')
    low_stock_threshold = models.PositiveIntegerField(default=5, verbose_name='حد هشدار موجودی')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'نمونه محصول'
        verbose_name_plural = 'نمونه‌های محصول'
    
    def __str__(self):
        return f'{self.product.name_fa} - {self.sku}'
    
    @property
    def final_price(self):
        """Return instance price or product base price"""
        return self.price or self.product.base_price
    
    @property
    def is_low_stock(self):
        """Check if stock is below threshold"""
        return self.stock_quantity <= self.low_stock_threshold
    
    @property
    def is_out_of_stock(self):
        return self.stock_quantity <= 0

class ProductInstanceAttribute(models.Model):
    """
    Attribute values for product instances with multiple instances having varying attributes
    """
    instance = models.ForeignKey(
        ProductInstance, 
        on_delete=models.CASCADE, 
        related_name='attribute_values'
    )
    attribute = models.ForeignKey(ProductAttribute, on_delete=models.CASCADE)
    value = models.CharField(max_length=500, verbose_name='مقدار')
    
    # Special field for color attributes (visual color squares)
    color_hex = models.CharField(
        max_length=7, 
        null=True, 
        blank=True, 
        help_text='برای رنگ‌ها (مثل #FF0000)'
    )
    
    class Meta:
        unique_together = ['instance', 'attribute']
        verbose_name = 'مقدار ویژگی نمونه'
        verbose_name_plural = 'مقادیر ویژگی‌های نمونه'
    
    def __str__(self):
        return f'{self.instance} - {self.attribute.name_fa}: {self.value}'

class ProductMedia(models.Model):
    """
    Separate model for product media to better handle social media integration
    """
    MEDIA_TYPES = [
        ('image', 'تصویر'),
        ('video', 'ویدیو'),
    ]
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='media')
    media_type = models.CharField(max_length=10, choices=MEDIA_TYPES)
    file = models.FileField(upload_to='products/')
    thumbnail = models.ImageField(upload_to='products/thumbnails/', null=True, blank=True)
    alt_text = models.CharField(max_length=200, blank=True)
    title = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    
    # Social media source tracking
    imported_from_social = models.BooleanField(default=False)
    social_media_url = models.URLField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['order', '-created_at']
        verbose_name = 'رسانه محصول'
        verbose_name_plural = 'رسانه‌های محصول'
    
    def __str__(self):
        return f'{self.product.name_fa} - {self.get_media_type_display()}'

class SocialMediaImport(models.Model):
    """
    Track social media imports for products
    """
    SOURCES = [
        ('telegram', 'تلگرام'),
        ('instagram', 'اینستاگرام'),
    ]
    
    store = models.ForeignKey('stores.Store', on_delete=models.CASCADE)
    source = models.CharField(max_length=20, choices=SOURCES)
    channel_username = models.CharField(max_length=100, verbose_name='نام کاربری کانال')
    post_id = models.CharField(max_length=100, verbose_name='شناسه پست')
    post_url = models.URLField()
    imported_content = models.JSONField(verbose_name='محتوای وارد شده')
    products_created = models.ManyToManyField(Product, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['source', 'post_id']
        verbose_name = 'واردات شبکه اجتماعی'
        verbose_name_plural = 'واردات‌های شبکه اجتماعی'
    
    def __str__(self):
        return f'{self.get_source_display()} - {self.channel_username} - {self.post_id}'
