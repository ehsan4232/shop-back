from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from mptt.admin import MPTTModelAdmin
from .models import (
    AttributeType, Tag, ProductClass, ProductClassAttribute,
    ProductCategory, ProductAttribute, Brand,
    Product, ProductVariant, ProductAttributeValue, ProductImage, Collection
)

@admin.register(AttributeType)
class AttributeTypeAdmin(admin.ModelAdmin):
    list_display = ['name_fa', 'name', 'data_type', 'is_required', 'is_filterable', 'display_order']
    list_filter = ['data_type', 'is_required', 'is_filterable']
    search_fields = ['name_fa', 'name']
    ordering = ['display_order', 'name_fa']
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ['name_fa', 'tag_type', 'store', 'usage_count', 'is_featured', 'is_filterable']
    list_filter = ['tag_type', 'is_featured', 'is_filterable', 'store']
    search_fields = ['name_fa', 'name']
    ordering = ['-usage_count', 'name_fa']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['usage_count']

class ProductClassAttributeInline(admin.TabularInline):
    model = ProductClassAttribute
    extra = 0
    autocomplete_fields = ['attribute_type']

@admin.register(ProductClass)
class ProductClassAdmin(MPTTModelAdmin):
    list_display = ['name_fa', 'store', 'parent', 'base_price', 'is_leaf', 'product_count', 'is_active']
    list_filter = ['store', 'is_active', 'is_leaf']
    search_fields = ['name_fa', 'name']
    ordering = ['tree_id', 'lft']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['is_leaf', 'product_count']
    inlines = [ProductClassAttributeInline]
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('parent', 'store')

class ProductAttributeInline(admin.TabularInline):
    model = ProductAttribute
    extra = 0
    autocomplete_fields = ['attribute_type']

@admin.register(ProductCategory)
class ProductCategoryAdmin(MPTTModelAdmin):
    list_display = ['name_fa', 'store', 'parent', 'product_count', 'is_active']
    list_filter = ['store', 'is_active']
    search_fields = ['name_fa', 'name']
    ordering = ['tree_id', 'lft']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['product_count']
    inlines = [ProductAttributeInline]
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('parent', 'store')

@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ['name_fa', 'store', 'product_count', 'is_active']
    list_filter = ['store', 'is_active']
    search_fields = ['name_fa', 'name']
    ordering = ['name_fa']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['product_count']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('store')

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 0
    readonly_fields = ['image_preview']
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height: 100px;"/>', obj.image.url)
        return "No Image"
    image_preview.short_description = "Preview"

class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 0
    readonly_fields = ['in_stock', 'discount_percentage']
    
    def in_stock(self, obj):
        return obj.in_stock
    in_stock.boolean = True
    
    def discount_percentage(self, obj):
        return f"{obj.discount_percentage}%"

class ProductAttributeValueInline(admin.TabularInline):
    model = ProductAttributeValue
    extra = 0
    autocomplete_fields = ['attribute']

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        'name_fa', 'store', 'product_class', 'category', 'brand', 
        'effective_price', 'stock_quantity', 'status', 'is_featured',
        'view_count', 'sales_count', 'created_at'
    ]
    list_filter = [
        'store', 'product_class', 'category', 'brand', 'status', 
        'product_type', 'is_featured', 'imported_from_social'
    ]
    search_fields = ['name_fa', 'name', 'sku', 'description']
    ordering = ['-created_at']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = [
        'effective_price', 'in_stock', 'discount_percentage', 'is_low_stock',
        'view_count', 'sales_count', 'created_at', 'updated_at', 'published_at'
    ]
    autocomplete_fields = ['product_class', 'category', 'brand', 'tags']
    filter_horizontal = ['tags']
    inlines = [ProductAttributeValueInline, ProductImageInline, ProductVariantInline]
    
    fieldsets = (
        ('اطلاعات پایه', {
            'fields': (
                'name', 'name_fa', 'slug', 'description', 'short_description',
                'product_class', 'category', 'brand', 'tags'
            )
        }),
        ('نوع و قیمت', {
            'fields': (
                'product_type', 'base_price', 'effective_price', 'compare_price', 
                'cost_price', 'discount_percentage'
            )
        }),
        ('موجودی', {
            'fields': (
                'sku', 'stock_quantity', 'manage_stock', 'low_stock_threshold',
                'in_stock', 'is_low_stock'
            )
        }),
        ('رسانه', {
            'fields': ('featured_image', 'weight')
        }),
        ('SEO', {
            'fields': ('meta_title', 'meta_description'),
            'classes': ('collapse',)
        }),
        ('وضعیت', {
            'fields': ('status', 'is_featured')
        }),
        ('شبکه اجتماعی', {
            'fields': (
                'imported_from_social', 'social_media_source', 'social_media_post_id'
            ),
            'classes': ('collapse',)
        }),
        ('آمار', {
            'fields': (
                'view_count', 'sales_count', 'rating_average', 'rating_count',
                'created_at', 'updated_at', 'published_at'
            ),
            'classes': ('collapse',)
        }),
    )
    
    def effective_price(self, obj):
        return f"{obj.get_effective_price():,} تومان"
    effective_price.short_description = "قیمت مؤثر"
    
    def in_stock(self, obj):
        return obj.in_stock
    in_stock.boolean = True
    in_stock.short_description = "موجود"
    
    def discount_percentage(self, obj):
        return f"{obj.discount_percentage}%" if obj.discount_percentage else "-"
    discount_percentage.short_description = "درصد تخفیف"
    
    def is_low_stock(self, obj):
        return obj.is_low_stock
    is_low_stock.boolean = True
    is_low_stock.short_description = "موجودی کم"
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'store', 'product_class', 'category', 'brand'
        ).prefetch_related('tags')

@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = [
        'product', 'sku', 'price', 'stock_quantity', 
        'is_active', 'is_default', 'in_stock'
    ]
    list_filter = ['is_active', 'is_default', 'product__store']
    search_fields = ['sku', 'product__name_fa']
    ordering = ['product', 'price']
    readonly_fields = ['in_stock', 'discount_percentage']
    autocomplete_fields = ['product']
    
    def in_stock(self, obj):
        return obj.in_stock
    in_stock.boolean = True
    
    def discount_percentage(self, obj):
        return f"{obj.discount_percentage}%"

@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ['product', 'image_preview', 'is_featured', 'display_order', 'imported_from_social']
    list_filter = ['is_featured', 'imported_from_social', 'product__store']
    search_fields = ['product__name_fa', 'alt_text']
    ordering = ['product', 'display_order']
    readonly_fields = ['image_preview']
    autocomplete_fields = ['product', 'variant']
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height: 100px;"/>', obj.image.url)
        return "No Image"
    image_preview.short_description = "Preview"

@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    list_display = ['name_fa', 'store', 'products_count', 'is_featured', 'is_active']
    list_filter = ['store', 'is_featured', 'is_active']
    search_fields = ['name_fa', 'name']
    ordering = ['display_order', 'name_fa']
    prepopulated_fields = {'slug': ('name',)}
    filter_horizontal = ['products']
    
    def products_count(self, obj):
        return obj.products.count()
    products_count.short_description = "تعداد محصولات"
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('store').prefetch_related('products')

# Admin site customization
admin.site.site_header = "مال - پنل مدیریت"
admin.site.site_title = "مال - مدیریت محصولات"
admin.site.index_title = "خوش آمدید به پنل مدیریت مال"
