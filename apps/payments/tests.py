from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.stores.models import Store
from apps.orders.models import Order
from .models import PaymentGateway, Payment

User = get_user_model()

class PaymentModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            phone='09123456789',
            username='testuser'
        )
        self.store = Store.objects.create(
            owner=self.user,
            name='Test Store',
            name_fa='فروشگاه تست',
            slug='test-store',
            subdomain='test'
        )
    
    def test_payment_gateway_creation(self):
        gateway = PaymentGateway.objects.create(
            store=self.store,
            gateway='zarinpal',
            merchant_id='test-merchant-id'
        )
        self.assertEqual(gateway.store, self.store)
        self.assertEqual(gateway.gateway, 'zarinpal')
        self.assertTrue(gateway.is_active)
        self.assertTrue(gateway.is_sandbox)
    
    def test_payment_creation(self):
        gateway = PaymentGateway.objects.create(
            store=self.store,
            gateway='zarinpal',
            merchant_id='test-merchant-id'
        )
        
        order = Order.objects.create(
            store=self.store,
            customer=self.user,
            customer_name='Test User',
            customer_phone='09123456789',
            shipping_address='Test Address',
            shipping_city='Tehran',
            shipping_state='Tehran',
            subtotal=100000,
            total_amount=100000
        )
        
        payment = Payment.objects.create(
            order=order,
            gateway=gateway,
            amount=100000
        )
        
        self.assertEqual(payment.order, order)
        self.assertEqual(payment.gateway, gateway)
        self.assertEqual(payment.amount, 100000)
        self.assertEqual(payment.status, 'pending')
