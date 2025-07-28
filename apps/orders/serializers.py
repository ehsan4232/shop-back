"""
Complete Order Serializers
"""
from rest_framework import serializers
from .models import Order, OrderItem, Cart, CartItem, Wishlist
from apps.products.serializers import ProductListSerializer, ProductVariantSerializer

class OrderItemSerializer(serializers.ModelSerializer):
    """Order item serializer"""
    
    class Meta:
        model = OrderItem
        fields = [
            'id', 'product', 'product_variant', 'quantity', 'unit_price', 
            'total_price', 'product_name', 'product_sku', 'product_attributes'
        ]
        read_only_fields = ['id', 'total_price']

class OrderSerializer(serializers.ModelSerializer):
    """Basic order serializer"""
    items = OrderItemSerializer(many=True, read_only=True)
    items_count = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    payment_status_display = serializers.CharField(source='get_payment_status_display', read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'status', 'status_display', 'payment_status', 
            'payment_status_display', 'customer_name', 'customer_phone', 
            'total_amount', 'items', 'items_count', 'tracking_code', 'created_at'
        ]
        read_only_fields = ['id', 'order_number', 'created_at']
    
    def get_items_count(self, obj):
        return obj.items.count()

class OrderDetailSerializer(OrderSerializer):
    """Detailed order serializer"""
    store_name = serializers.CharField(source='store.name_fa', read_only=True)
    
    class Meta(OrderSerializer.Meta):
        fields = OrderSerializer.Meta.fields + [
            'store_name', 'customer_email', 'shipping_address', 'shipping_city', 
            'shipping_state', 'shipping_postal_code', 'subtotal', 'shipping_cost', 
            'tax_amount', 'discount_amount', 'payment_method', 'payment_reference',
            'customer_notes', 'admin_notes', 'updated_at'
        ]

class OrderCreateSerializer(serializers.ModelSerializer):
    """Order creation serializer"""
    
    class Meta:
        model = Order
        fields = [
            'store', 'customer_name', 'customer_phone', 'customer_email',
            'shipping_address', 'shipping_city', 'shipping_state', 
            'shipping_postal_code', 'customer_notes', 'payment_method'
        ]
    
    def validate(self, data):
        # Validate required shipping information
        required_fields = ['customer_name', 'customer_phone', 'shipping_address', 'shipping_city']
        for field in required_fields:
            if not data.get(field):
                raise serializers.ValidationError(f'{field} الزامی است')
        return data

class CartItemSerializer(serializers.ModelSerializer):
    """Cart item serializer"""
    product = ProductListSerializer(read_only=True)
    product_variant = ProductVariantSerializer(read_only=True)
    unit_price = serializers.SerializerMethodField()
    total_price = serializers.SerializerMethodField()
    in_stock = serializers.SerializerMethodField()
    
    class Meta:
        model = CartItem
        fields = [
            'id', 'product', 'product_variant', 'quantity', 'unit_price', 
            'total_price', 'in_stock', 'added_at'
        ]
        read_only_fields = ['id', 'added_at']
    
    def get_unit_price(self, obj):
        return obj.unit_price
    
    def get_total_price(self, obj):
        return obj.total_price
    
    def get_in_stock(self, obj):
        """Check if item is still in stock"""
        if obj.product_variant:
            return obj.product_variant.stock_quantity >= obj.quantity
        return obj.product.stock_quantity >= obj.quantity

class CartSerializer(serializers.ModelSerializer):
    """Shopping cart serializer"""
    items = CartItemSerializer(many=True, read_only=True)
    total_amount = serializers.SerializerMethodField()
    total_items = serializers.SerializerMethodField()
    store_name = serializers.CharField(source='store.name_fa', read_only=True)
    
    class Meta:
        model = Cart
        fields = [
            'id', 'store', 'store_name', 'items', 'total_amount', 
            'total_items', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_total_amount(self, obj):
        return obj.total_amount
    
    def get_total_items(self, obj):
        return obj.total_items

class WishlistSerializer(serializers.ModelSerializer):
    """Wishlist serializer"""
    product = ProductListSerializer(read_only=True)
    store_name = serializers.CharField(source='store.name_fa', read_only=True)
    
    class Meta:
        model = Wishlist
        fields = ['id', 'product', 'store', 'store_name', 'added_at']
        read_only_fields = ['id', 'added_at']

class CheckoutSerializer(serializers.Serializer):
    """Checkout serializer"""
    cart_id = serializers.UUIDField()
    customer_name = serializers.CharField(max_length=100)
    customer_phone = serializers.CharField(max_length=15)
    customer_email = serializers.EmailField(required=False, allow_blank=True)
    shipping_address = serializers.CharField()
    shipping_city = serializers.CharField(max_length=50)
    shipping_state = serializers.CharField(max_length=50)
    shipping_postal_code = serializers.CharField(max_length=20)
    payment_method = serializers.ChoiceField(
        choices=[('online', 'آنلاین'), ('cash', 'نقدی')],
        default='online'
    )
    customer_notes = serializers.CharField(required=False, allow_blank=True)

class OrderStatusUpdateSerializer(serializers.Serializer):
    """Order status update serializer"""
    status = serializers.ChoiceField(choices=Order.STATUS_CHOICES)
    admin_notes = serializers.CharField(required=False, allow_blank=True)

class TrackingCodeSerializer(serializers.Serializer):
    """Tracking code serializer"""
    tracking_code = serializers.CharField(max_length=100)
    
    def validate_tracking_code(self, value):
        if not value.strip():
            raise serializers.ValidationError('کد رهگیری نمی‌تواند خالی باشد')
        return value.strip()

class OrderAnalyticsSerializer(serializers.Serializer):
    """Order analytics serializer"""
    total_orders = serializers.IntegerField()
    pending_orders = serializers.IntegerField()
    completed_orders = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=15, decimal_places=0)
    average_order_value = serializers.DecimalField(max_digits=12, decimal_places=0)
