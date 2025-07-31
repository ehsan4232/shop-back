from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django import forms
from mptt.admin import MPTTModelAdmin
from .models import (
    AttributeType, Tag, ProductClass, ProductClassAttribute,
    ProductCategory, ProductAttribute, Brand,
    Product, ProductVariant, ProductAttributeValue, ProductImage, Collection
)

# ENHANCED: Color Widget for proper color field support
class ColorWidget(forms.TextInput):
    """Enhanced color picker widget for admin interface"""
    input_type = 'color'
    template_name = 'admin/widgets/color.html'
    
    class Media:
        css = {
            'screen': ('admin/css/color-picker.css',)
        }
        js = ('admin/js/color-picker.js',)
    
    def format_value(self, value):
        if value:
            return value
        return '#000000'

# ENHANCED: Form for ProductAttributeValue with color support
class ProductAttributeValueForm(forms.ModelForm):
    """Enhanced form for product attribute values with dynamic field display"""
    
    class Meta:
        model = ProductAttributeValue
        fields = '__all__'
        widgets = {
            'value_color': ColorWidget(attrs={
                'class': 'color-picker-input',
                'style': 'width: 100px;'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Dynamically show/hide fields based on attribute type
        if 'attribute' in self.data or (self.instance and self.instance.attribute_id):
            try:
                attribute_id = self.data.get('attribute') or self.instance.attribute_id
                if attribute_id:
                    attribute = ProductAttribute.objects.get(id=attribute_id)
                    attr_type = attribute.attribute_type.data_type
                    
                    # Hide irrelevant fields based on attribute type
                    if attr_type != 'color':
                        self.fields['value_color'].widget = forms.HiddenInput()
                    if attr_type != 'number':
                        self.fields['value_number'].widget = forms.HiddenInput()
                    if attr_type != 'boolean':
                        self.fields['value_boolean'].widget = forms.HiddenInput()
                    if attr_type != 'date':
                        self.fields['value_date'].widget = forms.HiddenInput()
                    if attr_type in ['color', 'number', 'boolean', 'date']:
                        self.fields['value_text'].widget = forms.HiddenInput()
            except (ProductAttribute.DoesNotExist, ValueError):
                pass

@admin.register(AttributeType)
class AttributeTypeAdmin(admin.ModelAdmin):
    list_display = ['name_fa', 'name', 'data_type', 'is_required', 'is_filterable', 'color_indicator', 'display_order']
    list_filter = ['data_type', 'is_required', 'is_filterable']
    search_fields = ['name_fa', 'name']
    ordering = ['display_order', 'name_fa']
    prepopulated_fields = {'slug': ('name',)}
    
    def color_indicator(self, obj):
        """Show color indicator for color attribute types"""
        if obj.data_type == 'color':
            return format_html(
                '<span style="background: linear-gradient(90deg, #ff0000, #00ff00, #0000ff); width: 30px; height: 15px; display: inline-block; border-radius: 3px; border: 1px solid #ccc;"></span>'
            )
        return '-'
    color_indicator.short_description = 'نوع رنگ'

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

# ENHANCED: ProductAttributeValueInline with color support
class ProductAttributeValueInline(admin.TabularInline):
    model = ProductAttributeValue
    form = ProductAttributeValueForm
    extra = 0
    autocomplete_fields = ['attribute']
    
    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(super().get_readonly_fields(request, obj))
        
        # Make attribute readonly after creation to prevent data corruption
        if obj and obj.pk:
            readonly_fields.append('attribute')
        
        return readonly_fields
    
    def color_preview(self, obj):
        """Display color preview in admin"""
        if obj.value_color:
            return format_html(
                '<div style="width: 20px; height: 20px; background-color: {}; border: 1px solid #ccc; display: inline-block; margin-right: 5px;"></div>{}',
                obj.value_color,
                obj.value_color
            )
        return '-'
    color_preview.short_description = 'پیش‌نمایش رنگ'
    
    readonly_fields = ['color_preview']

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        'name_fa', 'store', 'product_class', 'category', 'brand', 
        'effective_price', 'stock_quantity', 'stock_warning_status', 'status', 'is_featured',
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
        'stock_warning_status', 'view_count', 'sales_count', 'created_at', 'updated_at', 'published_at'
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
                'in_stock', 'is_low_stock', 'stock_warning_status'
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
    
    # ENHANCED: Stock warning status display
    def stock_warning_status(self, obj):
        """Show stock warning status with visual indicators"""
        if obj.needs_stock_warning():
            if obj.stock_quantity == 0:
                return format_html(
                    '<span style="color: #dc3545; font-weight: bold;">⚠️ ناموجود</span>'
                )
            else:
                return format_html(
                    '<span style="color: #ffc107; font-weight: bold;">⚠️ موجودی کم ({})</span>',
                    obj.stock_quantity
                )
        return format_html('<span style="color: #28a745;">✅ موجود</span>')
    stock_warning_status.short_description = "وضعیت موجودی"
    stock_warning_status.admin_order_field = 'stock_quantity'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'store', 'product_class', 'category', 'brand'
        ).prefetch_related('tags')
    
    class Media:
        css = {
            'screen': ('admin/css/enhanced-product-admin.css',)
        }
        js = (
            'admin/js/jquery.min.js',
            'admin/js/color-picker.js',
            'admin/js/product-form-enhancements.js',
        )

@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = [
        'product', 'sku', 'price', 'stock_quantity', 'stock_warning_status',
        'is_active', 'is_default', 'in_stock'
    ]
    list_filter = ['is_active', 'is_default', 'product__store']
    search_fields = ['sku', 'product__name_fa']
    ordering = ['product', 'price']
    readonly_fields = ['in_stock', 'discount_percentage', 'stock_warning_status']
    autocomplete_fields = ['product']
    
    def in_stock(self, obj):
        return obj.in_stock
    in_stock.boolean = True
    
    def discount_percentage(self, obj):
        return f"{obj.discount_percentage}%"
    
    def stock_warning_status(self, obj):
        """Show stock warning status for variants"""
        if obj.needs_stock_warning():
            if obj.stock_quantity == 0:
                return format_html('<span style="color: #dc3545;">⚠️ ناموجود</span>')
            else:
                return format_html('<span style="color: #ffc107;">⚠️ کم</span>')
        return format_html('<span style="color: #28a745;">✅</span>')
    stock_warning_status.short_description = "موجودی"

@admin.register(ProductAttributeValue)
class ProductAttributeValueAdmin(admin.ModelAdmin):
    list_display = ['product', 'variant', 'attribute', 'get_value_display', 'color_preview']
    list_filter = ['attribute__attribute_type__data_type', 'product__store']
    search_fields = ['product__name_fa', 'variant__sku', 'value_text']
    autocomplete_fields = ['product', 'variant', 'attribute']
    form = ProductAttributeValueForm
    
    def get_value_display(self, obj):
        """Display the value based on attribute type"""
        value = obj.get_value()
        if obj.attribute.attribute_type.data_type == 'color' and value:
            return format_html(
                '<div style="display: flex; align-items: center; gap: 8px;">'  
                '<div style="width: 20px; height: 20px; background-color: {}; border: 1px solid #ccc; border-radius: 3px;"></div>'  
                '<span>{}</span></div>',
                value, value
            )
        return str(value) if value is not None else '-'
    get_value_display.short_description = 'مقدار'
    
    def color_preview(self, obj):
        """Display color preview"""
        if obj.attribute.attribute_type.data_type == 'color' and obj.value_color:
            return format_html(
                '<div style="width: 25px; height: 25px; background-color: {}; border: 1px solid #ccc; border-radius: 50%;"></div>',
                obj.value_color
            )
        return '-'
    color_preview.short_description = 'پیش‌نمایش'

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
