from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db import transaction
from decimal import Decimal
import uuid

class Cart(models.Model):
    """Shopping cart for temporary item storage"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, null=True, blank=True)
    store = models.ForeignKey('stores.Store', on_delete=models.CASCADE)
    session_key = models.CharField(max_length=40, null=True, blank=True, verbose_name='کلید جلسه')
    
    # Cart metadata
    total_items = models.PositiveIntegerField(default=0, verbose_name='تعداد کل آیتم‌ها')
    total_amount = models.DecimalField(max_digits=12, decimal_places=0, default=0, verbose_name='مبلغ کل')
    discount_amount = models.DecimalField(max_digits=12, decimal_places=0, default=0, verbose_name='مبلغ تخفیف')
    tax_amount = models.DecimalField(max_digits=12, decimal_places=0, default=0, verbose_name='مبلغ مالیات')
    shipping_amount = models.DecimalField(max_digits=12, decimal_places=0, default=0, verbose_name='هزینه ارسال')
    final_amount = models.DecimalField(max_digits=12, decimal_places=0, default=0, verbose_name='مبلغ نهایی')
    
    # Applied discounts
    coupon_code = models.CharField(max_length=50, blank=True, verbose_name='کد تخفیف')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'سبد خرید'
        verbose_name_plural = 'سبدهای خرید'
        indexes = [
            models.Index(fields=['user', 'store']),
            models.Index(fields=['session_key', 'store']),
            models.Index(fields=['-updated_at']),
        ]
    
    def __str__(self):
        identifier = self.user.phone if self.user else f"Session: {self.session_key}"
        return f"سبد خرید {identifier} - {self.store.name_fa}"
    
    def add_item(self, product, variant=None, quantity=1, custom_price=None):
        """Add item to cart or update quantity if exists"""
        # Check if item already exists
        cart_item, created = CartItem.objects.get_or_create(
            cart=self,
            product=product,
            variant=variant,
            defaults={
                'quantity': quantity,
                'unit_price': custom_price or self.get_item_price(product, variant),
            }
        )
        
        if not created:
            cart_item.quantity += quantity
            cart_item.save()
        
        self.recalculate_totals()
        return cart_item
    
    def update_item_quantity(self, item_id, quantity):
        """Update item quantity"""
        try:
            item = self.items.get(id=item_id)
            if quantity <= 0:
                item.delete()
            else:
                item.quantity = quantity
                item.save()
            
            self.recalculate_totals()
            return True
        except CartItem.DoesNotExist:
            return False
    
    def remove_item(self, item_id):
        """Remove item from cart"""
        try:
            self.items.get(id=item_id).delete()
            self.recalculate_totals()
            return True
        except CartItem.DoesNotExist:
            return False
    
    def clear(self):
        """Clear all items from cart"""
        self.items.all().delete()
        self.recalculate_totals()
    
    def recalculate_totals(self):
        """Recalculate cart totals"""
        items = self.items.all()
        
        self.total_items = sum(item.quantity for item in items)
        self.total_amount = sum(item.total_price for item in items)
        
        # Apply tax
        tax_rate = self.store.tax_rate / 100
        self.tax_amount = self.total_amount * Decimal(str(tax_rate))
        
        # Calculate final amount
        self.final_amount = self.total_amount + self.tax_amount + self.shipping_amount - self.discount_amount
        
        self.save(update_fields=['total_items', 'total_amount', 'tax_amount', 'final_amount'])
    
    def get_item_price(self, product, variant=None):
        """Get price for product/variant"""
        if variant:
            return variant.price
        return product.get_effective_price()
    
    def apply_coupon(self, coupon_code):
        """Apply coupon code to cart"""
        # TODO: Implement coupon validation and discount calculation
        # For now, just store the code
        self.coupon_code = coupon_code
        self.save()
    
    def get_shipping_methods(self):
        """Get available shipping methods for this cart"""
        # TODO: Implement shipping methods based on store configuration
        return []
    
    def can_checkout(self):
        """Check if cart can proceed to checkout"""
        if self.total_items == 0:
            return False, "سبد خرید خالی است"
        
        # Check stock availability
        for item in self.items.all():
            if not item.check_stock():
                return False, f"موجودی کافی برای {item.product.name_fa} وجود ندارد"
        
        return True, ""

class CartItem(models.Model):
    """Individual items in shopping cart"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE)
    variant = models.ForeignKey('products.ProductVariant', on_delete=models.CASCADE, null=True, blank=True)
    
    quantity = models.PositiveIntegerField(default=1, verbose_name='تعداد')
    unit_price = models.DecimalField(max_digits=12, decimal_places=0, verbose_name='قیمت واحد')
    
    # Custom attributes for this cart item
    custom_attributes = models.JSONField(default=dict, blank=True, verbose_name='ویژگی‌های سفارشی')
    notes = models.TextField(blank=True, verbose_name='یادداشت')
    
    added_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['cart', 'product', 'variant']
        verbose_name = 'آیتم سبد خرید'
        verbose_name_plural = 'آیتم‌های سبد خرید'
    
    def __str__(self):
        variant_info = f" - {self.variant}" if self.variant else ""
        return f"{self.product.name_fa}{variant_info} x {self.quantity}"
    
    @property
    def total_price(self):
        """Calculate total price for this item"""
        return self.unit_price * self.quantity
    
    def check_stock(self):
        """Check if requested quantity is available"""
        if self.variant:
            return self.variant.stock_quantity >= self.quantity
        else:
            return self.product.stock_quantity >= self.quantity

