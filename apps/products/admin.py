from django.contrib import admin
from mptt.admin import MPTTModelAdmin
from .models import ProductCategory, ProductAttribute, Product, ProductInstance, ProductInstanceAttribute

class ProductAttributeInline(admin.TabularInline):
    model = ProductAttribute
    extra = 1
    fields = ('name_fa', 'attribute_type', 'is_required', 'is_categorizer', 'order')

@admin.register(ProductCategory)
class ProductCategoryAdmin(MPTTModelAdmin):
    list_display = ('name_fa', 'name', 'store', 'is_categorizer', 'is_active', 'created_at')
    list_filter = ('store', 'is_categorizer', 'is_active', 'created_at')
    search_fields = ('name', 'name_fa')
    inlines = [ProductAttributeInline]
    
    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('store', 'parent', 'name', 'name_fa', 'description')
        }),
        ('تنظیمات', {
            'fields': ('is_categorizer', 'image', 'is_active')
        }),
    )

class ProductInstanceAttributeInline(admin.TabularInline):
    model = ProductInstanceAttribute
    extra = 0
    fields = ('attribute', 'value', 'color_hex')

class ProductInstanceInline(admin.TabularInline):
    model = ProductInstance
    extra = 1
    fields = ('sku', 'price', 'stock_quantity', 'is_active')
    readonly_fields = ('id',)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name_fa', 'category', 'store', 'base_price', 'is_featured', 'view_count', 'created_at')
    list_filter = ('store', 'category', 'is_active', 'is_featured', 'created_at')
    search_fields = ('name', 'name_fa', 'description_fa')
    readonly_fields = ('id', 'view_count', 'created_at', 'updated_at')
    inlines = [ProductInstanceInline]
    
    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('store', 'category', 'name', 'name_fa', 'description_fa', 'base_price')
        }),
        ('رسانه', {
            'fields': ('images', 'videos')
        }),
        ('تنظیمات', {
            'fields': ('is_active', 'is_featured')
        }),
        ('آمار', {
            'fields': ('view_count', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(ProductInstance)
class ProductInstanceAdmin(admin.ModelAdmin):
    list_display = ('product', 'sku', 'final_price', 'stock_quantity', 'is_low_stock', 'is_active')
    list_filter = ('product__store', 'is_active', 'created_at')
    search_fields = ('sku', 'product__name_fa')
    inlines = [ProductInstanceAttributeInline]
    
    def is_low_stock(self, obj):
        return obj.is_low_stock
    is_low_stock.boolean = True
    is_low_stock.short_description = 'موجودی کم'

@admin.register(ProductAttribute)
class ProductAttributeAdmin(admin.ModelAdmin):
    list_display = ('name_fa', 'category', 'attribute_type', 'is_required', 'is_categorizer')
    list_filter = ('attribute_type', 'is_required', 'is_categorizer')
    search_fields = ('name', 'name_fa', 'category__name_fa')