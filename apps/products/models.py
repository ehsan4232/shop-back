from django.db import models
from django.core.exceptions import ValidationError
from mptt.models import MPTTModel, TreeForeignKey
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
import uuid

class ProductCategory(MPTTModel):
    """
    Enhanced category model for jewelry/clothing/accessories/digital goods store
    Supports unlimited hierarchy with proper attribute inheritance
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
    
    # Category properties
    category_type = models.CharField(max_length=20, choices=[
        ('physical', 'کالای فیزیکی'),
        ('digital', 'کالای دیجیتال'),
        ('service', 'خدمات'),
    ], default='physical', verbose_name='نوع دسته‌بندی')
    
    # Display properties
    icon = models.CharField(max_length=50, blank=True, verbose_name='آیکون')
    banner_image = models.ImageField(upload_to='categories/', null=True, blank=True, verbose_name='تصویر بنر')
    display_order = models.PositiveIntegerField(default=0, verbose_name='ترتیب نمایش')
    show_in_menu = models.BooleanField(default=True, verbose_name='نمایش در منو')
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    
    # SEO
    meta_title = models.CharField(max_length=200, blank=True, verbose_name='عنوان متا')
    meta_description = models.TextField(blank=True, verbose_name='توضیحات متا')
    
    # Analytics
    product_count_cache = models.PositiveIntegerField(default=0, verbose_name='تعداد محصولات (کش)')
    view_count = models.PositiveIntegerField(default=0, verbose_name='تعداد بازدید')
    
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
            models.Index(fields=['store', 'show_in_menu', 'is_active']),
        ]
    
    def __str__(self):
        return self.name_fa or self.name
    
    @property
    def is_leaf(self):
        """Only leaf categories can have products"""
        return not self.children.exists()
    
    def get_all_attributes(self):
        """
        Get all attributes including inherited from parent hierarchy
        Implements proper OOP inheritance
        """
        # Use caching for performance
        cache_key = f"category_attributes_{self.id}"
        attrs = cache.get(cache_key)
        
        if attrs is None:
            # Direct attributes
            attrs = list(self.attributes.all().select_related('attribute_type').order_by('display_order'))
            
            # Inherited attributes from ancestors
            for ancestor in self.get_ancestors():
                inherited = ancestor.attributes.all().select_related('attribute_type')
                for attr in inherited:
                    # Avoid duplicates
                    if not any(a.attribute_type.name == attr.attribute_type.name for a in attrs):
                        attrs.append(attr)
            
            cache.set(cache_key, attrs, 300)  # Cache for 5 minutes
        
        return attrs
    
    def get_applicable_brands(self):
        """Get brands that have products in this category tree"""
        descendant_ids = [self.id] + list(self.get_descendants().values_list('id', flat=True))
        return Brand.objects.filter(
            products__category_id__in=descendant_ids,
            is_active=True
        ).distinct()
    
    def update_product_count(self):
        """Update cached product count"""
        descendant_ids = [self.id] + list(self.get_descendants().values_list('id', flat=True))
        count = Product.objects.filter(
            category_id__in=descendant_ids,
            status='published'
        ).count()
        self.product_count_cache = count
        self.save(update_fields=['product_count_cache'])
        return count

class AttributeType(models.Model):
    """
    Global attribute types that can be reused across categories
    Supports all common e-commerce attribute types
    """
    DISPLAY_TYPES = [
        ('text', 'متن'),
        ('number', 'عدد'),
        ('color', 'رنگ'),
        ('choice', 'انتخاب'),
        ('multi_choice', 'چند انتخاب'),
        ('range', 'محدوده'),
        ('boolean', 'بله/خیر'),
        ('measurement', 'اندازه‌گیری'),
        ('image', 'انتخاب تصویر'),
        ('date', 'تاریخ'),
    ]
    
    FILTER_TYPES = [
        ('exact', 'دقیق'),
        ('range', 'محدوده'),
        ('choice', 'چند انتخاب'),
        ('boolean', 'بله/خیر'),
        ('search', 'جستجو متنی'),
        ('none', 'بدون فیلتر'),
    ]
    
    name = models.CharField(max_length=50, unique=True, verbose_name='نام انگلیسی')
    name_fa = models.CharField(max_length=50, verbose_name='نام فارسی')
    display_type = models.CharField(max_length=20, choices=DISPLAY_TYPES, verbose_name='نوع نمایش')
    filter_type = models.CharField(max_length=20, choices=FILTER_TYPES, verbose_name='نوع فیلتر')
    
    # For measurements
    unit = models.CharField(max_length=20, blank=True, verbose_name='واحد', help_text='مثل: cm, kg, carat, gram')
    
    # For choices
    predefined_choices = models.JSONField(
        default=list, 
        blank=True,
        verbose_name='گزینه‌های از پیش تعریف شده',
        help_text='برای نوع انتخاب، لیست گزینه‌ها را وارد کنید'
    )
    
    # Behavior settings
    is_filterable = models.BooleanField(default=True, verbose_name='قابل فیلتر')
    is_searchable = models.BooleanField(default=False, verbose_name='قابل جستجو')
    show_in_listing = models.BooleanField(default=True, verbose_name='نمایش در لیست')
    is_variant_creating = models.BooleanField(
        default=False,
        verbose_name='ایجادکننده انواع محصول',
        help_text='آیا این ویژگی باعث ایجاد انواع مختلف محصول می‌شود؟'
    )
    
    # Display configuration
    icon = models.CharField(max_length=50, blank=True, verbose_name='آیکون')
    help_text = models.TextField(blank=True, verbose_name='متن راهنما')
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['name_fa']
        verbose_name = 'نوع ویژگی'
        verbose_name_plural = 'انواع ویژگی'
    
    def __str__(self):
        return self.name_fa
    
    @property
    def has_choices(self):
        return self.display_type in ['choice', 'multi_choice']

class ProductAttribute(models.Model):
    """Attributes assigned to categories with inheritance support"""
    category = models.ForeignKey(
        ProductCategory, 
        on_delete=models.CASCADE, 
        related_name='attributes',
        verbose_name='دسته‌بندی'
    )
    attribute_type = models.ForeignKey(
        AttributeType, 
        on_delete=models.CASCADE,
        verbose_name='نوع ویژگی'
    )
    
    # Customization for this category
    is_required = models.BooleanField(default=False, verbose_name='اجباری')
    display_order = models.PositiveIntegerField(default=0, verbose_name='ترتیب نمایش')
    
    # Override choices for this category
    custom_choices = models.JSONField(
        default=list, 
        blank=True,
        verbose_name='گزینه‌های سفارشی',
        help_text='گزینه‌های سفارشی برای این دسته‌بندی (جایگزین گزینه‌های پیش‌فرض)'
    )
    
    # Validation rules
    min_value = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        verbose_name='حداقل مقدار'
    )
    max_value = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        verbose_name='حداکثر مقدار'
    )
    
    # Inheritance tracking
    is_inherited = models.BooleanField(default=False, verbose_name='وراثتی')
    inherited_from = models.ForeignKey(
        ProductCategory, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='inherited_attributes',
        verbose_name='به ارث رسیده از'
    )
    
    class Meta:
        unique_together = ['category', 'attribute_type']
        ordering = ['display_order', 'attribute_type__name_fa']
        verbose_name = 'ویژگی دسته‌بندی'
        verbose_name_plural = 'ویژگی‌های دسته‌بندی'
    
    def __str__(self):
        inheritance_info = f" (از {self.inherited_from.name_fa})" if self.is_inherited else ""
        return f'{self.category.name_fa} - {self.attribute_type.name_fa}{inheritance_info}'
    
    @property
    def effective_choices(self):
        """Get effective choices (custom or predefined)"""
        return self.custom_choices or self.attribute_type.predefined_choices
    
    @property
    def is_variant_creating(self):
        """Check if this attribute creates product variants"""
        return self.attribute_type.is_variant_creating

class Brand(models.Model):
    """Brand management for cross-category filtering"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store = models.ForeignKey('stores.Store', on_delete=models.CASCADE, related_name='brands')
    
    # Basic info
    name = models.CharField(max_length=100, verbose_name='نام')
    name_fa = models.CharField(max_length=100, verbose_name='نام فارسی')
    slug = models.SlugField(max_length=100, verbose_name='نامک')
    
    # Brand details
    logo = models.ImageField(upload_to='brands/', null=True, blank=True, verbose_name='لوگو')
    description = models.TextField(blank=True, verbose_name='توضیحات')
    website = models.URLField(blank=True, verbose_name='وب‌سایت')
    country_of_origin = models.CharField(max_length=100, blank=True, verbose_name='کشور سازنده')
    
    # Display settings
    is_featured = models.BooleanField(default=False, verbose_name='ویژه')
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    display_order = models.PositiveIntegerField(default=0, verbose_name='ترتیب نمایش')
    
    # Analytics
    product_count = models.PositiveIntegerField(default=0, verbose_name='تعداد محصولات')
    view_count = models.PositiveIntegerField(default=0, verbose_name='تعداد بازدید')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['store', 'slug']
        ordering = ['display_order', 'name_fa']
        verbose_name = 'برند'
        verbose_name_plural = 'برندها'
        indexes = [
            models.Index(fields=['store', 'is_active']),
            models.Index(fields=['is_featured', 'display_order']),
        ]
    
    def __str__(self):
        return self.name_fa or self.name
    
    def update_product_count(self):
        """Update cached product count"""
        count = self.products.filter(status='published').count()
        self.product_count = count
        self.save(update_fields=['product_count'])
        return count

