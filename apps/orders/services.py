from typing import Dict, List, Optional, Tuple
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.conf import settings
from django.core.exceptions import ValidationError
from .models import Order, OrderItem, Cart, CartItem
from apps.products.models import Product, ProductVariant
import logging

logger = logging.getLogger(__name__)

class OrderError(Exception):
    """Custom exception for order processing errors"""
    pass

class InventoryError(Exception):
    """Custom exception for inventory-related errors"""
    pass

class OrderService:
    """
    Complete order processing service
    """
    
    def validate_cart_for_checkout(self, cart: Cart) -> Tuple[bool, str]:
        """
        Validate cart before checkout
        """
        if not cart.items.exists():
            return False, "سبد خرید خالی است"
        
        # Check stock availability
        for item in cart.items.all():
            if not self._check_item_stock(item):
                return False, f"موجودی کافی برای {item.product.name_fa} وجود ندارد"
        
        # Check minimum order amount
        min_order_amount = getattr(settings, 'MIN_ORDER_AMOUNT', 10000)
        if cart.final_amount < min_order_amount:
            return False, f"حداقل مبلغ سفارش {min_order_amount:,} تومان است"
        
        return True, ""
    
    def _check_item_stock(self, cart_item: CartItem) -> bool:
        """
        Check if cart item has sufficient stock
        """
        if cart_item.variant:
            return cart_item.variant.stock_quantity >= cart_item.quantity
        else:
            return cart_item.product.stock_quantity >= cart_item.quantity
    
    @transaction.atomic
    def create_order_from_cart(
        self, 
        cart: Cart, 
        customer_info: Dict, 
        shipping_info: Dict,
        payment_method: str = 'zarinpal'
    ) -> Order:
        """
        Create order from cart with inventory reservation
        """
        try:
            # Validate cart
            is_valid, error_message = self.validate_cart_for_checkout(cart)
            if not is_valid:
                raise OrderError(error_message)
            
            # Reserve inventory
            reserved_items = self._reserve_inventory(cart)
            
            try:
                # Create order
                order = Order.objects.create(
                    store=cart.store,
                    customer=cart.user,
                    customer_first_name=customer_info['first_name'],
                    customer_last_name=customer_info['last_name'],
                    customer_phone=customer_info['phone'],
                    customer_email=customer_info.get('email', ''),
                    shipping_address=shipping_info['address'],
                    shipping_city=shipping_info['city'],
                    shipping_state=shipping_info['state'],
                    shipping_postal_code=shipping_info['postal_code'],
                    subtotal=cart.total_amount,
                    tax_amount=cart.tax_amount,
                    shipping_amount=cart.shipping_amount,
                    discount_amount=cart.discount_amount,
                    total_amount=cart.final_amount,
                    coupon_code=cart.coupon_code,
                    shipping_method=shipping_info.get('method', 'standard'),
                    notes=customer_info.get('notes', ''),
                    status='pending',
                    payment_status='pending'
                )
                
                # Create order items
                for cart_item in cart.items.all():
                    OrderItem.objects.create(
                        order=order,
                        product=cart_item.product,
                        variant=cart_item.variant,
                        quantity=cart_item.quantity,
                        unit_price=cart_item.unit_price,
                        total_price=cart_item.total_price,
                        product_name=cart_item.product.name_fa,
                        product_sku=cart_item.variant.sku if cart_item.variant else cart_item.product.sku,
                        custom_attributes=cart_item.custom_attributes
                    )
                
                # Clear cart
                cart.clear()
                
                return order
                
            except Exception as e:
                # Rollback inventory reservation
                self._rollback_inventory_reservation(reserved_items)
                raise OrderError(f"خطا در ایجاد سفارش: {e}")
                
        except InventoryError as e:
            raise OrderError(str(e))
        except Exception as e:
            logger.error(f"Order creation error: {e}")
            raise OrderError(f"خطای غیرمنتظره: {e}")
    
    def _reserve_inventory(self, cart: Cart) -> List[Dict]:
        """
        Reserve inventory for cart items
        """
        reserved_items = []
        
        try:
            for cart_item in cart.items.all():
                if cart_item.variant:
                    # Reserve variant stock
                    variant = cart_item.variant
                    if variant.stock_quantity < cart_item.quantity:
                        raise InventoryError(f"موجودی کافی برای {cart_item.product.name_fa} وجود ندارد")
                    
                    reserved_items.append({
                        'type': 'variant',
                        'item': variant,
                        'quantity': cart_item.quantity,
                        'original_stock': variant.stock_quantity
                    })
                    
                    variant.stock_quantity -= cart_item.quantity
                    variant.save()
                    
                else:
                    # Reserve product stock
                    product = cart_item.product
                    if product.stock_quantity < cart_item.quantity:
                        raise InventoryError(f"موجودی کافی برای {product.name_fa} وجود ندارد")
                    
                    reserved_items.append({
                        'type': 'product',
                        'item': product,
                        'quantity': cart_item.quantity,
                        'original_stock': product.stock_quantity
                    })
                    
                    product.stock_quantity -= cart_item.quantity
                    product.save()
            
            return reserved_items
            
        except Exception as e:
            # Rollback any partial reservations
            self._rollback_inventory_reservation(reserved_items)
            raise InventoryError(f"خطا در رزرو موجودی: {e}")
    
    def _rollback_inventory_reservation(self, reserved_items: List[Dict]):
        """
        Rollback inventory reservations
        """
        for reservation in reserved_items:
            try:
                item = reservation['item']
                item.stock_quantity = reservation['original_stock']
                item.save()
            except Exception as e:
                logger.error(f"Failed to rollback inventory for {item}: {e}")
    
    def update_order_status(self, order: Order, new_status: str, notes: str = "", user=None) -> bool:
        """
        Update order status with proper workflow validation
        """
        try:
            # Validate status transition
            if not self._is_valid_status_transition(order.status, new_status):
                raise OrderError(f"تغییر وضعیت مجاز نیست")
            
            old_status = order.status
            
            # Handle status-specific logic
            if new_status == 'shipped':
                order.shipped_at = timezone.now()
                if not order.tracking_number:
                    order.tracking_number = self._generate_tracking_number(order)
            elif new_status == 'delivered':
                order.delivered_at = timezone.now()
                # Update product sales count
                for item in order.items.all():
                    item.product.increment_sales_count(item.quantity)
            elif new_status == 'cancelled':
                self._handle_cancelled_status(order)
            
            # Update order
            order.status = new_status
            if notes:
                order.admin_notes += f"\n{timezone.now()}: {notes}"
            order.save()
            
            # Create status history
            from .models import OrderStatusHistory
            OrderStatusHistory.objects.create(
                order=order,
                old_status=old_status,
                new_status=new_status,
                notes=notes,
                changed_by=user
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Order status update error: {e}")
            raise OrderError(f"خطا در به‌روزرسانی وضعیت: {e}")
    
    def _is_valid_status_transition(self, current_status: str, new_status: str) -> bool:
        """
        Validate if status transition is allowed
        """
        valid_transitions = {
            'pending': ['paid', 'cancelled'],
            'paid': ['processing', 'cancelled'],
            'processing': ['shipped', 'cancelled'],
            'shipped': ['delivered', 'cancelled'],
            'delivered': ['refunded'],
            'cancelled': [],
            'refunded': []
        }
        
        return new_status in valid_transitions.get(current_status, [])
    
    def _handle_cancelled_status(self, order: Order):
        """Handle order cancellation"""
        # Restore inventory
        for item in order.items.all():
            if item.variant:
                item.variant.stock_quantity += item.quantity
                item.variant.save()
            else:
                item.product.stock_quantity += item.quantity
                item.product.save()
        
        order.admin_notes += f"\n{timezone.now()}: سفارش لغو شد - موجودی بازگردانده شد"
    
    def _generate_tracking_number(self, order: Order) -> str:
        """Generate tracking number"""
        import random
        import string
        return f"TR{order.order_number[-6:]}{random.randint(1000, 9999)}"
    
    def get_order_analytics(self, store, start_date=None, end_date=None) -> Dict:
        """
        Get order analytics for store
        """
        from django.db.models import Sum, Count, Avg
        from datetime import datetime, timedelta
        
        if not start_date:
            start_date = timezone.now() - timedelta(days=30)
        if not end_date:
            end_date = timezone.now()
        
        orders = Order.objects.filter(
            store=store,
            created_at__range=[start_date, end_date]
        )
        
        total_orders = orders.count()
        completed_orders = orders.filter(status='delivered').count()
        total_revenue = orders.filter(
            status__in=['delivered', 'shipped']
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
        
        avg_order_value = orders.aggregate(
            avg=Avg('total_amount')
        )['avg'] or Decimal('0')
        
        # Status breakdown
        status_stats = orders.values('status').annotate(
            count=Count('id'),
            revenue=Sum('total_amount')
        )
        
        return {
            'total_orders': total_orders,
            'completed_orders': completed_orders,
            'completion_rate': (completed_orders / total_orders * 100) if total_orders > 0 else 0,
            'total_revenue': total_revenue,
            'average_order_value': avg_order_value,
            'status_breakdown': list(status_stats),
        }

# Cart service
class CartService:
    """
    Shopping cart management service
    """
    
    def get_or_create_cart(self, store, user=None, session_key=None) -> Cart:
        """
        Get or create cart for user/session
        """
        if user:
            cart, created = Cart.objects.get_or_create(
                user=user,
                store=store,
                defaults={'session_key': session_key}
            )
        else:
            cart, created = Cart.objects.get_or_create(
                session_key=session_key,
                store=store,
                defaults={'user': user}
            )
        
        return cart
    
    def add_to_cart(self, cart: Cart, product: Product, quantity: int = 1, variant: ProductVariant = None) -> CartItem:
        """
        Add item to cart
        """
        # Check stock
        available_stock = variant.stock_quantity if variant else product.stock_quantity
        if available_stock < quantity:
            raise ValidationError("موجودی کافی نیست")
        
        # Get or create cart item
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            variant=variant,
            defaults={
                'quantity': quantity,
                'unit_price': variant.price if variant else product.price
            }
        )
        
        if not created:
            new_quantity = cart_item.quantity + quantity
            if available_stock < new_quantity:
                raise ValidationError("موجودی کافی نیست")
            cart_item.quantity = new_quantity
            cart_item.save()
        
        cart.recalculate_totals()
        return cart_item
    
    def update_cart_item(self, cart: Cart, item_id: str, quantity: int) -> bool:
        """
        Update cart item quantity
        """
        try:
            item = cart.items.get(id=item_id)
            
            if quantity <= 0:
                item.delete()
            else:
                # Check stock
                available_stock = item.variant.stock_quantity if item.variant else item.product.stock_quantity
                if available_stock < quantity:
                    raise ValidationError("موجودی کافی نیست")
                
                item.quantity = quantity
                item.save()
            
            cart.recalculate_totals()
            return True
            
        except CartItem.DoesNotExist:
            return False
    
    def remove_from_cart(self, cart: Cart, item_id: str) -> bool:
        """
        Remove item from cart
        """
        try:
            cart.items.get(id=item_id).delete()
            cart.recalculate_totals()
            return True
        except CartItem.DoesNotExist:
            return False
    
    def clear_cart(self, cart: Cart):
        """
        Clear all items from cart
        """
        cart.items.all().delete()
        cart.recalculate_totals()
    
    def apply_coupon(self, cart: Cart, coupon_code: str) -> Tuple[bool, str]:
        """
        Apply coupon to cart
        """
        # Basic coupon validation (extend as needed)
        valid_coupons = {
            'WELCOME10': 0.1,  # 10% discount
            'SAVE20': 0.2,     # 20% discount
        }
        
        if coupon_code not in valid_coupons:
            return False, "کد تخفیف معتبر نیست"
        
        discount_rate = valid_coupons[coupon_code]
        cart.coupon_code = coupon_code
        cart.discount_amount = cart.total_amount * Decimal(str(discount_rate))
        cart.save()
        cart.recalculate_totals()
        
        return True, f"تخفیف {int(discount_rate * 100)}% اعمال شد"
