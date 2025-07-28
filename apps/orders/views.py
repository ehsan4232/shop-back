"""
Complete Order Management Views
"""
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import Q, Sum, Count
from .models import Order, OrderItem, Cart, CartItem, Wishlist
from .serializers import (
    OrderSerializer, OrderDetailSerializer, OrderCreateSerializer,
    CartSerializer, CartItemSerializer, WishlistSerializer
)
from apps.products.models import Product, ProductVariant

class IsOwnerOrStoreOwner(permissions.BasePermission):
    """Custom permission for orders"""
    def has_object_permission(self, request, view, obj):
        # Customer can access their own orders
        if hasattr(obj, 'customer') and obj.customer == request.user:
            return True
        # Store owner can access orders for their store
        if hasattr(obj, 'store') and obj.store.owner == request.user:
            return True
        return False

class OrderViewSet(viewsets.ModelViewSet):
    """Order management ViewSet"""
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrStoreOwner]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return OrderCreateSerializer
        elif self.action in ['retrieve']:
            return OrderDetailSerializer
        return OrderSerializer
    
    def get_queryset(self):
        user = self.request.user
        if user.is_store_owner:
            # Store owners see orders for their stores
            return Order.objects.filter(store__owner=user)
        else:
            # Customers see their own orders
            return Order.objects.filter(customer=user)
    
    def perform_create(self, serializer):
        """Create order from cart"""
        with transaction.atomic():
            # Get customer's cart
            cart = Cart.objects.filter(
                customer=self.request.user,
                store=serializer.validated_data['store']
            ).first()
            
            if not cart or not cart.items.exists():
                raise ValidationError("سبد خرید خالی است")
            
            # Create order
            order = serializer.save(
                customer=self.request.user,
                order_number=f'ORD{timezone.now().strftime("%Y%m%d%H%M%S")}'
            )
            
            # Create order items from cart
            total_amount = 0
            for cart_item in cart.items.all():
                order_item = OrderItem.objects.create(
                    order=order,
                    product=cart_item.product,
                    product_variant=cart_item.product_variant,
                    quantity=cart_item.quantity,
                    unit_price=cart_item.unit_price,
                    total_price=cart_item.total_price,
                    product_name=cart_item.product.name_fa,
                    product_sku=cart_item.product.sku or ''
                )
                total_amount += cart_item.total_price
                
                # Reduce inventory
                if cart_item.product_variant:
                    if cart_item.product_variant.stock_quantity >= cart_item.quantity:
                        cart_item.product_variant.stock_quantity -= cart_item.quantity
                        cart_item.product_variant.save()
                else:
                    if cart_item.product.stock_quantity >= cart_item.quantity:
                        cart_item.product.stock_quantity -= cart_item.quantity
                        cart_item.product.save()
            
            # Update order totals
            order.subtotal = total_amount
            order.total_amount = total_amount  # Add shipping, tax later
            order.save()
            
            # Clear cart
            cart.items.all().delete()
    
    @action(detail=True, methods=['patch'])
    def update_status(self, request, pk=None):
        """Update order status (store owner only)"""
        order = self.get_object()
        if order.store.owner != request.user:
            return Response({'error': 'دسترسی غیرمجاز'}, status=403)
        
        new_status = request.data.get('status')
        if new_status not in dict(Order.STATUS_CHOICES):
            return Response({'error': 'وضعیت نامعتبر'}, status=400)
        
        order.status = new_status
        order.save()
        
        return Response({'message': 'وضعیت سفارش به‌روزرسانی شد', 'status': new_status})
    
    @action(detail=True, methods=['patch'])
    def add_tracking(self, request, pk=None):
        """Add tracking code"""
        order = self.get_object()
        if order.store.owner != request.user:
            return Response({'error': 'دسترسی غیرمجاز'}, status=403)
        
        tracking_code = request.data.get('tracking_code')
        if not tracking_code:
            return Response({'error': 'کد رهگیری الزامی است'}, status=400)
        
        order.tracking_code = tracking_code
        order.status = 'shipped'
        order.save()
        
        return Response({'message': 'کد رهگیری اضافه شد', 'tracking_code': tracking_code})

class CartViewSet(viewsets.ModelViewSet):
    """Shopping cart management"""
    serializer_class = CartSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Cart.objects.filter(customer=self.request.user)
    
    def get_object(self):
        """Get or create cart for current store"""
        store_id = self.request.query_params.get('store')
        if not store_id:
            from django.core.exceptions import ValidationError
            raise ValidationError("Store ID required")
        
        cart, created = Cart.objects.get_or_create(
            customer=self.request.user,
            store_id=store_id
        )
        return cart