class Tag(models.Model):
    """Flexible tagging system for cross-category classification"""
    TAG_TYPES = [
        ('general', 'عمومی'),
        ('occasion', 'مناسبت'),     # عروسی، مهمانی، روزمره، رسمی
        ('season', 'فصل'),          # تابستان، زمستان، بهار، پاییز
        ('style', 'سبک'),           # مدرن، کلاسیک، وینتیج، اسپرت
        ('material', 'جنس'),        # طلا، نقره، پنبه، چرم
        ('feature', 'ویژگی'),       # ضد آب، دست‌ساز، ارگانیک
        ('target', 'مخاطب'),        # مردانه، زنانه، بچگانه
        ('price', 'قیمت'),          # اقتصادی، متوسط، لاکچری
    ]
    
    store = models.ForeignKey('stores.Store', on_delete=models.CASCADE, related_name='tags')
    name = models.CharField(max_length=50, verbose_name='نام')
    name_fa = models.CharField(max_length=50, verbose_name='نام فارسی')
    slug = models.SlugField(max_length=50, verbose_name='نامک')
    tag_type = models.CharField(max_length=20, choices=TAG_TYPES, verbose_name='نوع برچسب')
    
    # Display properties
    color = models.CharField(max_length=7, default='#007bff', verbose_name='رنگ')
    icon = models.CharField(max_length=50, blank=True, verbose_name='آیکون')
    description = models.TextField(blank=True, verbose_name='توضیحات')
    
    # Behavior
    is_featured = models.BooleanField(default=False, verbose_name='ویژه')
    is_filterable = models.BooleanField(default=True, verbose_name='قابل فیلتر')
    
    # Analytics
    usage_count = models.PositiveIntegerField(default=0, verbose_name='تعداد استفاده')
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['store', 'slug']
        ordering = ['-usage_count', 'name_fa']
        verbose_name = 'برچسب'
        verbose_name_plural = 'برچسب‌ها'
        indexes = [
            models.Index(fields=['store', 'tag_type']),
            models.Index(fields=['is_featured', '-usage_count']),
        ]
    
    def __str__(self):
        return self.name_fa
    
    def increment_usage(self):
        """Increment usage count"""
        self.usage_count += 1
        self.save(update_fields=['usage_count'])

