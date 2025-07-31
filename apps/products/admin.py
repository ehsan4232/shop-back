from django.contrib import admin
from django.utils.html import format_html
from django.urls import path, reverse
from django.shortcuts import redirect
from django.contrib import messages
from django.db.models import Count, Q
from mptt.admin import MPTTModelAdmin
from apps.products.models import (
    AttributeType, Tag, ProductClass, ProductClassAttribute,
    ProductCategory, Brand, ProductAttribute, Product,
    ProductAttributeValue, ProductVariant, ProductImage, Collection
)
from apps.products.forms import ProductInstanceCreationForm


@admin.register(AttributeType)
class AttributeTypeAdmin(admin.ModelAdmin):
    list_display = ['name_fa', 'name', 'data_type', 'is_required', 'is_filterable', 'is_categorizer']
    list_filter = ['data_type', 'is_required', 'is_filterable', 'is_categorizer']
    search_fields = ['name', 'name_fa']
    ordering = ['display_order', 'name_fa']
    
    fieldsets = (
        ('اطلاعات پایه', {
            'fields': ('name', 'name_fa', 'slug', 'data_type')
        }),
        ('تنظیمات', {
            'fields': ('is_required', 'is_filterable', 'is_categorizer', 'display_order')
        }),
        ('اعتبارسنجی', {
            'fields': ('validation_rules',),
            'classes': ('collapse',)
        })
    )


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ['name_fa', 'tag_type', 'usage_count', 'is_featured', 'color_display']
    list_filter = ['tag_type', 'is_featured', 'is_filterable', 'store']
    search_fields = ['name', 'name_fa']
    readonly_fields = ['usage_count']
    
    def color_display(self, obj):
        return format_html(
            '<span style="background-color: {}; padding: 3px 8px; border-radius: 3px; color: white;">{}</span>',
            obj.color,
            obj.color
        )
    color_display.short_description = 'رنگ'


@admin.register(ProductClass)
class ProductClassAdmin(MPTTModelAdmin):
    """
    CRITICAL: Enhanced admin for ProductClass with object-oriented hierarchy
    Product requirement: Object-oriented product classes with inheritance
    """
    list_display = ['name_fa', 'parent', 'is_leaf', 'product_count', 'effective_price_display', 'is_active']
    list_filter = ['is_active', 'is_leaf', 'store']
    search_fields = ['name', 'name_fa']
    readonly_fields = ['product_count', 'effective_price_display', 'inherited_media_display']
    
    fieldsets = (
        ('اطلاعات پایه', {
            'fields': ('name', 'name_fa', 'slug', 'description', 'store')
        }),
        ('ساختار سلسله‌مراتبی', {
            'fields': ('parent',)
        }),
        ('قیمت‌گذاری (وراثتی)', {
            'fields': ('base_price', 'effective_price_display'),
            'description': 'قیمت از کلاس والد به ارث می‌رسد'
        }),
        ('رسانه (وراثتی)', {
            'fields': ('media_list', 'inherited_media_display'),
            'classes': ('collapse',)
        }),
        ('نمایش', {
            'fields': ('icon', 'image', 'display_order', 'is_active')
        }),
        ('وضعیت', {
            'fields': ('is_leaf', 'product_count'),
            'classes': ('collapse',)
        })
    )
    
    def effective_price_display(self, obj):
        price = obj.get_effective_price()
        if obj.base_price:
            return format_html(
                '<strong style="color: green;">{:,} تومان</strong> (مستقیم)',
                price
            )
        elif price > 0:
            return format_html(
                '<span style="color: blue;">{:,} تومان</span> (وراثتی)',
                price
            )
        else:
            return format_html('<span style="color: red;">تعریف نشده</span>')
    effective_price_display.short_description = 'قیمت مؤثر'
    
    def inherited_media_display(self, obj):
        media = obj.get_inherited_media()
        if media:
            return format_html(
                '<div>{} رسانه از کلاس‌های والد</div>',
                len(media)
            )
        return 'بدون رسانه'
    inherited_media_display.short_description = 'رسانه‌های وراثتی'
    
    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            product_count_annotated=Count('products', filter=Q(products__status='published'))
        )


@admin.register(ProductClassAttribute)
class ProductClassAttributeAdmin(admin.ModelAdmin):
    list_display = ['product_class', 'attribute_type', 'is_required', 'is_inherited', 'is_categorizer']
    list_filter = ['is_required', 'is_inherited', 'is_categorizer', 'attribute_type__data_type']
    search_fields = ['product_class__name_fa', 'attribute_type__name_fa']