class CartItemViewSet(viewsets.ModelViewSet):
    """Cart item management"""
    serializer_class = CartItemSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return CartItem.objects.filter(cart__customer=self.request.user)
    
    def perform_create(self, serializer):
        """Add item to cart"""
        product_id = self.request.data.get('product')
        variant_id = self.request.data.get('product_variant')
        quantity = int(self.request.data.get('quantity', 1))
        
        # Get product and variant
        product = get_object_or_404(Product, id=product_id)
        variant = None
        if variant_id:
            variant = get_object_or_404(ProductVariant, id=variant_id, product=product)
        
        # Get or create cart
        cart, created = Cart.objects.get_or_create(
            customer=self.request.user,
            store=product.store
        )
        
        # Check if item already exists
        existing_item = CartItem.objects.filter(
            cart=cart,
            product=product,
            product_variant=variant
        ).first()
        
        if existing_item:
            existing_item.quantity += quantity
            existing_item.save()
            serializer.instance = existing_item
        else:
            serializer.save(
                cart=cart,
                product=product,
                product_variant=variant
            )

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def add_to_cart(request):
    """Add product to cart"""
    product_id = request.data.get('product_id')
    variant_id = request.data.get('variant_id')
    quantity = int(request.data.get('quantity', 1))
    
    if not product_id:
        return Response({'error': 'شناسه محصول الزامی است'}, status=400)
    
    try:
        product = Product.objects.get(id=product_id, status='published')
    except Product.DoesNotExist:
        return Response({'error': 'محصول یافت نشد'}, status=404)
    
    variant = None
    if variant_id:
        try:
            variant = ProductVariant.objects.get(id=variant_id, product=product, is_active=True)
        except ProductVariant.DoesNotExist:
            return Response({'error': 'نوع محصول یافت نشد'}, status=404)
    
    # Check stock
    available_stock = variant.stock_quantity if variant else product.stock_quantity
    if available_stock < quantity:
        return Response({'error': 'موجودی کافی نیست'}, status=400)
    
    # Get or create cart
    cart, created = Cart.objects.get_or_create(
        customer=request.user,
        store=product.store
    )
    
    # Add or update cart item
    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
        product_variant=variant,
        defaults={'quantity': quantity}
    )
    
    if not created:
        cart_item.quantity += quantity
        cart_item.save()
    
    return Response({
        'message': 'محصول به سبد خرید اضافه شد',
        'cart_item': CartItemSerializer(cart_item).data
    })

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def update_cart_item(request, item_id):
    """Update cart item quantity"""
    try:
        cart_item = CartItem.objects.get(
            id=item_id,
            cart__customer=request.user
        )
    except CartItem.DoesNotExist:
        return Response({'error': 'آیتم یافت نشد'}, status=404)
    
    quantity = int(request.data.get('quantity', 1))
    
    if quantity <= 0:
        cart_item.delete()
        return Response({'message': 'آیتم از سبد حذف شد'})
    
    # Check stock
    available_stock = (cart_item.product_variant.stock_quantity 
                      if cart_item.product_variant 
                      else cart_item.product.stock_quantity)
    
    if available_stock < quantity:
        return Response({'error': 'موجودی کافی نیست'}, status=400)
    
    cart_item.quantity = quantity
    cart_item.save()
    
    return Response({
        'message': 'تعداد به‌روزرسانی شد',
        'cart_item': CartItemSerializer(cart_item).data
    })

@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def remove_from_cart(request, item_id):
    """Remove item from cart"""
    try:
        cart_item = CartItem.objects.get(
            id=item_id,
            cart__customer=request.user
        )
        cart_item.delete()
        return Response({'message': 'آیتم از سبد حذف شد'})
    except CartItem.DoesNotExist:
        return Response({'error': 'آیتم یافت نشد'}, status=404)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def clear_cart(request):
    """Clear user's cart"""
    store_id = request.data.get('store_id')
    if store_id:
        Cart.objects.filter(
            customer=request.user,
            store_id=store_id
        ).delete()
    else:
        Cart.objects.filter(customer=request.user).delete()
    
    return Response({'message': 'سبد خرید خالی شد'})