class Product(models.Model):
    """Enhanced product model supporting multiple types and comprehensive features"""
    PRODUCT_TYPES = [
        ('simple', 'ساده'),
        ('variable', 'متغیر'),      # دارای انواع مختلف (سایز، رنگ، وزن)
        ('digital', 'دیجیتال'),
        ('bundle', 'بسته'),
        ('subscription', 'اشتراک'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'پیش‌نویس'),
        ('published', 'منتشر شده'),
        ('archived', 'بایگانی شده'),
        ('out_of_stock', 'ناموجود'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store = models.ForeignKey('stores.Store', on_delete=models.CASCADE, related_name='products')
    category = models.ForeignKey(
        ProductCategory, 
        on_delete=models.CASCADE, 
        related_name='products',
        limit_choices_to={'children__isnull': True},  # Only leaf categories
        verbose_name='دسته‌بندی'
    )
    brand = models.ForeignKey(
        Brand, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='products',
        verbose_name='برند'
    )
    
    # Basic information
    name = models.CharField(max_length=200, verbose_name='نام')
    name_fa = models.CharField(max_length=200, verbose_name='نام فارسی')
    slug = models.SlugField(max_length=200, verbose_name='نامک')
    description = models.TextField(blank=True, verbose_name='توضیحات کامل')
    short_description = models.CharField(max_length=500, blank=True, verbose_name='توضیحات کوتاه')
    
    # Product type
    product_type = models.CharField(
        max_length=20, 
        choices=PRODUCT_TYPES, 
        default='simple',
        verbose_name='نوع محصول'
    )
    
    # Pricing
    base_price = models.DecimalField(
        max_digits=12, 
        decimal_places=0, 
        verbose_name='قیمت پایه (تومان)'
    )
    compare_price = models.DecimalField(
        max_digits=12, 
        decimal_places=0, 
        null=True, 
        blank=True,
        verbose_name='قیمت قبل از تخفیف',
        help_text='قیمت اصلی قبل از تخفیف'
    )
    cost_price = models.DecimalField(
        max_digits=12, 
        decimal_places=0, 
        null=True, 
        blank=True,
        verbose_name='قیمت تمام شده',
        help_text='قیمت خرید یا تولید'
    )
    
    # Inventory (for simple products)
    sku = models.CharField(
        max_length=100, 
        unique=True, 
        null=True, 
        blank=True,
        verbose_name='کد محصول'
    )
    stock_quantity = models.PositiveIntegerField(default=0, verbose_name='موجودی انبار')
    manage_stock = models.BooleanField(default=True, verbose_name='مدیریت موجودی')
    low_stock_threshold = models.PositiveIntegerField(default=5, verbose_name='حد هشدار موجودی')
    
    # Digital product fields
    digital_file = models.FileField(
        upload_to='digital_products/', 
        null=True, 
        blank=True,
        verbose_name='فایل دیجیتال'
    )
    download_limit = models.PositiveIntegerField(
        null=True, 
        blank=True,
        verbose_name='حد دانلود'
    )
    download_expiry_days = models.PositiveIntegerField(
        null=True, 
        blank=True,
        verbose_name='مدت انقضا (روز)'
    )
    
    # Physical properties
    weight = models.DecimalField(
        max_digits=8, 
        decimal_places=2, 
        null=True, 
        blank=True,
        verbose_name='وزن (گرم)'
    )
    dimensions = models.JSONField(
        default=dict, 
        blank=True,
        verbose_name='ابعاد',
        help_text='طول، عرض، ارتفاع'
    )
    
    # Media
    featured_image = models.ImageField(
        upload_to='products/', 
        null=True, 
        blank=True,
        verbose_name='تصویر اصلی'
    )
    
    # SEO
    meta_title = models.CharField(max_length=200, blank=True, verbose_name='عنوان متا')
    meta_description = models.TextField(blank=True, verbose_name='توضیحات متا')
    meta_keywords = models.TextField(blank=True, verbose_name='کلمات کلیدی')
    
    # Status
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='draft',
        verbose_name='وضعیت'
    )
    is_featured = models.BooleanField(default=False, verbose_name='محصول ویژه')
    is_digital = models.BooleanField(default=False, verbose_name='محصول دیجیتال')
    
    # Relationships
    tags = models.ManyToManyField(Tag, blank=True, related_name='products', verbose_name='برچسب‌ها')
    related_products = models.ManyToManyField(
        'self', 
        blank=True, 
        symmetrical=False,
        verbose_name='محصولات مرتبط'
    )
    
    # Analytics and metrics
    view_count = models.PositiveIntegerField(default=0, verbose_name='تعداد بازدید')
    sales_count = models.PositiveIntegerField(default=0, verbose_name='تعداد فروش')
    rating_average = models.DecimalField(
        max_digits=3, 
        decimal_places=2, 
        default=0,
        verbose_name='میانگین امتیاز'
    )
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
    social_media_post_id = models.CharField(
        max_length=100, 
        null=True, 
        blank=True,
        verbose_name='شناسه پست'
    )
    
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
            models.Index(fields=['base_price']),
            models.Index(fields=['sku']),
            models.Index(fields=['-view_count']),
            models.Index(fields=['-sales_count']),
        ]
    
    def __str__(self):
        return self.name_fa or self.name
    
    def save(self, *args, **kwargs):
        # Auto-generate SKU if not provided
        if not self.sku and not self.id:
            self.sku = f"P{uuid.uuid4().hex[:8].upper()}"
        
        # Set published date on first publish
        if self.status == 'published' and not self.published_at:
            from django.utils import timezone
            self.published_at = timezone.now()
        
        super().save(*args, **kwargs)
    
    @property
    def is_variable(self):
        return self.product_type == 'variable'
    
    @property
    def is_simple(self):
        return self.product_type == 'simple'
    
    @property
    def in_stock(self):
        """Check if product is in stock"""
        if self.is_variable:
            return self.variants.filter(
                is_active=True,
                stock_quantity__gt=0
            ).exists()
        return self.stock_quantity > 0
    
    @property
    def discount_percentage(self):
        """Calculate discount percentage"""
        if self.compare_price and self.compare_price > self.base_price:
            return round(((self.compare_price - self.base_price) / self.compare_price) * 100)
        return 0
    
    def get_variants(self):
        """Get active variants"""
        return self.variants.filter(is_active=True)
    
    def get_price_range(self):
        """Get price range including variants"""
        if self.is_variable:
            variants = self.get_variants()
            if variants.exists():
                prices = variants.values_list('price', flat=True)
                return min(prices), max(prices)
        return self.base_price, self.base_price
    
    def get_available_attributes(self):
        """Get all available attributes for this product from category hierarchy"""
        return self.category.get_all_attributes()
    
    def get_variant_creating_attributes(self):
        """Get attributes that create variants"""
        return [attr for attr in self.get_available_attributes() 
                if attr.is_variant_creating]
    
    def increment_view_count(self):
        """Increment view count"""
        self.view_count += 1
        self.save(update_fields=['view_count'])
    
    def increment_sales_count(self, quantity=1):
        """Increment sales count"""
        self.sales_count += quantity
        self.save(update_fields=['sales_count'])

