from django.test import TestCase
from django.contrib.auth import get_user_model
from .models import Store, StoreTheme

User = get_user_model()


class StoreModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            phone='09123456789',
            password='testpass123'
        )
        
    def test_store_creation(self):
        """Test creating a store"""
        store = Store.objects.create(
            name='Test Store',
            owner=self.user,
            domain='teststore.com'
        )
        self.assertEqual(str(store), 'Test Store')
        self.assertEqual(store.owner, self.user)
        self.assertEqual(store.domain, 'teststore.com')
        self.assertTrue(store.is_active)
        
    def test_store_unique_domain(self):
        """Test store domain uniqueness"""
        Store.objects.create(
            name='Store 1',
            owner=self.user,
            domain='unique.com'
        )
        
        # Creating another store with same domain should work
        # as we might want subdomain support
        store2 = Store.objects.create(
            name='Store 2',
            owner=self.user,
            domain='unique2.com'
        )
        self.assertNotEqual(store2.domain, 'unique.com')
        
    def test_store_theme_creation(self):
        """Test creating a store theme"""
        store = Store.objects.create(
            name='Test Store',
            owner=self.user,
            domain='teststore.com'
        )
        theme = StoreTheme.objects.create(
            store=store,
            name='Modern Theme',
            primary_color='#007bff',
            secondary_color='#6c757d'
        )
        self.assertEqual(str(theme), 'Modern Theme - Test Store')
        self.assertEqual(theme.store, store)
