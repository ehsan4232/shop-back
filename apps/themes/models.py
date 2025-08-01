from django.db import models
from django.core.exceptions import ValidationError
from apps.core.mixins import TimestampMixin, SlugMixin, StoreOwnedMixin
import uuid
import json


class ThemeCategory(TimestampMixin, SlugMixin):
    """Theme categories for better organization"""
    
    CATEGORY_TYPES = [
        ('business', 'کسب و کار'),
        ('fashion', 'مد و پوشاک'),
        ('food', 'غذا و رستوران'),
        ('electronics', 'الکترونیک'),
        ('beauty', 'زیبایی و آرایشی'),
        ('jewelry', 'طلا و جواهر'),
        ('services', 'خدمات'),
        ('minimal', 'مینیمال'),
        ('modern', 'مدرن'),
        ('classic', 'کلاسیک'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    name = models.CharField(max_length=100, unique=True, verbose_name='نام انگلیسی')
    name_fa = models.CharField(max_length=100, verbose_name='نام فارسی')
    category_type = models.CharField(max_length=20, choices=CATEGORY_TYPES, verbose_name='نوع دسته‌بندی')
    description = models.TextField(blank=True, verbose_name='توضیحات')
    icon = models.CharField(max_length=50, blank=True, verbose_name='آیکون')
    
    display_order = models.PositiveIntegerField(default=0, verbose_name='ترتیب نمایش')
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    
    class Meta:
        verbose_name = 'دسته‌بندی قالب'
        verbose_name_plural = 'دسته‌بندی‌های قالب'
        ordering = ['display_order', 'name_fa']
        indexes = [
            models.Index(fields=['category_type', 'is_active']),
            models.Index(fields=['display_order']),
        ]
    
    def __str__(self):
        return self.name_fa


class Theme(TimestampMixin, SlugMixin):
    """
    Theme templates for store websites
    Product requirement: "various fancy and modern designs and layouts and themes"
    """
    
    THEME_TYPES = [
        ('free', 'رایگان'),
        ('premium', 'پریمیوم'),
        ('custom', 'سفارشی'),
    ]
    
    COMPATIBILITY = [
        ('all', 'همه محصولات'),
        ('simple', 'محصولات ساده'),
        ('variable', 'محصولات متغیر'),
        ('digital', 'محصولات دیجیتال'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Basic info
    name = models.CharField(max_length=100, unique=True, verbose_name='نام قالب')
    name_fa = models.CharField(max_length=100, verbose_name='نام فارسی')
    description = models.TextField(verbose_name='توضیحات')
    version = models.CharField(max_length=20, default='1.0.0', verbose_name='نسخه')
    
    # Categorization
    category = models.ForeignKey(ThemeCategory, on_delete=models.CASCADE, related_name='themes')
    theme_type = models.CharField(max_length=20, choices=THEME_TYPES, default='free', verbose_name='نوع قالب')
    compatibility = models.CharField(max_length=20, choices=COMPATIBILITY, default='all', verbose_name='سازگاری')
    
    # Media
    preview_image = models.ImageField(upload_to='themes/previews/', verbose_name='تصویر پیش‌نمایش')
    demo_url = models.URLField(blank=True, verbose_name='لینک دمو')
    
    # Technical details
    template_files = models.JSONField(default=dict, verbose_name='فایل‌های قالب')
    css_variables = models.JSONField(default=dict, verbose_name='متغیرهای CSS')
    js_config = models.JSONField(default=dict, verbose_name='تنظیمات JavaScript')
    
    # Customization options
    customizable_colors = models.JSONField(default=list, verbose_name='رنگ‌های قابل تغییر')
    customizable_fonts = models.JSONField(default=list, verbose_name='فونت‌های قابل تغییر')
    layout_options = models.JSONField(default=dict, verbose_name='گزینه‌های چیدمان')
    
    # Pricing
    price = models.DecimalField(max_digits=10, decimal_places=0, default=0, verbose_name='قیمت (تومان)')
    
    # Status
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    is_featured = models.BooleanField(default=False, verbose_name='قالب ویژه')
    
    # Analytics
    download_count = models.PositiveIntegerField(default=0, verbose_name='تعداد دانلود')
    usage_count = models.PositiveIntegerField(default=0, verbose_name='تعداد استفاده')
    rating_average = models.DecimalField(max_digits=3, decimal_places=2, default=0, verbose_name='میانگین امتیاز')
    rating_count = models.PositiveIntegerField(default=0, verbose_name='تعداد امتیاز')
    
    class Meta:
        verbose_name = 'قالب'
        verbose_name_plural = 'قالب‌ها'
        ordering = ['-is_featured', '-usage_count', 'name_fa']
        indexes = [
            models.Index(fields=['category', 'is_active']),
            models.Index(fields=['theme_type', 'is_active']),
            models.Index(fields=['is_featured', 'is_active']),
            models.Index(fields=['-usage_count']),
            models.Index(fields=['-rating_average']),
        ]
    
    def __str__(self):
        return self.name_fa
    
    def clean(self):
        """Validate theme configuration"""
        super().clean()
        
        # Validate template files structure
        if self.template_files:
            required_files = ['layout.html', 'product_list.html', 'product_detail.html']
            for file in required_files:
                if file not in self.template_files:
                    raise ValidationError({
                        'template_files': f'فایل {file} اجباری است'
                    })
    
    def get_customization_options(self):
        """Get all customization options for this theme"""
        return {
            'colors': self.customizable_colors,
            'fonts': self.customizable_fonts,
            'layout': self.layout_options,
            'css_variables': self.css_variables,
        }
    
    def increment_usage(self):
        """Increment usage count when theme is applied"""
        self.usage_count += 1
        self.save(update_fields=['usage_count'])
    
    def increment_downloads(self):
        """Increment download count"""
        self.download_count += 1
        self.save(update_fields=['download_count'])


class StoreTheme(StoreOwnedMixin, TimestampMixin):
    """
    Applied theme configuration for a store
    Product requirement: "they can also change it later very simple"
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    theme = models.ForeignKey(Theme, on_delete=models.CASCADE, related_name='store_applications')
    
    # Custom overrides
    custom_colors = models.JSONField(default=dict, verbose_name='رنگ‌های سفارشی')
    custom_css = models.TextField(blank=True, verbose_name='CSS سفارشی')
    custom_js = models.TextField(blank=True, verbose_name='JavaScript سفارشی')
    
    # Layout customizations
    layout_config = models.JSONField(default=dict, verbose_name='تنظیمات چیدمان')
    font_selections = models.JSONField(default=dict, verbose_name='انتخاب فونت‌ها')
    
    # Settings
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    applied_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ اعمال')
    
    class Meta:
        verbose_name = 'قالب فروشگاه'
        verbose_name_plural = 'قالب‌های فروشگاه'
        unique_together = ['store', 'theme']
        indexes = [
            models.Index(fields=['store', 'is_active']),
            models.Index(fields=['theme', 'is_active']),
            models.Index(fields=['-applied_at']),
        ]
    
    def __str__(self):
        return f"{self.store.name} - {self.theme.name_fa}"
    
    def get_compiled_css(self):
        """Get compiled CSS with custom overrides"""
        base_css = self.theme.css_variables
        custom_css = self.custom_css or ""
        
        # Merge base CSS with custom colors
        if self.custom_colors:
            for variable, color in self.custom_colors.items():
                custom_css += f":root {{ --{variable}: {color}; }}\n"
        
        return custom_css
    
    def get_compiled_config(self):
        """Get complete configuration for theme rendering"""
        config = {
            'theme': self.theme.name,
            'version': self.theme.version,
            'template_files': self.theme.template_files,
            'css_variables': {**self.theme.css_variables, **self.custom_colors},
            'js_config': self.theme.js_config,
            'layout_config': {**self.theme.layout_options, **self.layout_config},
            'fonts': self.font_selections,
            'custom_css': self.custom_css,
            'custom_js': self.custom_js,
        }
        return config


class ThemeRating(StoreOwnedMixin, TimestampMixin):
    """Theme ratings and reviews from store owners"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    theme = models.ForeignKey(Theme, on_delete=models.CASCADE, related_name='ratings')
    rating = models.PositiveIntegerField(choices=[(i, i) for i in range(1, 6)], verbose_name='امتیاز')
    review = models.TextField(blank=True, verbose_name='نظر')
    
    is_approved = models.BooleanField(default=False, verbose_name='تایید شده')
    
    class Meta:
        verbose_name = 'امتیاز قالب'
        verbose_name_plural = 'امتیازات قالب'
        unique_together = ['store', 'theme']
        indexes = [
            models.Index(fields=['theme', 'is_approved']),
            models.Index(fields=['rating']),
        ]
    
    def __str__(self):
        return f"{self.theme.name_fa} - {self.rating} ستاره"


# Signal handlers for updating theme statistics
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

@receiver(post_save, sender=ThemeRating)
def update_theme_rating(sender, instance, **kwargs):
    """Update theme rating statistics"""
    theme = instance.theme
    ratings = theme.ratings.filter(is_approved=True)
    
    if ratings.exists():
        theme.rating_average = ratings.aggregate(
            avg=models.Avg('rating')
        )['avg']
        theme.rating_count = ratings.count()
    else:
        theme.rating_average = 0
        theme.rating_count = 0
    
    theme.save(update_fields=['rating_average', 'rating_count'])

@receiver(post_delete, sender=ThemeRating)
def update_theme_rating_on_delete(sender, instance, **kwargs):
    """Update theme rating when rating is deleted"""
    theme = instance.theme
    ratings = theme.ratings.filter(is_approved=True)
    
    if ratings.exists():
        theme.rating_average = ratings.aggregate(
            avg=models.Avg('rating')
        )['avg']
        theme.rating_count = ratings.count()
    else:
        theme.rating_average = 0
        theme.rating_count = 0
    
    theme.save(update_fields=['rating_average', 'rating_count'])

@receiver(post_save, sender=StoreTheme)
def increment_theme_usage(sender, instance, created, **kwargs):
    """Increment theme usage when applied to a store"""
    if created:
        instance.theme.increment_usage()
