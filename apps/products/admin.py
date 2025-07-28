from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Count, Q
from mptt.admin import MPTTModelAdmin
from .models import *

@admin.register(AttributeType)
class AttributeTypeAdmin(admin.ModelAdmin):
    """User-friendly attribute type management"""
    
    list_display = ['name_fa', 'display_type', 'filter_type', 'is_filterable', 'is_variant_creating', 'unit']
    list_filter = ['display_type', 'filter_type', 'is_filterable', 'is_variant_creating']
    search_fields = ['name_fa', 'name']
    
    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('name', 'name_fa', 'display_type', 'filter_type'),
            'description': 'اطلاعات اساسی نوع ویژگی'
        }),
        ('تنظیمات پیشرفته', {
            'fields': ('unit', 'predefined_choices', 'icon', 'help_text'),
            'classes': ('collapse',),
            'description': 'تنظیمات اضافی برای ویژگی'
        }),
        ('رفتار سیستم', {
            'fields': ('is_filterable', 'is_searchable', 'show_in_listing', 'is_variant_creating'),
            'description': 'نحوه نمایش و کارکرد ویژگی در سیستم'
        })
    )

class ProductAttributeInline(admin.TabularInline):
    """Inline for category attributes"""
    model = ProductAttribute
    extra = 0
    fields = ['attribute_type', 'is_required', 'display_order', 'is_inherited']
    readonly_fields = ['is_inherited']

@admin.register(ProductCategory)
class ProductCategoryAdmin(MPTTModelAdmin):
    """Hierarchical category management with inheritance support"""
    
    list_display = [
        'name_fa', 'parent', 'category_type', 'product_count_display', 
        'show_in_menu', 'is_active', 'display_order'
    ]
    list_filter = ['category_type', 'is_active', 'show_in_menu', 'parent']
    search_fields = ['name_fa', 'name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    
    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('name', 'name_fa', 'slug', 'parent', 'category_type', 'description')
        }),
        ('نمایش و ظاهر', {
            'fields': ('icon', 'banner_image', 'display_order', 'show_in_menu', 'is_active'),
            'classes': ('collapse',)
        }),
        ('سئو', {
            'fields': ('meta_title', 'meta_description'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [ProductAttributeInline]
    
    def product_count_display(self, obj):
        """Show product count with link to products"""
        count = obj.product_count_cache
        if count > 0:
            url = reverse('admin:products_product_changelist') + f'?category__id__exact={obj.id}'
            return format_html('<a href="{}" title="مشاهده محصولات">{} محصول</a>', url, count)
        return '0 محصول'
    product_count_display.short_description = 'تعداد محصولات'

@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    """Brand management with product tracking"""
    
    list_display = [
        'name_fa', 'logo_preview', 'product_count_display', 
        'country_of_origin', 'is_featured', 'is_active'
    ]
    list_filter = ['is_featured', 'is_active', 'country_of_origin']
    search_fields = ['name_fa', 'name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    
    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('name', 'name_fa', 'slug', 'logo', 'description')
        }),
        ('جزئیات برند', {
            'fields': ('website', 'country_of_origin'),
            'classes': ('collapse',)
        }),
        ('تنظیمات نمایش', {
            'fields': ('is_featured', 'is_active', 'display_order')
        }),
    )
    
    def logo_preview(self, obj):
        if obj.logo:
            return format_html(
                '<img src="{}" style="width: 50px; height: 50px; object-fit: cover; border-radius: 4px;" />',
                obj.logo.url
            )
        return format_html('<div style="width: 50px; height: 50px; background: #f0f0f0; display: flex; align-items: center; justify-content: center; border-radius: 4px; font-size: 12px;">بدون لوگو</div>')
    logo_preview.short_description = 'لوگو'
    
    def product_count_display(self, obj):
        count = obj.product_count
        if count > 0:
            url = reverse('admin:products_product_changelist') + f'?brand__id__exact={obj.id}'
            return format_html('<a href="{}" title="مشاهده محصولات">{} محصول</a>', url, count)
        return '0 محصول'
    product_count_display.short_description = 'محصولات'

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    """Tag management with usage statistics"""
    
    list_display = ['name_fa', 'tag_type', 'color_preview', 'usage_count', 'is_featured', 'is_filterable']
    list_filter = ['tag_type', 'is_featured', 'is_filterable']
    search_fields = ['name_fa', 'name']
    prepopulated_fields = {'slug': ('name',)}
    
    def color_preview(self, obj):
        return format_html(
            '<div style="width: 30px; height: 20px; background-color: {}; border: 1px solid #ddd; border-radius: 3px; display: inline-block;"></div>',
            obj.color
        )
    color_preview.short_description = 'رنگ'

class ProductAttributeValueInline(admin.TabularInline):
    """Inline for product attribute values"""
    model = ProductAttributeValue
    extra = 0
    fields = ['attribute', 'display_value_readonly', 'value_text', 'value_number', 'color_hex']
    readonly_fields = ['display_value_readonly']
    
    def display_value_readonly(self, obj):
        return obj.display_value if obj else ''
    display_value_readonly.short_description = 'مقدار نمایشی'

class ProductVariantInline(admin.TabularInline):
    """Inline for product variants"""
    model = ProductVariant
    extra = 0
    fields = [
        'sku', 'price', 'stock_quantity', 'weight', 
        'is_active', 'is_default', 'variant_summary'
    ]
    readonly_fields = ['variant_summary']
    
    def variant_summary(self, obj):
        if obj and obj.id:
            return obj.get_attribute_summary()
        return 'جدید'
    variant_summary.short_description = 'ویژگی‌ها'

class ProductImageInline(admin.TabularInline):
    """Inline for product images"""
    model = ProductImage
    extra = 1
    fields = ['image', 'image_preview', 'alt_text', 'is_featured', 'display_order']
    readonly_fields = ['image_preview']
    
    def image_preview(self, obj):
        if obj and obj.image:
            return format_html(
                '<img src="{}" style="width: 100px; height: 100px; object-fit: cover;" />',
                obj.image.url
            )
        return 'بدون تصویر'
    image_preview.short_description = 'پیش‌نمایش'

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """Comprehensive product management with variant support"""
    
    list_display = [
        'name_fa', 'category', 'brand', 'product_type', 
        'price_display', 'stock_status', 'status', 'is_featured'
    ]
    list_filter = [
        'status', 'product_type', 'is_featured', 'category', 'brand',
        ('created_at', admin.DateFieldListFilter),
        'tags'
    ]
    search_fields = ['name_fa', 'name', 'sku', 'description']
    prepopulated_fields = {'slug': ('name',)}
    filter_horizontal = ['tags', 'related_products']
    
    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': (
                'name', 'name_fa', 'slug', 'category', 'brand',
                'product_type', 'description', 'short_description'
            )
        }),
        ('قیمت و موجودی', {
            'fields': ('base_price', 'compare_price', 'sku', 'stock_quantity', 'manage_stock'),
            'description': 'برای محصولات متغیر، قیمت‌ها در انواع محصول تنظیم می‌شوند'
        }),
        ('رسانه', {
            'fields': ('featured_image',),
        }),
        ('محصول دیجیتال', {
            'fields': ('digital_file', 'download_limit', 'download_expiry_days'),
            'classes': ('collapse',),
        }),
        ('سئو', {
            'fields': ('meta_title', 'meta_description'),
            'classes': ('collapse',)
        }),
        ('تنظیمات', {
            'fields': ('status', 'is_featured', 'tags')
        })
    )
    
    inlines = [ProductImageInline, ProductAttributeValueInline, ProductVariantInline]
    
    def price_display(self, obj):
        """Show price or price range"""
        if obj.product_type == 'variable':
            min_price, max_price = obj.get_price_range()
            if min_price == max_price:
                return f'{min_price:,} تومان'
            return f'{min_price:,} - {max_price:,} تومان'
        return f'{obj.base_price:,} تومان'
    price_display.short_description = 'قیمت'
    
    def stock_status(self, obj):
        """Show stock status with colors"""
        if obj.product_type == 'variable':
            total_stock = sum(v.stock_quantity for v in obj.get_variants())
            if total_stock > 10:
                return format_html('<span style="color: green;">موجود ({})</span>', total_stock)
            elif total_stock > 0:
                return format_html('<span style="color: orange;">کم موجود ({})</span>', total_stock)
            else:
                return format_html('<span style="color: red;">ناموجود</span>')
        else:
            if obj.stock_quantity > 10:
                return format_html('<span style="color: green;">موجود ({})</span>', obj.stock_quantity)
            elif obj.stock_quantity > 0:
                return format_html('<span style="color: orange;">کم موجود ({})</span>', obj.stock_quantity)
            else:
                return format_html('<span style="color: red;">ناموجود</span>')
    stock_status.short_description = 'وضعیت موجودی'