class Wishlist(models.Model):
    """Customer wishlists"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='wishlist_items')
    store = models.ForeignKey('stores.Store', on_delete=models.CASCADE)
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE)
    
    # Optional variant for specific product variations
    variant = models.ForeignKey('products.ProductVariant', on_delete=models.CASCADE, null=True, blank=True)
    
    # Additional metadata
    notes = models.TextField(blank=True, verbose_name='یادداشت')
    priority = models.PositiveIntegerField(
        default=1,
        choices=[
            (1, 'کم'),
            (2, 'متوسط'),
            (3, 'زیاد'),
        ],
        verbose_name='اولویت'
    )
    
    # Price tracking
    price_when_added = models.DecimalField(max_digits=12, decimal_places=0, verbose_name='قیمت هنگام افزودن')
    notify_on_discount = models.BooleanField(default=True, verbose_name='اطلاع‌رسانی تخفیف')
    notify_on_availability = models.BooleanField(default=True, verbose_name='اطلاع‌رسانی موجودی')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['customer', 'product', 'variant']
        verbose_name = 'لیست علاقه‌مندی'
        verbose_name_plural = 'لیست‌های علاقه‌مندی'
        indexes = [
            models.Index(fields=['customer', '-created_at']),
            models.Index(fields=['store', '-created_at']),
            models.Index(fields=['product']),
        ]
    
    def __str__(self):
        variant_info = f" - {self.variant}" if self.variant else ""
        return f"{self.customer.full_name} - {self.product.name_fa}{variant_info}"
    
    def save(self, *args, **kwargs):
        # Set price when first added
        if not self.price_when_added:
            self.price_when_added = self.variant.price if self.variant else self.product.get_effective_price()
        super().save(*args, **kwargs)
    
    @property
    def current_price(self):
        """Get current price of the item"""
        return self.variant.price if self.variant else self.product.get_effective_price()
    
    @property
    def price_difference(self):
        """Calculate price difference since added"""
        return self.current_price - self.price_when_added
    
    @property
    def has_discount(self):
        """Check if item is currently discounted"""
        return self.price_difference < 0
    
    @property
    def is_available(self):
        """Check if item is currently in stock"""
        if self.variant:
            return self.variant.stock_quantity > 0
        return self.product.stock_quantity > 0
    
    def move_to_cart(self, quantity=1):
        """Move item from wishlist to cart"""
        if not self.is_available:
            return False, "محصول موجود نیست"
        
        # Get or create cart
        cart, created = Cart.objects.get_or_create(
            user=self.customer,
            store=self.store
        )
        
        # Add to cart
        cart_item = cart.add_item(
            product=self.product,
            variant=self.variant,
            quantity=quantity
        )
        
        return True, cart_item

class Order(models.Model):
    """Customer orders"""
    STATUS_CHOICES = [
        ('pending', 'در انتظار پرداخت'),
        ('paid', 'پرداخت شده'),
        ('processing', 'در حال پردازش'),
        ('shipped', 'ارسال شده'),
        ('delivered', 'تحویل داده شده'),
        ('cancelled', 'لغو شده'),
        ('refunded', 'بازگردانده شده'),
    ]
    
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'در انتظار'),
        ('paid', 'پرداخت شده'),
        ('failed', 'ناموفق'),
        ('refunded', 'بازگردانده شده'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_number = models.CharField(max_length=20, unique=True, verbose_name='شماره سفارش')
    
    # Relations
    store = models.ForeignKey('stores.Store', on_delete=models.CASCADE, related_name='orders')
    customer = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='orders')
    
    # Order information
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='وضعیت')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending', verbose_name='وضعیت پرداخت')
    
    # Customer information
    customer_first_name = models.CharField(max_length=150, verbose_name='نام')
    customer_last_name = models.CharField(max_length=150, verbose_name='نام خانوادگی')
    customer_phone = models.CharField(max_length=15, verbose_name='تلفن')
    customer_email = models.EmailField(blank=True, verbose_name='ایمیل')
    
    # Shipping address
    shipping_address = models.TextField(verbose_name='آدرس ارسال')
    shipping_city = models.CharField(max_length=100, verbose_name='شهر')
    shipping_state = models.CharField(max_length=100, verbose_name='استان')
    shipping_postal_code = models.CharField(max_length=10, verbose_name='کد پستی')
    
    # Billing address (if different)
    billing_address = models.TextField(blank=True, verbose_name='آدرس صورتحساب')
    billing_city = models.CharField(max_length=100, blank=True, verbose_name='شهر صورتحساب')
    billing_state = models.CharField(max_length=100, blank=True, verbose_name='استان صورتحساب')
    billing_postal_code = models.CharField(max_length=10, blank=True, verbose_name='کد پستی صورتحساب')
    
    # Financial information
    subtotal = models.DecimalField(max_digits=12, decimal_places=0, verbose_name='جمع جزء')
    tax_amount = models.DecimalField(max_digits=12, decimal_places=0, default=0, verbose_name='مالیات')
    shipping_amount = models.DecimalField(max_digits=12, decimal_places=0, default=0, verbose_name='هزینه ارسال')
    discount_amount = models.DecimalField(max_digits=12, decimal_places=0, default=0, verbose_name='تخفیف')
    total_amount = models.DecimalField(max_digits=12, decimal_places=0, verbose_name='مبلغ کل')
    
    # Discounts and coupons
    coupon_code = models.CharField(max_length=50, blank=True, verbose_name='کد تخفیف')
    
    # Shipping information
    shipping_method = models.CharField(max_length=100, blank=True, verbose_name='روش ارسال')
    tracking_number = models.CharField(max_length=100, blank=True, verbose_name='کد رهگیری')
    
    # Additional information
    notes = models.TextField(blank=True, verbose_name='یادداشت')
    admin_notes = models.TextField(blank=True, verbose_name='یادداشت مدیر')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='آخرین به‌روزرسانی')
    shipped_at = models.DateTimeField(null=True, blank=True, verbose_name='تاریخ ارسال')
    delivered_at = models.DateTimeField(null=True, blank=True, verbose_name='تاریخ تحویل')
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'سفارش'
        verbose_name_plural = 'سفارشات'
        indexes = [
            models.Index(fields=['store', '-created_at']),
            models.Index(fields=['customer', '-created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['payment_status']),
            models.Index(fields=['order_number']),
        ]
    
    def __str__(self):
        return f"سفارش {self.order_number} - {self.customer.full_name}"
    
    def save(self, *args, **kwargs):
        # Generate order number if not provided
        if not self.order_number:
            self.order_number = self.generate_order_number()
        
        super().save(*args, **kwargs)
    
    def generate_order_number(self):
        """Generate unique order number"""
        import random
        import string
        
        # Format: STORE_PREFIX + YEAR + RANDOM
        prefix = self.store.name[:3].upper() if len(self.store.name) >= 3 else 'ORD'
        year = timezone.now().year
        random_part = ''.join(random.choices(string.digits, k=6))
        
        order_number = f"{prefix}{year}{random_part}"
        
        # Ensure uniqueness
        while Order.objects.filter(order_number=order_number).exists():
            random_part = ''.join(random.choices(string.digits, k=6))
            order_number = f"{prefix}{year}{random_part}"
        
        return order_number
    
    @classmethod
    def create_from_cart(cls, cart, customer_info, shipping_info, payment_method=None):
        """Create order from shopping cart"""
        if not cart.items.exists():
            raise ValidationError("سبد خرید خالی است")
        
        with transaction.atomic():
            # Create order
            order = cls.objects.create(
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
                shipping_method=shipping_info.get('method', ''),
                notes=customer_info.get('notes', ''),
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
                    custom_attributes=cart_item.custom_attributes,
                )
                
                # Reserve stock
                if cart_item.variant:
                    cart_item.variant.stock_quantity -= cart_item.quantity
                    cart_item.variant.save(update_fields=['stock_quantity'])
                else:
                    cart_item.product.stock_quantity -= cart_item.quantity
                    cart_item.product.save(update_fields=['stock_quantity'])
            
            # Clear cart
            cart.clear()
            
            return order
    
    def update_status(self, new_status, notes=None):
        """Update order status with proper validation"""
        old_status = self.status
        self.status = new_status
        
        # Set timestamps based on status
        if new_status == 'shipped' and not self.shipped_at:
            self.shipped_at = timezone.now()
        elif new_status == 'delivered' and not self.delivered_at:
            self.delivered_at = timezone.now()
        
        if notes:
            self.admin_notes += f"\n{timezone.now()}: {notes}"
        
        self.save()
        
        # Create status history
        OrderStatusHistory.objects.create(
            order=self,
            old_status=old_status,
            new_status=new_status,
            notes=notes or '',
        )
        
        # Send notification to customer
        self.send_status_notification()
    
    def send_status_notification(self):
        """Send status update notification to customer"""
        # TODO: Implement SMS/email notification
        pass
    
    def can_cancel(self):
        """Check if order can be cancelled"""
        return self.status in ['pending', 'paid']
    
    def can_refund(self):
        """Check if order can be refunded"""
        return self.status in ['delivered'] and self.payment_status == 'paid'
    
    def calculate_refund_amount(self):
        """Calculate refund amount"""
        # For now, return full amount minus shipping
        return self.total_amount - self.shipping_amount

class OrderItem(models.Model):
    """Individual items in an order"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE)
    variant = models.ForeignKey('products.ProductVariant', on_delete=models.CASCADE, null=True, blank=True)
    
    quantity = models.PositiveIntegerField(verbose_name='تعداد')
    unit_price = models.DecimalField(max_digits=12, decimal_places=0, verbose_name='قیمت واحد')
    total_price = models.DecimalField(max_digits=12, decimal_places=0, verbose_name='قیمت کل')
    
    # Snapshot of product/variant details at time of order
    product_name = models.CharField(max_length=200, verbose_name='نام محصول')
    product_sku = models.CharField(max_length=100, blank=True, verbose_name='کد محصول')
    custom_attributes = models.JSONField(default=dict, blank=True, verbose_name='ویژگی‌ها')
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'آیتم سفارش'
        verbose_name_plural = 'آیتم‌های سفارش'
    
    def __str__(self):
        variant_info = f" - {self.variant}" if self.variant else ""
        return f"{self.product_name}{variant_info} x {self.quantity}"
    
    def save(self, *args, **kwargs):
        # Snapshot product details
        if not self.product_name:
            self.product_name = self.product.name_fa
        if not self.product_sku:
            self.product_sku = self.variant.sku if self.variant else self.product.sku
        
        super().save(*args, **kwargs)

