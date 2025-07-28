from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.stores.models import Store
from apps.products.models import Product, ProductClass, ProductInstance
from .models import Order, OrderItem, ShippingAddress
from decimal import Decimal

User = get_user_model()


class OrderModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            phone='09123456789',
            password='testpass123'
        )
        self.store = Store.objects.create(
            name='Test Store',
            owner=self.user,
            domain='teststore.com'
        )
        self.product_class = ProductClass.objects.create(
            name='Books',
            store=self.store
        )
        self.product = Product.objects.create(
            name='Test Book',
            product_class=self.product_class,
            base_price=Decimal('10.99')
        )
        self.product_instance = ProductInstance.objects.create(
            product=self.product,
            stock_quantity=100,
            price=Decimal('10.99')
        )
        
    def test_order_creation(self):
        """Test creating an order"""
        order = Order.objects.create(
            customer=self.user,
            store=self.store,
            status='pending',
            total_amount=Decimal('10.99')
        )
        self.assertEqual(order.customer, self.user)
        self.assertEqual(order.store, self.store)
        self.assertEqual(order.status, 'pending')
        self.assertEqual(order.total_amount, Decimal('10.99'))
        
    def test_order_item_creation(self):
        """Test creating order items"""
        order = Order.objects.create(
            customer=self.user,
            store=self.store,
            status='pending',
            total_amount=Decimal('21.98')
        )
        order_item = OrderItem.objects.create(
            order=order,
            product_instance=self.product_instance,
            quantity=2,
            price=Decimal('10.99')
        )
        self.assertEqual(order_item.order, order)
        self.assertEqual(order_item.quantity, 2)
        self.assertEqual(order_item.get_total(), Decimal('21.98'))
        
    def test_shipping_address_creation(self):
        """Test creating shipping address"""
        order = Order.objects.create(
            customer=self.user,
            store=self.store,
            status='pending',
            total_amount=Decimal('10.99')
        )
        address = ShippingAddress.objects.create(
            order=order,
            full_name='John Doe',
            address_line_1='123 Main St',
            city='Tehran',
            postal_code='1234567890',
            phone='09123456789'
        )
        self.assertEqual(address.order, order)
        self.assertEqual(address.full_name, 'John Doe')
        self.assertEqual(address.city, 'Tehran')
