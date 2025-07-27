from django.contrib import admin
from .models import Order, OrderItem, Cart, CartItem

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('total_price',)
    fields = ('product_instance', 'quantity', 'unit_price', 'total_price', 'product_name', 'product_sku')

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'customer_name', 'store', 'status', 'payment_status', 'total_amount', 'created_at')
    list_filter = ('status', 'payment_status', 'store', 'created_at')
    search_fields = ('order_number', 'customer_name', 'customer_phone', 'customer_email')
    readonly_fields = ('id', 'order_number', 'created_at', 'updated_at')
    inlines = [OrderItemInline]
    
    fieldsets = (
        ('اطلاعات سفارش', {
            'fields': ('order_number', 'store', 'customer', 'status', 'payment_status')
        }),
        ('اطلاعات مشتری', {
            'fields': ('customer_name', 'customer_phone', 'customer_email')
        }),
        ('آدرس ارسال', {
            'fields': ('shipping_address', 'shipping_city', 'shipping_state', 'shipping_postal_code')
        }),
        ('مبالغ مالی', {
            'fields': ('subtotal', 'shipping_cost', 'tax_amount', 'discount_amount', 'total_amount')
        }),
        ('پرداخت', {
            'fields': ('payment_method', 'payment_reference')
        }),
        ('تحویل', {
            'fields': ('tracking_code',)
        }),
        ('یادداشت‌ها', {
            'fields': ('customer_notes', 'admin_notes')
        }),
        ('اطلاعات سیستم', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('customer', 'store', 'total_items', 'total_amount', 'updated_at')
    list_filter = ('store', 'created_at')
    search_fields = ('customer__phone_number', 'store__name_fa')
    inlines = [CartItemInline]
    
    def total_items(self, obj):
        return obj.total_items
    total_items.short_description = 'تعداد آیتم‌ها'
    
    def total_amount(self, obj):
        return f'{obj.total_amount:,} تومان'
    total_amount.short_description = 'مجموع'

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'product_name', 'quantity', 'unit_price', 'total_price')
    list_filter = ('order__store', 'order__created_at')
    search_fields = ('product_name', 'product_sku', 'order__order_number')

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('cart', 'product_instance', 'quantity', 'total_price', 'added_at')
    list_filter = ('cart__store', 'added_at')
    search_fields = ('product_instance__product__name_fa', 'cart__customer__phone_number')