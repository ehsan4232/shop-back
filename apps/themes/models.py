from django.db import models
from apps.core.mixins import StoreOwnedMixin, TimestampMixin
import uuid


class Theme(TimestampMixin):
    """
    Website themes for store customization
    Product description: "various fancy and modern designs and layouts and themes for store owners to choose from"
    """
    THEME_TYPES = [
        ('minimal', 'مینیمال'),
        ('modern', 'مدرن'),
        ('classic', 'کلاسیک'),
        ('elegant', 'شیک'),
        ('bold', 'پررنگ'),
        ('business', 'تجاری'),
        ('creative', 'خلاقانه'),
    ]
    
    LAYOUT_TYPES = [
        ('grid', 'شبکه‌ای'),
        ('list', 'لیستی'),
        ('masonry', 'آجری'),
        ('carousel', 'کاروسل'),
        ('magazine', 'مجله‌ای'),
    ]
    
    COLOR_SCHEMES = [
        ('red_blue_white', 'قرمز آبی سفید'),
        ('blue_white', 'آبی سفید'),
        ('dark_elegant', 'تیره شیک'),
        ('warm_earth', 'زمینی گرم'),
        ('cool_modern', 'مدرن سرد'),
        ('vibrant_pop', 'رنگارنگ'),
        ('custom', 'سفارشی'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Basic information
    name = models.CharField(max_length=100, verbose_name='نام قالب')
    name_fa = models.CharField(max_length=100, verbose_name='نام فارسی')
    description = models.TextField(verbose_name='توضیحات')
    
    # Theme properties
    theme_type = models.CharField(max_length=20, choices=THEME_TYPES, verbose_name='نوع قالب')
    layout_type = models.CharField(max_length=20, choices=LAYOUT_TYPES, verbose_name='نوع چیدمان')
    color_scheme = models.CharField(max_length=20, choices=COLOR_SCHEMES, default='red_blue_white', verbose_name='طرح رنگی')
    
    # Design assets
    preview_image = models.ImageField(upload_to='themes/previews/', verbose_name='تصویر پیش‌نمایش')
    thumbnail = models.ImageField(upload_to='themes/thumbnails/', verbose_name='تصویر کوچک')
    demo_url = models.URLField(blank=True, verbose_name='لینک دمو')
    
    # CSS and templates
    css_file = models.FileField(upload_to='themes/css/', verbose_name='فایل CSS')
    template_data = models.JSONField(default=dict, verbose_name='داده‌های قالب')
    
    # Customization options
    customizable_colors = models.JSONField(default=list, verbose_name='رنگ‌های قابل تغییر')
    customizable_fonts = models.JSONField(default=list, verbose_name='فونت‌های قابل تغییر')
    layout_options = models.JSONField(default=dict, verbose_name='گزینه‌های چیدمان')
    
    # Business logic
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    is_premium = models.BooleanField(default=False, verbose_name='پریمیام')
    price = models.DecimalField(max_digits=10, decimal_places=0, default=0, verbose_name='قیمت')
    
    # Usage tracking
    usage_count = models.PositiveIntegerField(default=0, verbose_name='تعداد استفاده')
    rating_average = models.DecimalField(max_digits=3, decimal_places=2, default=0, verbose_name='میانگین امتیاز')
    rating_count = models.PositiveIntegerField(default=0, verbose_name='تعداد امتیاز')
    
    # Product type suggestions based on business
    suggested_for_types = models.JSONField(default=list, verbose_name='پیشنهاد برای انواع کسب‌وکار')
    
    class Meta:
        verbose_name = 'قالب وبسایت'
        verbose_name_plural = 'قالب‌های وبسایت'
        ordering = ['-usage_count', 'name_fa']
        indexes = [
            models.Index(fields=['theme_type', 'is_active']),
            models.Index(fields=['is_premium', 'price']),
            models.Index(fields=['usage_count']),
            models.Index(fields=['rating_average']),
        ]
    
    def __str__(self):
        return self.name_fa
    
    def increment_usage(self):
        """Increment usage count when theme is applied"""
        self.usage_count += 1
        self.save(update_fields=['usage_count'])


class StoreTheme(StoreOwnedMixin, TimestampMixin):
    """
    Applied theme configuration for a store
    Product description: "they can also change it later very simple"
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    theme = models.ForeignKey(Theme, on_delete=models.PROTECT, verbose_name='قالب')
    
    # Customizations
    custom_colors = models.JSONField(default=dict, verbose_name='رنگ‌های سفارشی')
    custom_fonts = models.JSONField(default=dict, verbose_name='فونت‌های سفارشی')
    custom_layout = models.JSONField(default=dict, verbose_name='چیدمان سفارشی')
    custom_css = models.TextField(blank=True, verbose_name='CSS سفارشی')
    
    # Logo and branding
    logo = models.ImageField(upload_to='store_themes/logos/', null=True, blank=True, verbose_name='لوگو')
    favicon = models.ImageField(upload_to='store_themes/favicons/', null=True, blank=True, verbose_name='فاویکون')
    
    # Header and footer
    header_config = models.JSONField(default=dict, verbose_name='تنظیمات هدر')
    footer_config = models.JSONField(default=dict, verbose_name='تنظیمات فوتر')
    
    # Social media links
    social_links = models.JSONField(default=dict, verbose_name='لینک‌های شبکه اجتماعی')
    
    # SEO and meta
    meta_title = models.CharField(max_length=60, blank=True, verbose_name='عنوان متا')
    meta_description = models.CharField(max_length=160, blank=True, verbose_name='توضیح متا')
    meta_keywords = models.CharField(max_length=255, blank=True, verbose_name='کلمات کلیدی')
    
    # Status
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    is_published = models.BooleanField(default=False, verbose_name='منتشر شده')
    
    # Backup of previous theme
    previous_theme_data = models.JSONField(default=dict, verbose_name='داده‌های قالب قبلی')
    
    class Meta:
        verbose_name = 'قالب فروشگاه'
        verbose_name_plural = 'قالب‌های فروشگاه'
        unique_together = ['store']
        indexes = [
            models.Index(fields=['store', 'is_active']),
            models.Index(fields=['theme', 'is_published']),
        ]
    
    def __str__(self):
        return f"{self.store.name} - {self.theme.name_fa}"
    
    def apply_theme(self, theme, custom_options=None):
        """
        Apply new theme with customizations
        Product description: "they can also change it later very simple"
        """
        # Backup current theme
        self.previous_theme_data = {
            'theme_id': str(self.theme.id) if self.theme else None,
            'custom_colors': self.custom_colors,
            'custom_fonts': self.custom_fonts,
            'custom_layout': self.custom_layout,
            'applied_at': self.updated_at.isoformat() if self.updated_at else None
        }
        
        # Apply new theme
        self.theme = theme
        if custom_options:
            self.custom_colors.update(custom_options.get('colors', {}))
            self.custom_fonts.update(custom_options.get('fonts', {}))
            self.custom_layout.update(custom_options.get('layout', {}))
        
        self.save()
        
        # Update theme usage
        theme.increment_usage()
    
    def revert_to_previous_theme(self):
        """Revert to previous theme configuration"""
        if self.previous_theme_data.get('theme_id'):
            try:
                previous_theme = Theme.objects.get(id=self.previous_theme_data['theme_id'])
                self.theme = previous_theme
                self.custom_colors = self.previous_theme_data.get('custom_colors', {})
                self.custom_fonts = self.previous_theme_data.get('custom_fonts', {})
                self.custom_layout = self.previous_theme_data.get('custom_layout', {})
                self.save()
                return True
            except Theme.DoesNotExist:
                pass
        return False
    
    def get_compiled_css(self):
        """Get complete CSS for the store with customizations"""
        base_css = self.theme.css_file.read() if self.theme.css_file else ""
        
        # Apply color customizations
        css_variables = []
        for key, value in self.custom_colors.items():
            css_variables.append(f"--color-{key}: {value};")
        
        # Apply font customizations  
        for key, value in self.custom_fonts.items():
            css_variables.append(f"--font-{key}: {value};")
        
        custom_css_vars = ":root {\n" + "\n".join(css_variables) + "\n}"
        
        return f"{custom_css_vars}\n{base_css}\n{self.custom_css}"


class ThemeReview(StoreOwnedMixin, TimestampMixin):
    """Theme reviews from store owners"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    theme = models.ForeignKey(Theme, on_delete=models.CASCADE, related_name='reviews')
    rating = models.PositiveIntegerField(choices=[(i, i) for i in range(1, 6)], verbose_name='امتیاز')
    review_text = models.TextField(blank=True, verbose_name='متن نظر')
    
    # Review metadata
    is_approved = models.BooleanField(default=False, verbose_name='تأیید شده')
    is_featured = models.BooleanField(default=False, verbose_name='نظر ویژه')
    
    class Meta:
        verbose_name = 'نظر قالب'
        verbose_name_plural = 'نظرات قالب'
        unique_together = ['store', 'theme']
        indexes = [
            models.Index(fields=['theme', 'rating']),
            models.Index(fields=['is_approved', 'is_featured']),
        ]
    
    def __str__(self):
        return f"{self.store.name} - {self.theme.name_fa} ({self.rating}⭐)"


# Signal handlers for theme usage tracking
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

@receiver(post_save, sender=ThemeReview)
def update_theme_rating(sender, instance, **kwargs):
    """Update theme rating when review is added/updated"""
    theme = instance.theme
    reviews = theme.reviews.filter(is_approved=True)
    
    if reviews.exists():
        theme.rating_average = reviews.aggregate(
            avg_rating=models.Avg('rating')
        )['avg_rating']
        theme.rating_count = reviews.count()
        theme.save(update_fields=['rating_average', 'rating_count'])

@receiver(post_delete, sender=ThemeReview)
def update_theme_rating_on_delete(sender, instance, **kwargs):
    """Update theme rating when review is deleted"""
    theme = instance.theme
    reviews = theme.reviews.filter(is_approved=True)
    
    if reviews.exists():
        theme.rating_average = reviews.aggregate(
            avg_rating=models.Avg('rating')
        )['avg_rating']
        theme.rating_count = reviews.count()
    else:
        theme.rating_average = 0
        theme.rating_count = 0
    
    theme.save(update_fields=['rating_average', 'rating_count'])