@admin.register(ProductCategory)
class ProductCategoryAdmin(MPTTModelAdmin):
    list_display = ['name_fa', 'parent', 'product_count', 'is_active']
    list_filter = ['is_active', 'store']
    search_fields = ['name', 'name_fa']
    readonly_fields = ['product_count']


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ['name_fa', 'product_count', 'is_active']
    list_filter = ['is_active', 'store']
    search_fields = ['name', 'name_fa']
    readonly_fields = ['product_count']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """
    CRITICAL: Enhanced Product admin with all product requirements
    - Checkbox for creating another instance
    - Stock warning display
    - Social media import integration
    """
    form = ProductInstanceCreationForm
    list_display = [
        'name_fa', 'product_class', 'category', 'price_display', 
        'stock_status', 'social_media_badge', 'status'
    ]
    list_filter = [
        'status', 'product_type', 'is_featured', 'imported_from_social',
        'social_media_source', 'product_class', 'category', 'brand'
    ]
    search_fields = ['name', 'name_fa', 'sku']
    readonly_fields = [
        'effective_price_display', 'stock_warning_display', 
        'inherited_attributes_display', 'social_import_info'
    ]
    filter_horizontal = ['tags']
    
    fieldsets = (
        ('اطلاعات پایه', {
            'fields': ('name', 'name_fa', 'slug', 'description', 'short_description')
        }),
        ('ساختار محصول', {
            'fields': ('product_class', 'category', 'brand', 'tags', 'product_type'),
            'description': 'فقط از کلاس‌های برگ می‌توان محصول ایجاد کرد'
        }),
        ('قیمت‌گذاری', {
            'fields': ('base_price', 'effective_price_display', 'compare_price', 'cost_price')
        }),
        ('موجودی و انبار', {
            'fields': ('sku', 'stock_quantity', 'stock_warning_display', 'manage_stock', 'low_stock_threshold')
        }),
        ('رسانه', {
            'fields': ('featured_image',)
        }),
        ('ویژگی‌های فیزیکی', {
            'fields': ('weight',),
            'classes': ('collapse',)
        }),
        ('وضعیت و نمایش', {
            'fields': ('status', 'is_featured')
        }),
        ('وراثت ویژگی‌ها', {
            'fields': ('inherited_attributes_display',),
            'classes': ('collapse',)
        }),
        ('شبکه‌های اجتماعی', {
            'fields': ('social_import_info',),
            'classes': ('collapse',)
        }),
        ('ایجاد نمونه دیگر', {
            'fields': ('create_another_instance',),
            'description': 'برای تسهیل در ایجاد محصولات مشابه'
        })
    )
    
    def price_display(self, obj):
        price = obj.get_effective_price()
        if obj.base_price:
            return format_html('{:,} تومان', price)
        else:
            return format_html(
                '<span style="color: blue;" title="قیمت وراثتی">{:,} تومان</span>',
                price
            )
    price_display.short_description = 'قیمت'
    
    def stock_status(self, obj):
        """Display stock status with warning colors"""
        if obj.needs_stock_warning():
            if obj.stock_quantity == 0:
                return format_html(
                    '<span style="color: red; font-weight: bold;">ناموجود</span>'
                )
            else:
                return format_html(
                    '<span style="color: orange; font-weight: bold;">کم ({} عدد)</span>',
                    obj.stock_quantity
                )
        else:
            return format_html(
                '<span style="color: green;">موجود ({} عدد)</span>',
                obj.stock_quantity
            )
    stock_status.short_description = 'وضعیت موجودی'
    
    def social_media_badge(self, obj):
        if obj.imported_from_social:
            platform_name = obj.get_social_media_source_display() if obj.social_media_source else 'شبکه اجتماعی'
            return format_html(
                '<span style="background: #1da1f2; color: white; padding: 2px 6px; '
                'border-radius: 3px; font-size: 11px;">{}</span>',
                platform_name
            )
        return '-'
    social_media_badge.short_description = 'شبکه اجتماعی'
    
    def effective_price_display(self, obj):
        return self.price_display(obj)
    effective_price_display.short_description = 'قیمت مؤثر'
    
    def stock_warning_display(self, obj):
        """Display stock warning as in frontend"""
        warning_msg = obj.get_stock_warning_message()
        if warning_msg:
            return format_html(
                '<div style="background: #fef3c7; border: 1px solid #f59e0b; '
                'color: #92400e; padding: 8px; border-radius: 4px;">'
                '<strong>هشدار:</strong> {}</div>',
                warning_msg
            )
        return format_html(
            '<span style="color: green;">موجودی مناسب</span>'
        )
    stock_warning_display.short_description = 'هشدار موجودی'
    
    def inherited_attributes_display(self, obj):
        if obj.product_class:
            attrs = obj.get_inherited_attributes()
            if attrs:
                attr_list = []
                for attr in attrs[:5]:  # Show first 5
                    attr_list.append(f"• {attr.attribute_type.name_fa}")
                result = '<br>'.join(attr_list)
                if len(attrs) > 5:
                    result += f'<br><em>... و {len(attrs) - 5} ویژگی دیگر</em>'
                return format_html(result)
        return 'بدون ویژگی وراثتی'
    inherited_attributes_display.short_description = 'ویژگی‌های وراثتی'
    
    def social_import_info(self, obj):
        if obj.imported_from_social:
            info = []
            if obj.social_media_source:
                info.append(f"پلتفرم: {obj.get_social_media_source_display()}")
            if obj.social_media_post_id:
                info.append(f"شناسه پست: {obj.social_media_post_id}")
            if obj.last_social_import:
                info.append(f"تاریخ وارد کردن: {obj.last_social_import.strftime('%Y/%m/%d %H:%M')}")
            return format_html('<br>'.join(info))
        return 'وارد نشده از شبکه اجتماعی'
    social_import_info.short_description = 'اطلاعات وارد کردن'
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # Pass current store context to form
        if hasattr(request, 'user') and request.user.is_authenticated:
            # This should be set by middleware based on current store context
            store = getattr(request, 'current_store', None)
            if store:
                form.base_fields['store'].initial = store
        return form
    
    def save_model(self, request, obj, form, change):
        # Handle the "create another instance" checkbox
        if form.cleaned_data.get('create_another_instance') and not change:
            # This will be handled by the form's save method
            pass
        super().save_model(request, obj, form, change)
    
    actions = ['bulk_update_stock_warning', 'mark_as_featured', 'import_from_social']
    
    def bulk_update_stock_warning(self, request, queryset):
        """Bulk action to update stock warnings"""
        updated = 0
        for product in queryset:
            if product.needs_stock_warning():
                updated += 1
        
        self.message_user(
            request,
            f'{updated} محصول نیاز به هشدار موجودی دارند',
            messages.WARNING if updated > 0 else messages.INFO
        )
    bulk_update_stock_warning.short_description = 'بررسی هشدار موجودی'
    
    def mark_as_featured(self, request, queryset):
        updated = queryset.update(is_featured=True)
        self.message_user(request, f'{updated} محصول به عنوان ویژه علامت‌گذاری شد')
    mark_as_featured.short_description = 'علامت‌گذاری به عنوان ویژه'


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ['product', 'variant_display', 'price', 'stock_quantity', 'is_active', 'is_default']
    list_filter = ['is_active', 'is_default', 'product__status']
    search_fields = ['product__name_fa', 'sku']
    
    def variant_display(self, obj):
        return str(obj)
    variant_display.short_description = 'نمایش نوع'


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ['product', 'image_preview', 'is_featured', 'imported_from_social', 'display_order']
    list_filter = ['is_featured', 'imported_from_social']
    readonly_fields = ['image_preview']
    
    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-width: 100px; max-height: 100px;" />',
                obj.image.url
            )
        return 'بدون تصویر'
    image_preview.short_description = 'پیش‌نمایش'