class WishlistViewSet(viewsets.ModelViewSet):
    """Wishlist management"""
    serializer_class = WishlistSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Wishlist.objects.filter(customer=self.request.user)
    
    def perform_create(self, serializer):
        product_id = self.request.data.get('product')
        product = get_object_or_404(Product, id=product_id)
        
        # Check if already in wishlist
        if Wishlist.objects.filter(
            customer=self.request.user,
            product=product
        ).exists():
            return Response({'error': 'محصول در لیست علاقه‌مندی موجود است'}, status=400)
        
        serializer.save(
            customer=self.request.user,
            product=product,
            store=product.store
        )

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def add_to_wishlist(request):
    """Add product to wishlist"""
    product_id = request.data.get('product_id')
    
    try:
        product = Product.objects.get(id=product_id, status='published')
    except Product.DoesNotExist:
        return Response({'error': 'محصول یافت نشد'}, status=404)
    
    wishlist_item, created = Wishlist.objects.get_or_create(
        customer=request.user,
        product=product,
        store=product.store
    )
    
    if created:
        return Response({'message': 'محصول به لیست علاقه‌مندی اضافه شد'})
    else:
        return Response({'message': 'محصول در لیست علاقه‌مندی موجود است'})

@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def remove_from_wishlist(request, product_id):
    """Remove product from wishlist"""
    try:
        wishlist_item = Wishlist.objects.get(
            customer=request.user,
            product_id=product_id
        )
        wishlist_item.delete()
        return Response({'message': 'محصول از لیست علاقه‌مندی حذف شد'})
    except Wishlist.DoesNotExist:
        return Response({'error': 'محصول در لیست علاقه‌مندی یافت نشد'}, status=404)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def order_history(request):
    """Get customer order history"""
    orders = Order.objects.filter(customer=request.user).order_by('-created_at')
    serializer = OrderSerializer(orders, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def order_analytics(request):
    """Get order analytics for store owner"""
    store_id = request.query_params.get('store')
    if not store_id:
        return Response({'error': 'Store ID required'}, status=400)
    
    try:
        from apps.stores.models import Store
        store = Store.objects.get(id=store_id, owner=request.user)
    except Store.DoesNotExist:
        return Response({'error': 'Store not found'}, status=404)
    
    orders = Order.objects.filter(store=store)
    
    analytics = {
        'total_orders': orders.count(),
        'pending_orders': orders.filter(status='pending').count(),
        'completed_orders': orders.filter(status='delivered').count(),
        'total_revenue': orders.filter(payment_status='paid').aggregate(
            total=Sum('total_amount')
        )['total'] or 0,
        'average_order_value': orders.filter(payment_status='paid').aggregate(
            avg=models.Avg('total_amount')
        )['avg'] or 0,
    }
    
    return Response(analytics)

class CheckoutView(APIView):
    """Complete order checkout process"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        """Process checkout"""
        cart_id = request.data.get('cart_id')
        shipping_info = request.data.get('shipping_info', {})
        payment_method = request.data.get('payment_method', 'online')
        
        try:
            cart = Cart.objects.get(id=cart_id, customer=request.user)
        except Cart.DoesNotExist:
            return Response({'error': 'سبد خرید یافت نشد'}, status=404)
        
        if not cart.items.exists():
            return Response({'error': 'سبد خرید خالی است'}, status=400)
        
        with transaction.atomic():
            # Create order
            order = Order.objects.create(
                store=cart.store,
                customer=request.user,
                customer_name=shipping_info.get('name', ''),
                customer_phone=shipping_info.get('phone', ''),
                customer_email=shipping_info.get('email', ''),
                shipping_address=shipping_info.get('address', ''),
                shipping_city=shipping_info.get('city', ''),
                shipping_state=shipping_info.get('state', ''),
                shipping_postal_code=shipping_info.get('postal_code', ''),
                payment_method=payment_method,
                subtotal=cart.total_amount,
                total_amount=cart.total_amount,
            )
            
            # Create order items
            for cart_item in cart.items.all():
                OrderItem.objects.create(
                    order=order,
                    product=cart_item.product,
                    product_variant=cart_item.product_variant,
                    quantity=cart_item.quantity,
                    unit_price=cart_item.unit_price,
                    total_price=cart_item.total_price,
                    product_name=cart_item.product.name_fa,
                    product_sku=cart_item.product.sku or ''
                )
            
            # Clear cart
            cart.delete()
        
        return Response({
            'message': 'سفارش با موفقیت ثبت شد',
            'order_id': order.id,
            'order_number': order.order_number
        })
