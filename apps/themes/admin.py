from django.contrib import admin
from django.utils.html import format_html
from .models import ThemeCategory, Theme, StoreTheme, ThemeRating


@admin.register(ThemeCategory)
class ThemeCategoryAdmin(admin.ModelAdmin):
    list_display = ['name_fa', 'name', 'category_type', 'display_order', 'is_active']
    list_filter = ['category_type', 'is_active']
    search_fields = ['name', 'name_fa']
    ordering = ['display_order', 'name_fa']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Theme)
class ThemeAdmin(admin.ModelAdmin):
    list_display = [
        'name_fa', 'category', 'theme_type', 'price', 'usage_count', 
        'rating_display', 'is_featured', 'is_active'
    ]
    list_filter = ['category', 'theme_type', 'is_featured', 'is_active']
    search_fields = ['name', 'name_fa', 'description']
    ordering = ['-is_featured', '-usage_count']
    prepopulated_fields = {'slug': ('name',)}
    
    fieldsets = (
        ('اطلاعات پایه', {
            'fields': ('name', 'name_fa', 'slug', 'description', 'version', 'category')
        }),
        ('نوع و سازگاری', {
            'fields': ('theme_type', 'compatibility', 'price')
        }),
        ('رسانه', {
            'fields': ('preview_image', 'demo_url')
        }),
        ('تنظیمات فنی', {
            'fields': ('template_files', 'css_variables', 'js_config'),
            'classes': ('collapse',)
        }),
        ('شخصی‌سازی', {
            'fields': ('customizable_colors', 'customizable_fonts', 'layout_options'),
            'classes': ('collapse',)
        }),
        ('وضعیت', {
            'fields': ('is_active', 'is_featured')
        }),
        ('آمار', {
            'fields': ('download_count', 'usage_count', 'rating_average', 'rating_count'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['download_count', 'usage_count', 'rating_average', 'rating_count']
    
    def rating_display(self, obj):
        if obj.rating_count > 0:
            stars = '★' * int(obj.rating_average) + '☆' * (5 - int(obj.rating_average))
            return format_html(
                '<span title="{} امتیاز از {} نفر">{}</span>',
                obj.rating_average,
                obj.rating_count,
                stars
            )
        return '-'
    rating_display.short_description = 'امتیاز'


@admin.register(StoreTheme)
class StoreThemeAdmin(admin.ModelAdmin):
    list_display = ['store', 'theme', 'is_active', 'applied_at']
    list_filter = ['is_active', 'theme', 'applied_at']
    search_fields = ['store__name', 'theme__name_fa']
    ordering = ['-applied_at']
    
    fieldsets = (
        ('اطلاعات پایه', {
            'fields': ('store', 'theme', 'is_active')
        }),
        ('شخصی‌سازی رنگ‌ها', {
            'fields': ('custom_colors',),
            'classes': ('collapse',)
        }),
        ('CSS و JS سفارشی', {
            'fields': ('custom_css', 'custom_js'),
            'classes': ('collapse',)
        }),
        ('تنظیمات چیدمان', {
            'fields': ('layout_config', 'font_selections'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ThemeRating)
class ThemeRatingAdmin(admin.ModelAdmin):
    list_display = ['theme', 'store', 'rating', 'is_approved', 'created_at']
    list_filter = ['rating', 'is_approved', 'created_at']
    search_fields = ['theme__name_fa', 'store__name', 'review']
    ordering = ['-created_at']
    
    actions = ['approve_ratings', 'disapprove_ratings']
    
    def approve_ratings(self, request, queryset):
        updated = queryset.update(is_approved=True)
        self.message_user(request, f'{updated} امتیاز تایید شد.')
    approve_ratings.short_description = 'تایید امتیازات انتخاب شده'
    
    def disapprove_ratings(self, request, queryset):
        updated = queryset.update(is_approved=False)
        self.message_user(request, f'{updated} امتیاز رد شد.')
    disapprove_ratings.short_description = 'رد امتیازات انتخاب شده'
