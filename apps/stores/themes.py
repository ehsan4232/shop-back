from django.db import models
from django.core.exceptions import ValidationError
from apps.core.mixins import TimestampMixin
from apps.stores.models import Store
import uuid
import json


class StoreTheme(TimestampMixin):
    """
    Store themes and layouts system
    Product requirement: "there are various fancy and modern designs and layouts and themes there for store owners to choose from"
    """
    
    THEME_CATEGORY_CHOICES = [
        ('fashion', 'پوشاک و مد'),
        ('electronics', 'الکترونیک'),
        ('jewelry', 'جواهرات'),
        ('home_garden', 'خانه و باغ'),
        ('beauty', 'زیبایی و سلامت'),
        ('sports', 'ورزشی'),
        ('books', 'کتاب و فرهنگ'),
        ('food', 'غذا و نوشیدنی'),
        ('automotive', 'خودرو'),
        ('services', 'خدمات'),
        ('general', 'عمومی'),
    ]
    
    LAYOUT_TYPE_CHOICES = [
        ('grid', 'شبکه‌ای'),
        ('list', 'لیستی'),
        ('masonry', 'آجری'),
        ('carousel', 'کروسل'),
        ('magazine', 'مجله‌ای'),
        ('minimal', 'مینیمال'),
    ]
    
    COLOR_SCHEME_CHOICES = [
        ('light', 'روشن'),
        ('dark', 'تیره'),
        ('colorful', 'رنگارنگ'),
        ('monochrome', 'تک‌رنگ'),
        ('vintage', 'کلاسیک'),
        ('modern', 'مدرن'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Basic Information
    name = models.CharField(max_length=100, unique=True, verbose_name='نام قالب')
    name_fa = models.CharField(max_length=100, verbose_name='نام فارسی')
    description = models.TextField(verbose_name='توضیحات')
    
    # Categorization
    category = models.CharField(max_length=20, choices=THEME_CATEGORY_CHOICES, verbose_name='دسته‌بندی')
    layout_type = models.CharField(max_length=20, choices=LAYOUT_TYPE_CHOICES, verbose_name='نوع چیدمان')
    color_scheme = models.CharField(max_length=20, choices=COLOR_SCHEME_CHOICES, verbose_name='طرح رنگی')
    
    # Visual Assets
    preview_image = models.ImageField(upload_to='themes/previews/', verbose_name='تصویر پیش‌نمایش')
    preview_images = models.JSONField(default=list, verbose_name='تصاویر پیش‌نمایش متعدد')
    demo_url = models.URLField(blank=True, verbose_name='لینک دمو')
    
    # Theme Configuration
    css_framework = models.CharField(max_length=50, default='tailwind', verbose_name='فریمورک CSS')
    primary_color = models.CharField(max_length=7, default='#3B82F6', verbose_name='رنگ اصلی')
    secondary_color = models.CharField(max_length=7, default='#EF4444', verbose_name='رنگ فرعی')
    accent_color = models.CharField(max_length=7, default='#10B981', verbose_name='رنگ تاکیدی')
    
    # Design Properties
    is_responsive = models.BooleanField(default=True, verbose_name='ریسپانسیو')
    is_rtl_ready = models.BooleanField(default=True, verbose_name='آماده برای راست‌چین')
    supports_dark_mode = models.BooleanField(default=False, verbose_name='پشتیبانی حالت تیره')
    
    # Features
    features = models.JSONField(default=list, verbose_name='امکانات')
    # Example: ['mega_menu', 'product_zoom', 'wishlist', 'compare', 'quick_view']
    
    # Availability
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    is_premium = models.BooleanField(default=False, verbose_name='پریمیوم')
    price = models.PositiveIntegerField(default=0, verbose_name='قیمت (تومان)')
    
    # Usage Statistics
    install_count = models.PositiveIntegerField(default=0, verbose_name='تعداد نصب')
    rating_average = models.DecimalField(max_digits=3, decimal_places=2, default=0, verbose_name='میانگین امتیاز')
    rating_count = models.PositiveIntegerField(default=0, verbose_name='تعداد امتیاز')
    
    # Template Files (stored as JSON paths)
    template_files = models.JSONField(default=dict, verbose_name='فایل‌های قالب')
    # Example: {'homepage': 'themes/modern/homepage.html', 'product': 'themes/modern/product.html'}
    
    class Meta:
        verbose_name = 'قالب فروشگاه'
        verbose_name_plural = 'قالب‌های فروشگاه'
        ordering = ['-install_count', 'name_fa']
        indexes = [
            models.Index(fields=['category', 'is_active']),
            models.Index(fields=['layout_type']),
            models.Index(fields=['is_premium']),
            models.Index(fields=['-install_count']),
            models.Index(fields=['-rating_average']),
        ]
    
    def __str__(self):
        return self.name_fa
    
    def get_suggested_themes(self, store_category):
        """
        Get suggested themes based on store category
        Product requirement: "suggestions based on type of product is also shown (owner has entered this data in request form)"
        """
        return StoreTheme.objects.filter(
            category=store_category,
            is_active=True
        ).order_by('-rating_average', '-install_count')
    
    def increment_install_count(self):
        """Increment install count when theme is applied"""
        self.install_count += 1
        self.save(update_fields=['install_count'])


class StoreThemeCustomization(TimestampMixin):
    """
    Store-specific theme customizations
    Product requirement: "they can also change it later very simple"
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    store = models.OneToOneField(
        Store, 
        on_delete=models.CASCADE, 
        related_name='theme_customization',
        verbose_name='فروشگاه'
    )
    theme = models.ForeignKey(StoreTheme, on_delete=models.CASCADE, verbose_name='قالب')
    
    # Color Customizations
    custom_primary_color = models.CharField(max_length=7, blank=True, verbose_name='رنگ اصلی سفارشی')
    custom_secondary_color = models.CharField(max_length=7, blank=True, verbose_name='رنگ فرعی سفارشی')
    custom_accent_color = models.CharField(max_length=7, blank=True, verbose_name='رنگ تاکیدی سفارشی')
    
    # Layout Customizations
    custom_layout = models.CharField(max_length=20, blank=True, verbose_name='چیدمان سفارشی')
    show_breadcrumbs = models.BooleanField(default=True, verbose_name='نمایش مسیر')
    show_search_bar = models.BooleanField(default=True, verbose_name='نمایش نوار جستجو')
    show_social_links = models.BooleanField(default=True, verbose_name='نمایش لینک‌های اجتماعی')
    
    # Homepage Customizations
    hero_section_enabled = models.BooleanField(default=True, verbose_name='بخش هیرو فعال')
    featured_products_count = models.PositiveIntegerField(default=8, verbose_name='تعداد محصولات ویژه')
    show_categories_grid = models.BooleanField(default=True, verbose_name='نمایش شبکه دسته‌بندی‌ها')
    show_testimonials = models.BooleanField(default=True, verbose_name='نمایش نظرات مشتریان')
    
    # Product Page Customizations
    product_image_zoom = models.BooleanField(default=True, verbose_name='زوم تصویر محصول')
    show_related_products = models.BooleanField(default=True, verbose_name='نمایش محصولات مرتبط')
    enable_product_reviews = models.BooleanField(default=True, verbose_name='فعال‌سازی نظرات محصول')
    
    # Custom CSS
    custom_css = models.TextField(blank=True, verbose_name='CSS سفارشی')
    
    # Custom JavaScript
    custom_js = models.TextField(blank=True, verbose_name='JavaScript سفارشی')
    
    # Font Settings
    primary_font = models.CharField(
        max_length=50, 
        default='IRANSans',
        verbose_name='فونت اصلی'
    )
    secondary_font = models.CharField(
        max_length=50, 
        default='IRANSans',
        verbose_name='فونت فرعی'
    )
    
    # Advanced Settings
    settings = models.JSONField(default=dict, verbose_name='تنظیمات پیشرفته')
    
    class Meta:
        verbose_name = 'سفارشی‌سازی قالب'
        verbose_name_plural = 'سفارشی‌سازی‌های قالب'
    
    def __str__(self):
        return f"{self.store.name_fa} - {self.theme.name_fa}"
    
    def get_effective_colors(self):
        """Get effective colors with fallback to theme defaults"""
        return {
            'primary': self.custom_primary_color or self.theme.primary_color,
            'secondary': self.custom_secondary_color or self.theme.secondary_color,
            'accent': self.custom_accent_color or self.theme.accent_color,
        }
    
    def generate_css_variables(self):
        """Generate CSS variables for theme customization"""
        colors = self.get_effective_colors()
        return f"""
        :root {{
            --color-primary: {colors['primary']};
            --color-secondary: {colors['secondary']};
            --color-accent: {colors['accent']};
            --font-primary: '{self.primary_font}', 'IRANSans', sans-serif;
            --font-secondary: '{self.secondary_font}', 'IRANSans', sans-serif;
        }}
        {self.custom_css}
        """


class ThemeRating(TimestampMixin):
    """Theme ratings by store owners"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    theme = models.ForeignKey(StoreTheme, on_delete=models.CASCADE, related_name='ratings')
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    
    rating = models.PositiveIntegerField(
        choices=[(i, i) for i in range(1, 6)],  # 1-5 stars
        verbose_name='امتیاز'
    )
    review = models.TextField(blank=True, verbose_name='نظر')
    
    class Meta:
        unique_together = ['theme', 'store']
        verbose_name = 'امتیاز قالب'
        verbose_name_plural = 'امتیازات قالب'
    
    def __str__(self):
        return f"{self.theme.name_fa} - {self.rating} ستاره"


class ThemeTemplate(models.Model):
    """
    Template components for themes
    """
    
    COMPONENT_TYPES = [
        ('header', 'هدر'),
        ('footer', 'فوتر'),
        ('homepage', 'صفحه اصلی'),
        ('product_list', 'لیست محصولات'),
        ('product_detail', 'جزئیات محصول'),
        ('cart', 'سبد خرید'),
        ('checkout', 'تسویه حساب'),
        ('user_profile', 'پروفایل کاربر'),
        ('contact', 'تماس با ما'),
        ('about', 'درباره ما'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    theme = models.ForeignKey(StoreTheme, on_delete=models.CASCADE, related_name='templates')
    component_type = models.CharField(max_length=20, choices=COMPONENT_TYPES, verbose_name='نوع کامپوننت')
    
    # Template Content
    html_content = models.TextField(verbose_name='محتوای HTML')
    css_content = models.TextField(blank=True, verbose_name='محتوای CSS')
    js_content = models.TextField(blank=True, verbose_name='محتوای JavaScript')
    
    # Template Variables (for dynamic content)
    variables = models.JSONField(default=dict, verbose_name='متغیرهای قالب')
    
    # Version Control
    version = models.CharField(max_length=10, default='1.0', verbose_name='نسخه')
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    
    class Meta:
        unique_together = ['theme', 'component_type']
        verbose_name = 'قالب کامپوننت'
        verbose_name_plural = 'قالب‌های کامپوننت'
    
    def __str__(self):
        return f"{self.theme.name_fa} - {self.get_component_type_display()}"


# Helper functions for theme management
def get_recommended_themes_for_store(store):
    """
    Get recommended themes based on store category and characteristics
    Product requirement: "suggestions based on type of product is also shown"
    """
    # Determine store category from products or store type
    store_category = getattr(store, 'store_type', 'general')
    
    # Get themes for this category
    category_themes = StoreTheme.objects.filter(
        category=store_category,
        is_active=True
    ).order_by('-rating_average', '-install_count')[:6]
    
    # If not enough category-specific themes, add general themes
    if category_themes.count() < 3:
        general_themes = StoreTheme.objects.filter(
            category='general',
            is_active=True
        ).exclude(
            id__in=category_themes.values_list('id', flat=True)
        ).order_by('-rating_average', '-install_count')[:3]
        
        return list(category_themes) + list(general_themes)
    
    return category_themes


def apply_theme_to_store(store, theme):
    """Apply a theme to a store"""
    customization, created = StoreThemeCustomization.objects.get_or_create(
        store=store,
        defaults={'theme': theme}
    )
    
    if not created:
        customization.theme = theme
        customization.save()
    
    # Increment theme install count
    theme.increment_install_count()
    
    return customization


# Signal handlers
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

@receiver(post_save, sender=ThemeRating)
def update_theme_rating(sender, instance, created, **kwargs):
    """Update theme's average rating when new rating is added"""
    theme = instance.theme
    ratings = theme.ratings.all()
    
    if ratings.exists():
        average = sum(r.rating for r in ratings) / ratings.count()
        theme.rating_average = round(average, 2)
        theme.rating_count = ratings.count()
        theme.save(update_fields=['rating_average', 'rating_count'])

@receiver(post_delete, sender=ThemeRating)
def update_theme_rating_on_delete(sender, instance, **kwargs):
    """Update theme's average rating when rating is deleted"""
    theme = instance.theme
    ratings = theme.ratings.all()
    
    if ratings.exists():
        average = sum(r.rating for r in ratings) / ratings.count()
        theme.rating_average = round(average, 2)
        theme.rating_count = ratings.count()
    else:
        theme.rating_average = 0
        theme.rating_count = 0
    
    theme.save(update_fields=['rating_average', 'rating_count'])