class ProductVariant(models.Model):
    """Product variants for different combinations of attributes (size, color, weight, etc.)"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    
    # Identification
    sku = models.CharField(max_length=100, unique=True, verbose_name='کد محصول')
    barcode = models.CharField(max_length=50, blank=True, verbose_name='بارکد')
    
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
    stock_quantity = models.PositiveIntegerField(default=0, verbose_name='موجودی انبار')
    
    # Physical properties
    weight = models.DecimalField(
        max_digits=8, 
        decimal_places=2, 
        null=True, 
        blank=True,
        verbose_name='وزن (گرم)'
    )
    dimensions = models.JSONField(
        default=dict, 
        blank=True,
        verbose_name='ابعاد'
    )
    
    # Variant-specific media
    image = models.ImageField(
        upload_to='variants/', 
        null=True, 
        blank=True,
        verbose_name='تصویر نوع محصول'
    )
    
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
            models.Index(fields=['stock_quantity']),
        ]
    
    def __str__(self):
        variant_attrs = self.get_attribute_summary()
        return f"{self.product.name_fa} - {variant_attrs}"
    
    def save(self, *args, **kwargs):
        # Auto-generate SKU if not provided
        if not self.sku:
            base_sku = self.product.sku or f"P{self.product.id.hex[:8]}"
            variant_suffix = f"V{uuid.uuid4().hex[:4].upper()}"
            self.sku = f"{base_sku}-{variant_suffix}"
        
        super().save(*args, **kwargs)
        
        # Set as default if it's the first variant
        if not self.product.variants.filter(is_default=True).exclude(id=self.id).exists():
            self.is_default = True
            super().save(update_fields=['is_default'])
    
    def get_attribute_summary(self):
        """Get a summary of variant attributes for display"""
        attrs = []
        for attr_value in self.attribute_values.select_related('attribute__attribute_type'):
            attrs.append(f"{attr_value.attribute.attribute_type.name_fa}: {attr_value.display_value}")
        return " | ".join(attrs) if attrs else "پایه"
    
    @property
    def in_stock(self):
        return self.stock_quantity > 0
    
    @property
    def discount_percentage(self):
        """Calculate discount percentage"""
        if self.compare_price and self.compare_price > self.price:
            return round(((self.compare_price - self.price) / self.compare_price) * 100)
        return 0

class ProductAttributeValue(models.Model):
    """Attribute values for products and variants with flexible storage"""
    
    # Link to either Product or ProductVariant
    product = models.ForeignKey(
        Product, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='attribute_values',
        verbose_name='محصول'
    )
    variant = models.ForeignKey(
        ProductVariant, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='attribute_values',
        verbose_name='نوع محصول'
    )
    
    attribute = models.ForeignKey(
        ProductAttribute, 
        on_delete=models.CASCADE,
        verbose_name='ویژگی'
    )
    
    # Flexible value storage for different attribute types
    value_text = models.CharField(max_length=500, blank=True, verbose_name='مقدار متنی')
    value_number = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        verbose_name='مقدار عددی'
    )
    value_boolean = models.BooleanField(null=True, blank=True, verbose_name='مقدار بولی')
    value_json = models.JSONField(
        default=dict, 
        blank=True,
        verbose_name='مقدار JSON',
        help_text='برای مقادیر پیچیده'
    )
    
    # Special handling for colors
    color_hex = models.CharField(
        max_length=7, 
        blank=True,
        verbose_name='کد رنگ',
        help_text='کد هگز رنگ مثل #FF0000'
    )
    color_image = models.ImageField(
        upload_to='colors/', 
        null=True, 
        blank=True,
        verbose_name='تصویر رنگ'
    )
    
    # For image attributes
    value_image = models.ImageField(
        upload_to='attribute_images/', 
        null=True, 
        blank=True,
        verbose_name='تصویر ویژگی'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['product', 'attribute']),
            models.Index(fields=['variant', 'attribute']),
            models.Index(fields=['attribute', 'value_text']),
            models.Index(fields=['attribute', 'value_number']),
        ]
        verbose_name = 'مقدار ویژگی'
        verbose_name_plural = 'مقادیر ویژگی'
        constraints = [
            models.CheckConstraint(
                check=models.Q(product__isnull=False) | models.Q(variant__isnull=False),
                name='product_or_variant_required'
            ),
            models.CheckConstraint(
                check=~(models.Q(product__isnull=False) & models.Q(variant__isnull=False)),
                name='not_both_product_and_variant'
            ),
        ]
    
    def clean(self):
        # Ensure either product or variant is set, not both
        if self.product and self.variant:
            raise ValidationError("نمی‌توان هم محصول و هم نوع محصول را انتخاب کرد")
        if not self.product and not self.variant:
            raise ValidationError("باید محصول یا نوع محصول انتخاب شود")
    
    @property
    def display_value(self):
        """Get formatted display value based on attribute type"""
        attr_type = self.attribute.attribute_type.display_type
        
        if attr_type == 'color':
            return self.value_text or self.color_hex
        elif attr_type in ['number', 'measurement']:
            unit = self.attribute.attribute_type.unit
            if self.value_number is not None:
                return f"{self.value_number} {unit}" if unit else str(self.value_number)
            return self.value_text
        elif attr_type == 'boolean':
            if self.value_boolean is not None:
                return 'بله' if self.value_boolean else 'خیر'
            return self.value_text
        elif attr_type in ['choice', 'multi_choice']:
            return self.value_json.get('display', self.value_text) if self.value_json else self.value_text
        elif attr_type == 'image':
            return self.value_image.url if self.value_image else self.value_text
        else:
            return self.value_text or str(self.value_number) if self.value_number else ''
    
    def __str__(self):
        target = self.product or self.variant
        return f"{target} - {self.attribute.attribute_type.name_fa}: {self.display_value}"

class ProductImage(models.Model):
    """Product and variant images with ordering support"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    variant = models.ForeignKey(
        ProductVariant, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='images'
    )
    
    image = models.ImageField(upload_to='products/', verbose_name='تصویر')
    alt_text = models.CharField(max_length=200, blank=True, verbose_name='متن جایگزین')
    title = models.CharField(max_length=200, blank=True, verbose_name='عنوان تصویر')
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
            target += f" - {self.variant.get_attribute_summary()}"
        return f"تصویر {target}"