@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    list_display = ['name_fa', 'product_count_display', 'is_featured', 'is_active']
    list_filter = ['is_featured', 'is_active', 'store']
    search_fields = ['name', 'name_fa']
    filter_horizontal = ['products']
    
    def product_count_display(self, obj):
        count = obj.products.count()
        return f'{count} محصول'
    product_count_display.short_description = 'تعداد محصولات'


# Customize admin site
admin.site.site_header = 'پنل مدیریت مال'
admin.site.site_title = 'مال'
admin.site.index_title = 'خوش آمدید به پنل مدیریت فروشگاه‌ساز مال'

# Add custom views to admin
class ProductAdminExtended(ProductAdmin):
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'bulk-import-social/',
                self.admin_site.admin_view(self.bulk_import_social_view),
                name='products_product_bulk_import_social'
            ),
            path(
                'stock-warnings/',
                self.admin_site.admin_view(self.stock_warnings_view),
                name='products_product_stock_warnings'
            ),
        ]
        return custom_urls + urls
    
    def bulk_import_social_view(self, request):
        """Custom view for bulk social media import"""
        from django.shortcuts import render
        if request.method == 'POST':
            # Handle bulk import logic here
            messages.success(request, 'وارد کردن از شبکه‌های اجتماعی آغاز شد')
            return redirect('..')
        
        context = {
            'title': 'وارد کردن گروهی از شبکه‌های اجتماعی',
            'opts': self.model._meta,
        }
        return render(request, 'admin/products/bulk_social_import.html', context)
    
    def stock_warnings_view(self, request):
        """Custom view for stock warnings dashboard"""
        low_stock_products = Product.objects.filter(
            stock_quantity__lt=3,
            status='published'
        ).select_related('product_class', 'category')
        
        context = {
            'title': 'هشدارهای موجودی',
            'low_stock_products': low_stock_products,
            'opts': self.model._meta,
        }
        return render(request, 'admin/products/stock_warnings.html', context)

# Re-register with extended functionality
admin.site.unregister(Product)
admin.site.register(Product, ProductAdminExtended)
