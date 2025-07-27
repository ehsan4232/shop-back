from django.db import models
from mptt.models import MPTTModel, TreeForeignKey
import uuid

class ProductCategory(MPTTModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store = models.ForeignKey('stores.Store', on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    name_fa = models.CharField(max_length=100, verbose_name='نام فارسی')
    description = models.TextField(blank=True)
    parent = TreeForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    is_categorizer = models.BooleanField(default=False, help_text='آیا این دسته برای دسته‌بندی استفاده شود؟')
    image = models.ImageField(upload_to='categories/', null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class MPTTMeta:
        order_insertion_by = ['name_fa']
    
    class Meta:
        verbose_name = 'دسته‌بندی'
        verbose_name_plural = 'دسته‌بندی‌ها'
    
    def __str__(self):
        return self.name_fa or self.name
    
    @property
    def is_leaf(self):
        return not self.children.exists()

class ProductAttribute(models.Model):
    ATTRIBUTE_TYPES = [
        ('color', 'رنگ'),
        ('description', 'توضیحات'),
        ('size', 'سایز'),
        ('weight', 'وزن'),
        ('material', 'جنس'),
        ('brand', 'برند'),
        ('custom', 'سفارشی'),
    ]
    
    category = models.ForeignKey(ProductCategory, on_delete=models.CASCADE, related_name='attributes')
    name = models.CharField(max_length=50)
    name_fa = models.CharField(max_length=50, verbose_name='نام فارسی')
    attribute_type = models.CharField(max_length=20, choices=ATTRIBUTE_TYPES)
    is_required = models.BooleanField(default=False)
    is_categorizer = models.BooleanField(default=False, help_text='آیا برای دسته‌بندی استفاده شود؟')
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['order', 'name_fa']
        verbose_name = 'ویژگی'
        verbose_name_plural = 'ویژگی‌ها'
    
    def __str__(self):
        return f'{self.category.name_fa} - {self.name_fa}'

class Product(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store = models.ForeignKey('stores.Store', on_delete=models.CASCADE)
    category = models.ForeignKey(ProductCategory, on_delete=models.CASCADE, limit_choices_to={'children__isnull': True})
    name = models.CharField(max_length=200)
    name_fa = models.CharField(max_length=200, verbose_name='نام فارسی')
    description = models.TextField(blank=True)
    description_fa = models.TextField(blank=True, verbose_name='توضیحات فارسی')
    base_price = models.DecimalField(max_digits=12, decimal_places=0, verbose_name='قیمت پایه')
    images = models.JSONField(default=list, verbose_name='تصاویر')
    videos = models.JSONField(default=list, verbose_name='ویدیوها')
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False, verbose_name='محصول ویژه')
    view_count = models.PositiveIntegerField(default=0, verbose_name='تعداد بازدید')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'محصول'
        verbose_name_plural = 'محصولات'
    
    def __str__(self):
        return self.name_fa or self.name
    
    def increment_view_count(self):
        self.view_count += 1
        self.save(update_fields=['view_count'])

class ProductInstance(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='instances')
    price = models.DecimalField(max_digits=12, decimal_places=0, null=True, blank=True)
    stock_quantity = models.PositiveIntegerField(default=0, verbose_name='موجودی انبار')
    sku = models.CharField(max_length=100, unique=True, verbose_name='کد محصول')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'نمونه محصول'
        verbose_name_plural = 'نمونه‌های محصول'
    
    def __str__(self):
        return f'{self.product.name_fa} - {self.sku}'
    
    @property
    def final_price(self):
        return self.price or self.product.base_price
    
    @property
    def is_low_stock(self):
        return self.stock_quantity <= 1

class ProductInstanceAttribute(models.Model):
    instance = models.ForeignKey(ProductInstance, on_delete=models.CASCADE, related_name='attributes')
    attribute = models.ForeignKey(ProductAttribute, on_delete=models.CASCADE)
    value = models.CharField(max_length=255)
    color_hex = models.CharField(max_length=7, null=True, blank=True, help_text='برای رنگ‌ها (مثل #FF0000)')
    
    class Meta:
        unique_together = ['instance', 'attribute']
        verbose_name = 'مقدار ویژگی'
        verbose_name_plural = 'مقادیر ویژگی‌ها'
    
    def __str__(self):
        return f'{self.instance} - {self.attribute.name_fa}: {self.value}'