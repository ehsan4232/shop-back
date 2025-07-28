from django.db import models
from django.conf import settings
from django.core.validators import RegexValidator
import uuid

class Store(models.Model):
    """
    Store model with multi-tenant architecture and theme support as per product description
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        related_name='stores',
        verbose_name='مالک'
    )
    
    # Basic Information
    name = models.CharField(max_length=100, verbose_name='نام فروشگاه')
    name_fa = models.CharField(max_length=100, verbose_name='نام فارسی فروشگاه')
    slug = models.SlugField(max_length=100, unique=True, verbose_name='نامک')
    description = models.TextField(blank=True, verbose_name='توضیحات')
    description_fa = models.TextField(blank=True, verbose_name='توضیحات فارسی')
    
    # Visual Identity (as mentioned in product description)
    logo = models.ImageField(
        upload_to='store_logos/', 
        null=True, 
        blank=True,
        verbose_name='لوگو',
        help_text='طراحی لوگوی منحصر به فرد با رنگ‌های قرمز، آبی و سفید'
    )
    banner = models.ImageField(
        upload_to='store_banners/', 
        null=True, 
        blank=True,
        verbose_name='بنر'
    )
    favicon = models.ImageField(
        upload_to='store_favicons/', 
        null=True, 
        blank=True,
        verbose_name='آیکون'
    )
    
    # Domain Support (custom domain and subdomain hosting)
    domain = models.CharField(
        max_length=255, 
        unique=True, 
        null=True, 
        blank=True,
        verbose_name='دامنه اختصاصی',
        help_text='دامنه اختصاصی مثل: mystore.com'
    )
    subdomain = models.CharField(
        max_length=50, 
        unique=True,
        verbose_name='زیردامنه',
        help_text='زیردامنه مثل: mystore (برای mystore.mall.ir)',
        validators=[RegexValidator(
            regex='^[a-zA-Z0-9]([a-zA-Z0-9-]{0,48}[a-zA-Z0-9])?$',
            message='زیردامنه باید شامل حروف انگلیسی، اعداد و خط تیره باشد'
        )]
    )
    
    # Contact Information
    phone = models.CharField(max_length=15, blank=True, verbose_name='شماره تلفن')
    email = models.EmailField(blank=True, verbose_name='ایمیل')
    address = models.TextField(blank=True, verbose_name='آدرس')
    city = models.CharField(max_length=100, blank=True, verbose_name='شهر')
    state = models.CharField(max_length=100, blank=True, verbose_name='استان')
    postal_code = models.CharField(max_length=10, blank=True, verbose_name='کد پستی')
    
    # Social Media Integration (for content import)
    instagram_username = models.CharField(
        max_length=100, 
        blank=True,
        verbose_name='نام کاربری اینستاگرام',
        help_text='برای واردات محتوا از اینستاگرام'
    )
    telegram_username = models.CharField(
        max_length=100, 
        blank=True,
        verbose_name='نام کاربری تلگرام',
        help_text='برای واردات محتوا از تلگرام'
    )
    telegram_channel_id = models.CharField(max_length=100, blank=True)
    
    # Business Settings
    currency = models.CharField(max_length=10, default='تومان', verbose_name='واحد پول')
    tax_rate = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=0, 
        verbose_name='نرخ مالیات'
    )
    
    # Store Status
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    is_verified = models.BooleanField(default=False, verbose_name='تأیید شده')
    is_premium = models.BooleanField(default=False, verbose_name='پریمیوم')
    
    # Analytics and Metrics
    total_orders = models.PositiveIntegerField(default=0, verbose_name='کل سفارشات')
    total_revenue = models.DecimalField(
        max_digits=15, 
        decimal_places=0, 
        default=0,
        verbose_name='کل درآمد'
    )
    view_count = models.PositiveIntegerField(default=0, verbose_name='تعداد بازدید')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'فروشگاه'
        verbose_name_plural = 'فروشگاه‌ها'
        indexes = [
            models.Index(fields=['subdomain']),
            models.Index(fields=['domain']),
            models.Index(fields=['owner', '-created_at']),
        ]
    
    def __str__(self):
        return self.name_fa or self.name
    
    @property
    def full_domain(self):
        """Get the full domain for the store"""
        if self.domain:
            return self.domain
        return f'{self.subdomain}.mall.ir'
    
    @property
    def url(self):
        """Get the full URL for the store"""
        return f'https://{self.full_domain}'
    
    def increment_view_count(self):
        """Increment store view count"""
        self.view_count += 1
        self.save(update_fields=['view_count'])

class StoreTheme(models.Model):
    """
    Store theme customization with real-time switching capability
    """
    LAYOUT_CHOICES = [
        ('modern', 'مدرن'),
        ('classic', 'کلاسیک'),
        ('minimal', 'مینیمال'),
        ('colorful', 'رنگارنگ'),
        ('elegant', 'شیک'),
        ('bold', 'پررنگ'),
    ]
    
    FONT_CHOICES = [
        ('vazir', 'وزیر'),
        ('iran-sans', 'ایران سنس'),
        ('shabnam', 'شبنم'),
        ('sahel', 'ساحل'),
        ('tanha', 'تنها'),
    ]
    
    store = models.OneToOneField(
        Store, 
        on_delete=models.CASCADE, 
        related_name='theme',
        verbose_name='فروشگاه'
    )
    name = models.CharField(max_length=100, verbose_name='نام تم')
    
    # Color customization
    primary_color = models.CharField(
        max_length=7, 
        default='#3B82F6',
        verbose_name='رنگ اصلی',
        help_text='مثال: #FF0000'
    )
    secondary_color = models.CharField(
        max_length=7, 
        default='#64748B',
        verbose_name='رنگ فرعی'
    )
    accent_color = models.CharField(
        max_length=7, 
        default='#F59E0B',
        verbose_name='رنگ تأکید'
    )
    background_color = models.CharField(
        max_length=7, 
        default='#FFFFFF',
        verbose_name='رنگ پس‌زمینه'
    )
    text_color = models.CharField(
        max_length=7, 
        default='#1F2937',
        verbose_name='رنگ متن'
    )
    
    # Typography
    font_family = models.CharField(
        max_length=50, 
        choices=FONT_CHOICES, 
        default='vazir',
        verbose_name='فونت'
    )
    font_size_base = models.PositiveIntegerField(default=16, verbose_name='اندازه فونت پایه')
    
    # Layout options
    layout = models.CharField(
        max_length=20, 
        choices=LAYOUT_CHOICES, 
        default='modern',
        verbose_name='طرح‌بندی'
    )
    header_style = models.CharField(
        max_length=20,
        choices=[('fixed', 'ثابت'), ('sticky', 'چسبان'), ('static', 'استاتیک')],
        default='sticky',
        verbose_name='سبک هدر'
    )
    footer_style = models.CharField(
        max_length=20,
        choices=[('minimal', 'مینیمال'), ('detailed', 'تفصیلی'), ('simple', 'ساده')],
        default='simple',
        verbose_name='سبک فوتر'
    )
    
    # Product display options
    products_per_page = models.PositiveIntegerField(default=12, verbose_name='محصول در هر صفحه')
    product_card_style = models.CharField(
        max_length=20,
        choices=[('card', 'کارت'), ('list', 'لیست'), ('grid', 'گرید')],
        default='card',
        verbose_name='سبک کارت محصول'
    )
    show_product_badges = models.BooleanField(default=True, verbose_name='نمایش برچسب محصولات')
    
    # Custom CSS
    custom_css = models.TextField(
        blank=True, 
        verbose_name='CSS سفارشی',
        help_text='کد CSS سفارشی برای شخصی‌سازی بیشتر'
    )
    
    # Images
    homepage_banner = models.ImageField(
        upload_to='theme_banners/', 
        null=True, 
        blank=True,
        verbose_name='بنر صفحه اصلی'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'تم فروشگاه'
        verbose_name_plural = 'تم‌های فروشگاه'
    
    def __str__(self):
        return f'{self.name} - {self.store.name_fa}'

class StoreSettings(models.Model):
    """
    Store configuration and settings
    """
    store = models.OneToOneField(
        Store, 
        on_delete=models.CASCADE, 
        related_name='settings',
        verbose_name='فروشگاه'
    )
    
    # SEO Settings
    meta_title = models.CharField(max_length=200, blank=True, verbose_name='عنوان متا')
    meta_description = models.TextField(blank=True, verbose_name='توضیحات متا')
    meta_keywords = models.TextField(blank=True, verbose_name='کلمات کلیدی')
    robots_txt = models.TextField(blank=True, verbose_name='محتوای robots.txt')
    
    # Analytics Integration
    google_analytics_id = models.CharField(max_length=50, blank=True, verbose_name='Google Analytics ID')
    google_tag_manager_id = models.CharField(max_length=50, blank=True, verbose_name='Google Tag Manager ID')
    facebook_pixel_id = models.CharField(max_length=50, blank=True, verbose_name='Facebook Pixel ID')
    
    # Payment Gateway Integration (Iranian providers)
    zarinpal_merchant_id = models.CharField(max_length=100, blank=True, verbose_name='ZarinPal Merchant ID')
    parsian_pin = models.CharField(max_length=100, blank=True, verbose_name='Parsian PIN')
    mellat_terminal_id = models.CharField(max_length=100, blank=True, verbose_name='Mellat Terminal ID')
    
    # SMS Integration
    sms_provider = models.CharField(
        max_length=20,
        choices=[('kavenegar', 'کاوه نگار'), ('farapayamak', 'فراپیامک'), ('melipayamak', 'ملی پیامک')],
        default='kavenegar',
        verbose_name='ارائه‌دهنده SMS'
    )
    sms_api_key = models.CharField(max_length=200, blank=True, verbose_name='کلید API پیامک')
    sms_sender_number = models.CharField(max_length=15, blank=True, verbose_name='شماره ارسال کننده')
    
    # SMS Templates
    sms_welcome_template = models.TextField(
        blank=True, 
        verbose_name='قالب پیام خوش‌آمدگویی',
        help_text='متغیرها: {name}, {store_name}'
    )
    sms_order_confirmation_template = models.TextField(
        blank=True,
        verbose_name='قالب تأیید سفارش',
        help_text='متغیرها: {order_id}, {total}, {store_name}'
    )
    sms_shipping_template = models.TextField(
        blank=True,
        verbose_name='قالب ارسال سفارش',
        help_text='متغیرها: {order_id}, {tracking_code}'
    )
    
    # Logistics Integration (Iranian providers)
    logistics_provider = models.CharField(
        max_length=20,
        choices=[
            ('post', 'پست ایران'),
            ('tipax', 'تیپاکس'),
            ('chapar', 'چاپار'),
            ('miare', 'میاره'),
        ],
        default='post',
        verbose_name='ارائه‌دهنده حمل و نقل'
    )
    logistics_api_key = models.CharField(max_length=200, blank=True, verbose_name='کلید API حمل و نقل')
    
    # Store Policies
    return_policy = models.TextField(blank=True, verbose_name='سیاست برگشت کالا')
    privacy_policy = models.TextField(blank=True, verbose_name='سیاست حریم خصوصی')
    terms_of_service = models.TextField(blank=True, verbose_name='شرایط استفاده')
    shipping_policy = models.TextField(blank=True, verbose_name='سیاست ارسال')
    
    # Business Hours
    working_hours = models.JSONField(
        default=dict,
        verbose_name='ساعات کاری',
        help_text='ساعات کاری هر روز هفته'
    )
    
    # Feature Toggles
    enable_chat = models.BooleanField(default=True, verbose_name='فعال‌سازی چت آنلاین')
    enable_reviews = models.BooleanField(default=True, verbose_name='فعال‌سازی نظرات')
    enable_wishlist = models.BooleanField(default=True, verbose_name='فعال‌سازی لیست علاقه‌مندی')
    enable_compare = models.BooleanField(default=True, verbose_name='فعال‌سازی مقایسه محصولات')
    enable_social_login = models.BooleanField(default=False, verbose_name='ورود با شبکه‌های اجتماعی')
    
    # Inventory Settings
    low_stock_threshold = models.PositiveIntegerField(default=5, verbose_name='حد هشدار موجودی')
    auto_reduce_stock = models.BooleanField(default=True, verbose_name='کاهش خودکار موجودی')
    allow_backorders = models.BooleanField(default=False, verbose_name='اجازه پیش‌سفارش')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'تنظیمات فروشگاه'
        verbose_name_plural = 'تنظیمات فروشگاه‌ها'
    
    def __str__(self):
        return f'تنظیمات {self.store.name_fa}'

class StoreAnalytics(models.Model):
    """
    Store analytics and metrics tracking
    """
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='analytics')
    date = models.DateField(verbose_name='تاریخ')
    
    # Traffic Metrics
    visitors = models.PositiveIntegerField(default=0, verbose_name='بازدیدکنندگان')
    page_views = models.PositiveIntegerField(default=0, verbose_name='بازدید صفحات')
    unique_visitors = models.PositiveIntegerField(default=0, verbose_name='بازدیدکنندگان منحصر به فرد')
    bounce_rate = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=0,
        verbose_name='نرخ پرش'
    )
    
    # Sales Metrics
    orders_count = models.PositiveIntegerField(default=0, verbose_name='تعداد سفارشات')
    revenue = models.DecimalField(
        max_digits=15, 
        decimal_places=0, 
        default=0,
        verbose_name='درآمد'
    )
    conversion_rate = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=0,
        verbose_name='نرخ تبدیل'
    )
    average_order_value = models.DecimalField(
        max_digits=12, 
        decimal_places=0, 
        default=0,
        verbose_name='میانگین ارزش سفارش'
    )
    
    # Product Metrics
    products_viewed = models.PositiveIntegerField(default=0, verbose_name='محصولات مشاهده شده')
    cart_additions = models.PositiveIntegerField(default=0, verbose_name='افزودن به سبد')
    cart_abandonment_rate = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=0,
        verbose_name='نرخ رها کردن سبد'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'آمار فروشگاه'
        verbose_name_plural = 'آمارهای فروشگاه'
        unique_together = ['store', 'date']
        ordering = ['-date']
    
    def __str__(self):
        return f'{self.store.name_fa} - {self.date}'