@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    """Standalone variant management"""
    
    list_display = ['__str__', 'product', 'price', 'stock_quantity', 'is_active', 'is_default']
    list_filter = ['product__category', 'is_active', 'is_default']
    search_fields = ['sku', 'product__name_fa']
    
    inlines = [ProductAttributeValueInline]

@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    """Product collection management"""
    
    list_display = ['name_fa', 'collection_type', 'is_featured', 'is_active', 'display_order']
    list_filter = ['collection_type', 'is_featured', 'is_active']
    search_fields = ['name_fa', 'name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    filter_horizontal = ['products']
    
    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('name', 'name_fa', 'slug', 'description', 'collection_type')
        }),
        ('قوانین خودکار', {
            'fields': ('auto_rules',),
            'classes': ('collapse',),
            'description': 'فقط برای مجموعه‌های خودکار'
        }),
        ('نمایش', {
            'fields': ('featured_image', 'is_featured', 'display_order', 'is_active')
        }),
        ('سئو', {
            'fields': ('meta_title', 'meta_description'),
            'classes': ('collapse',)
        }),
        ('محصولات', {
            'fields': ('products',),
            'description': 'فقط برای مجموعه‌های دستی'
        })
    )

# Custom admin site for store owners
admin.site.site_header = 'مدیریت فروشگاه مال'
admin.site.site_title = 'پنل مدیریت مال'
admin.site.index_title = 'خوش آمدید به پنل مدیریت'