class Collection(models.Model):
    """Product collections for marketing and organization"""
    COLLECTION_TYPES = [
        ('manual', 'انتخاب دستی'),
        ('automatic', 'خودکار بر اساس قوانین'),
    ]
    
    store = models.ForeignKey('stores.Store', on_delete=models.CASCADE, related_name='collections')
    name = models.CharField(max_length=100, verbose_name='نام مجموعه')
    name_fa = models.CharField(max_length=100, verbose_name='نام فارسی')
    slug = models.SlugField(max_length=100, verbose_name='نامک')
    description = models.TextField(blank=True, verbose_name='توضیحات')
    
    # Collection configuration
    collection_type = models.CharField(
        max_length=20, 
        choices=COLLECTION_TYPES, 
        default='manual',
        verbose_name='نوع مجموعه'
    )
    
    # For automatic collections
    auto_rules = models.JSONField(
        default=dict, 
        blank=True,
        verbose_name='قوانین خودکار',
        help_text='قوانین برای انتخاب خودکار محصولات'
    )
    
    # Display
    featured_image = models.ImageField(
        upload_to='collections/', 
        null=True, 
        blank=True,
        verbose_name='تصویر شاخص'
    )
    is_featured = models.BooleanField(default=False, verbose_name='مجموعه ویژه')
    display_order = models.PositiveIntegerField(default=0, verbose_name='ترتیب نمایش')
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    
    # Manual product selection
    products = models.ManyToManyField(
        Product, 
        blank=True, 
        related_name='collections',
        verbose_name='محصولات'
    )
    
    # SEO
    meta_title = models.CharField(max_length=200, blank=True, verbose_name='عنوان متا')
    meta_description = models.TextField(blank=True, verbose_name='توضیحات متا')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['store', 'slug']
        ordering = ['display_order', 'name_fa']
        verbose_name = 'مجموعه محصولات'
        verbose_name_plural = 'مجموعه‌های محصولات'
    
    def __str__(self):
        return self.name_fa or self.name
    
    def get_products(self):
        """Get products in this collection"""
        if self.collection_type == 'manual':
            return self.products.filter(status='published')
        else:
            # Apply automatic rules
            return self.apply_auto_rules()
    
    def apply_auto_rules(self):
        """Apply automatic collection rules"""
        # Implementation for automatic product selection based on rules
        # This could include filters by category, tags, price range, etc.
        queryset = Product.objects.filter(
            store=self.store,
            status='published'
        )
        
        rules = self.auto_rules
        if 'categories' in rules:
            queryset = queryset.filter(category__slug__in=rules['categories'])
        if 'tags' in rules:
            queryset = queryset.filter(tags__slug__in=rules['tags'])
        if 'price_min' in rules:
            queryset = queryset.filter(base_price__gte=rules['price_min'])
        if 'price_max' in rules:
            queryset = queryset.filter(base_price__lte=rules['price_max'])
        
        return queryset.distinct()

