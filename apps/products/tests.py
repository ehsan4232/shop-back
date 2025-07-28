from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.stores.models import Store
from .models import Product, ProductClass, ProductAttribute, ProductInstance

User = get_user_model()


class ProductModelTest(TestCase):
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
        
    def test_product_class_creation(self):
        """Test creating a product class"""
        product_class = ProductClass.objects.create(
            name='Electronics',
            store=self.store
        )
        self.assertEqual(str(product_class), 'Electronics')
        
    def test_product_hierarchy(self):
        """Test product class hierarchy"""
        electronics = ProductClass.objects.create(
            name='Electronics',
            store=self.store
        )
        phones = ProductClass.objects.create(
            name='Phones',
            parent=electronics,
            store=self.store
        )
        self.assertEqual(phones.parent, electronics)
        self.assertIn(phones, electronics.get_children())
        
    def test_product_creation(self):
        """Test creating a product"""
        product_class = ProductClass.objects.create(
            name='Books',
            store=self.store
        )
        product = Product.objects.create(
            name='Test Book',
            product_class=product_class,
            base_price=10.99
        )
        self.assertEqual(str(product), 'Test Book')
        self.assertEqual(product.base_price, 10.99)
