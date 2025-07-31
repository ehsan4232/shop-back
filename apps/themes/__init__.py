from django.db import models
from django.core.cache import cache
from apps.core.mixins import TimestampMixin, StoreOwnedMixin
import uuid
import json


class StoreTheme(StoreOwnedMixin, TimestampMixin):
    """
    Store themes for customizing store websites
    Product requirement: "fancy and modern designs and layouts and themes"
    """
    
    THEME_TYPES = [
        ('minimal', 'مینیمال'),
        ('modern', 'مدرن'),
        ('classic', 'کلاسیک'),
        ('colorful', 'رنگارنگ'),
        ('dark', 'تیره'),
        ('professional', 'حرفه‌ای'),
        ('creative', 'خلاقانه'),
        ('elegant', 'شیک'),
    ]
    
    BUSINESS_CATEGORIES = [
        ('fashion', 'پوشاک و مد'),
        ('electronics', 'الکترونیک'),
        ('jewelry', 'جواهرات'),
        ('pets', 'حیوانات خانگی'),
        ('food', 'مواد غذایی'),
        ('beauty', 'آرایشی و بهداشتی'),
        ('sports', 'ورزشی'),
        ('books', 'کتاب و فرهنگ'),
        ('home', 'خانه و آشپزخانه'),
        ('general', 'عمومی'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Basic info
    name = models.CharField(max_length=100, verbose_name='نام قالب')
    name_fa = models.CharField(max_length=100, verbose_name='نام فارسی')
    description = models.TextField(blank=True, verbose_name='توضیحات')
    
    # Theme properties
    theme_type = models.CharField(max_length=20, choices=THEME_TYPES, verbose_name='نوع قالب')
    business_category = models.CharField(
        max_length=20, 
        choices=BUSINESS_CATEGORIES, 
        default='general',
        verbose_name='دسته کسب‌وکار'
    )
    
    # Visual properties
    primary_color = models.CharField(max_length=7, default='#007bff', verbose_name='رنگ اصلی')
    secondary_color = models.CharField(max_length=7, default='#6c757d', verbose_name='رنگ فرعی')
    accent_color = models.CharField(max_length=7, default='#28a745', verbose_name='رنگ تاکیدی')
    background_color = models.CharField(max_length=7, default='#ffffff', verbose_name='رنگ پس‌زمینه')
    text_color = models.CharField(max_length=7, default='#212529', verbose_name='رنگ متن')
    
    # Typography
    heading_font = models.CharField(
        max_length=50, 
        default='IRANSans',
        verbose_name='فونت عناوین'
    )
    body_font = models.CharField(
        max_length=50, 
        default='IRANSans',
        verbose_name='فونت متن'
    )
    
    # Layout settings
    layout_config = models.JSONField(default=dict, verbose_name='تنظیمات چیدمان')
    
    # Theme files and assets
    css_file = models.TextField(blank=True, verbose_name='فایل CSS')
    preview_image = models.ImageField(
        upload_to='theme_previews/', 
        null=True, 
        blank=True, 
        verbose_name='تصویر پیش‌نمایش'
    )
    
    # Status
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    is_premium = models.BooleanField(default=False, verbose_name='پریمیوم')
    is_public = models.BooleanField(default=True, verbose_name='عمومی')
    
    # Analytics
    usage_count = models.PositiveIntegerField(default=0, verbose_name='تعداد استفاده')
    rating_average = models.DecimalField(
        max_digits=3, 
        decimal_places=2, 
        default=0, 
        verbose_name='میانگین امتیاز'
    )
    rating_count = models.PositiveIntegerField(default=0, verbose_name='تعداد امتیاز')
    
    class Meta:
        verbose_name = 'قالب فروشگاه'
        verbose_name_plural = 'قالب‌های فروشگاه'
        ordering = ['-usage_count', 'name_fa']
        indexes = [
            models.Index(fields=['store', 'is_active']),
            models.Index(fields=['theme_type', 'business_category']),
            models.Index(fields=['is_public', 'is_active']),
            models.Index(fields=['usage_count']),
            models.Index(fields=['rating_average']),
        ]
    
    def __str__(self):
        return f"{self.name_fa} ({self.theme_type})"
    
    def get_css_variables(self):
        """Generate CSS variables for theme customization"""
        return {
            '--primary-color': self.primary_color,
            '--secondary-color': self.secondary_color,
            '--accent-color': self.accent_color,
            '--background-color': self.background_color,
            '--text-color': self.text_color,
            '--heading-font': self.heading_font,
            '--body-font': self.body_font,
        }
    
    def get_compiled_css(self):
        """Get compiled CSS with theme variables"""
        css_variables = self.get_css_variables()
        css_vars_string = '\n'.join([f'{key}: {value};' for key, value in css_variables.items()])
        
        base_css = f"""
        :root {{
            {css_vars_string}
        }}
        {self.css_file}
        """
        return base_css
    
    def increment_usage(self):
        """Increment usage count"""
        self.usage_count += 1
        self.save(update_fields=['usage_count'])


class StoreCustomization(StoreOwnedMixin, TimestampMixin):
    """
    Store-specific theme customizations
    Product requirement: "they can also change it later very simple"
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    theme = models.ForeignKey(
        StoreTheme, 
        on_delete=models.CASCADE, 
        related_name='customizations'
    )
    
    # Custom colors (override theme defaults)
    custom_primary_color = models.CharField(
        max_length=7, 
        null=True, 
        blank=True, 
        verbose_name='رنگ اصلی سفارشی'
    )
    custom_secondary_color = models.CharField(
        max_length=7, 
        null=True, 
        blank=True, 
        verbose_name='رنگ فرعی سفارشی'
    )
    custom_accent_color = models.CharField(
        max_length=7, 
        null=True, 
        blank=True, 
        verbose_name='رنگ تاکیدی سفارشی'
    )
    
    # Custom fonts
    custom_heading_font = models.CharField(
        max_length=50, 
        null=True, 
        blank=True, 
        verbose_name='فونت عناوین سفارشی'
    )
    custom_body_font = models.CharField(
        max_length=50, 
        null=True, 
        blank=True, 
        verbose_name='فونت متن سفارشی'
    )
    
    # Logo and branding
    logo = models.ImageField(
        upload_to='store_logos/', 
        null=True, 
        blank=True, 
        verbose_name='لوگو'
    )
    favicon = models.ImageField(
        upload_to='store_favicons/', 
        null=True, 
        blank=True, 
        verbose_name='فیویکان'
    )
    
    # Custom CSS
    custom_css = models.TextField(blank=True, verbose_name='CSS سفارشی')
    
    # Layout customizations
    layout_customizations = models.JSONField(default=dict, verbose_name='تنظیمات چیدمان سفارشی')
    
    # Header/Footer customizations
    custom_header = models.TextField(blank=True, verbose_name='هدر سفارشی')
    custom_footer = models.TextField(blank=True, verbose_name='فوتر سفارشی')
    
    # SEO customizations
    custom_meta_title = models.CharField(
        max_length=60, 
        blank=True, 
        verbose_name='عنوان سفارشی صفحه'
    )
    custom_meta_description = models.CharField(
        max_length=160, 
        blank=True, 
        verbose_name='توضیحات سفارشی صفحه'
    )
    
    # Status
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    
    class Meta:
        verbose_name = 'شخصی‌سازی فروشگاه'
        verbose_name_plural = 'شخصی‌سازی‌های فروشگاه'
        unique_together = ['store']
        indexes = [
            models.Index(fields=['store', 'is_active']),
            models.Index(fields=['theme']),
        ]
    
    def __str__(self):
        return f"شخصی‌سازی {self.store.name}"
    
    def get_effective_colors(self):
        """Get effective colors with custom overrides"""
        return {
            'primary': self.custom_primary_color or self.theme.primary_color,
            'secondary': self.custom_secondary_color or self.theme.secondary_color,
            'accent': self.custom_accent_color or self.theme.accent_color,
            'background': self.theme.background_color,
            'text': self.theme.text_color,
        }
    
    def get_effective_fonts(self):
        """Get effective fonts with custom overrides"""
        return {
            'heading': self.custom_heading_font or self.theme.heading_font,
            'body': self.custom_body_font or self.theme.body_font,
        }
    
    def get_compiled_theme_css(self):
        """Get complete compiled CSS for the store"""
        colors = self.get_effective_colors()
        fonts = self.get_effective_fonts()
        
        css_variables = {
            '--primary-color': colors['primary'],
            '--secondary-color': colors['secondary'],
            '--accent-color': colors['accent'],
            '--background-color': colors['background'],
            '--text-color': colors['text'],
            '--heading-font': fonts['heading'],
            '--body-font': fonts['body'],
        }
        
        css_vars_string = '\n'.join([f'{key}: {value};' for key, value in css_variables.items()])
        
        compiled_css = f"""
        :root {{
            {css_vars_string}
        }}
        
        /* Base theme CSS */
        {self.theme.css_file}
        
        /* Custom CSS */
        {self.custom_css}
        """
        
        return compiled_css


class ThemeComponent(TimestampMixin):
    """
    Reusable theme components
    """
    
    COMPONENT_TYPES = [
        ('header', 'هدر'),
        ('footer', 'فوتر'),
        ('sidebar', 'نوار کناری'),
        ('product_card', 'کارت محصول'),
        ('hero_section', 'بخش قهرمان'),
        ('testimonial', 'نظرات'),
        ('contact_form', 'فرم تماس'),
        ('newsletter', 'خبرنامه'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    name = models.CharField(max_length=100, verbose_name='نام کامپوننت')
    component_type = models.CharField(max_length=20, choices=COMPONENT_TYPES, verbose_name='نوع کامپوننت')
    
    # Component code
    html_template = models.TextField(verbose_name='قالب HTML')
    css_styles = models.TextField(blank=True, verbose_name='استایل‌های CSS')
    javascript_code = models.TextField(blank=True, verbose_name='کد JavaScript')
    
    # Configuration
    config_schema = models.JSONField(default=dict, verbose_name='طرح تنظیمات')
    default_config = models.JSONField(default=dict, verbose_name='تنظیمات پیش‌فرض')
    
    # Preview
    preview_image = models.ImageField(
        upload_to='component_previews/', 
        null=True, 
        blank=True, 
        verbose_name='تصویر پیش‌نمایش'
    )
    
    # Status
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    usage_count = models.PositiveIntegerField(default=0, verbose_name='تعداد استفاده')
    
    class Meta:
        verbose_name = 'کامپوننت قالب'
        verbose_name_plural = 'کامپوننت‌های قالب'
        ordering = ['component_type', 'name']
        indexes = [
            models.Index(fields=['component_type', 'is_active']),
            models.Index(fields=['usage_count']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_component_type_display()})"


class StoreThemeRating(StoreOwnedMixin, TimestampMixin):
    """Theme ratings by store owners"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    theme = models.ForeignKey(
        StoreTheme, 
        on_delete=models.CASCADE, 
        related_name='ratings'
    )
    rating = models.PositiveIntegerField(verbose_name='امتیاز (1-5)')
    review = models.TextField(blank=True, verbose_name='نظر')
    
    class Meta:
        verbose_name = 'امتیاز قالب'
        verbose_name_plural = 'امتیازات قالب'
        unique_together = ['store', 'theme']
        indexes = [
            models.Index(fields=['theme', 'rating']),
        ]
    
    def __str__(self):
        return f"امتیاز {self.rating} برای {self.theme.name_fa}"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update theme rating average
        self.theme.rating_count = self.theme.ratings.count()
        self.theme.rating_average = self.theme.ratings.aggregate(
            avg_rating=models.Avg('rating')
        )['avg_rating'] or 0
        self.theme.save(update_fields=['rating_count', 'rating_average'])


# Signal handlers for cache management
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

@receiver([post_save, post_delete], sender=StoreCustomization)
def clear_theme_cache(sender, instance, **kwargs):
    """Clear theme cache when customization changes"""
    cache_key = f"store_theme_{instance.store.id}"
    cache.delete(cache_key)

@receiver([post_save, post_delete], sender=StoreTheme)
def clear_all_theme_cache(sender, instance, **kwargs):
    """Clear all theme-related cache when theme changes"""
    # Clear cache for all stores using this theme
    for customization in instance.customizations.all():
        cache_key = f"store_theme_{customization.store.id}"
        cache.delete(cache_key)