# Signal handlers for automatic attribute inheritance and cache invalidation
from django.db.models.signals import post_save, pre_delete, m2m_changed
from django.dispatch import receiver

@receiver(post_save, sender=ProductCategory)
def create_inherited_attributes(sender, instance, created, **kwargs):
    """
    Automatically create inherited attributes when a new category is created
    Implements proper OOP inheritance
    """
    if created and instance.parent:
        # Get all attributes from parent hierarchy
        parent_attributes = instance.parent.get_all_attributes()
        
        for parent_attr in parent_attributes:
            # Create inherited attribute for this category
            ProductAttribute.objects.get_or_create(
                category=instance,
                attribute_type=parent_attr.attribute_type,
                defaults={
                    'is_required': parent_attr.is_required,
                    'display_order': parent_attr.display_order,
                    'custom_choices': parent_attr.custom_choices,
                    'min_value': parent_attr.min_value,
                    'max_value': parent_attr.max_value,
                    'is_inherited': True,
                    'inherited_from': parent_attr.category,
                }
            )

@receiver(post_save, sender=Product)
def update_category_product_count(sender, instance, **kwargs):
    """Update category product count when product is saved"""
    instance.category.update_product_count()

@receiver(post_save, sender=Product)
def update_brand_product_count(sender, instance, **kwargs):
    """Update brand product count when product is saved"""
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

@receiver([post_save, pre_delete], sender=ProductAttribute)
def invalidate_category_attributes_cache(sender, instance, **kwargs):
    """Invalidate category attributes cache when attributes change"""
    cache_key = f"category_attributes_{instance.category.id}"
    cache.delete(cache_key)
    
    # Also invalidate for all descendants
    for descendant in instance.category.get_descendants():
        cache_key = f"category_attributes_{descendant.id}"
        cache.delete(cache_key)