class OrderStatusHistory(models.Model):
    """Order status change history"""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='status_history')
    old_status = models.CharField(max_length=20, verbose_name='وضعیت قبلی')
    new_status = models.CharField(max_length=20, verbose_name='وضعیت جدید')
    notes = models.TextField(blank=True, verbose_name='یادداشت')
    changed_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'تاریخچه وضعیت سفارش'
        verbose_name_plural = 'تاریخچه وضعیت سفارشات'
    
    def __str__(self):
        return f"{self.order.order_number}: {self.old_status} → {self.new_status}"

# Signals for automatic actions
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

@receiver(post_save, sender=OrderItem)
def update_order_totals(sender, instance, **kwargs):
    """Update order totals when items change"""
    order = instance.order
    items = order.items.all()
    
    order.subtotal = sum(item.total_price for item in items)
    # Recalculate total with tax and shipping
    order.total_amount = order.subtotal + order.tax_amount + order.shipping_amount - order.discount_amount
    order.save(update_fields=['subtotal', 'total_amount'])

@receiver(post_save, sender=Order)
def update_store_analytics(sender, instance, created, **kwargs):
    """Update store analytics when order is created/updated"""
    if created:
        # Update store order count
        instance.store.total_orders += 1
        instance.store.save(update_fields=['total_orders'])
        
        # Update product sales count
        for item in instance.items.all():
            item.product.increment_sales_count(item.quantity)

@receiver(post_save, sender=CartItem)
def update_cart_totals(sender, instance, **kwargs):
    """Update cart totals when items change"""
    instance.cart.recalculate_totals()

@receiver(pre_delete, sender=CartItem)
def update_cart_totals_on_delete(sender, instance, **kwargs):
    """Update cart totals when items are deleted"""
    # Schedule recalculation after deletion
    from django.db import transaction
    transaction.on_commit(lambda: instance.cart.recalculate_totals())
