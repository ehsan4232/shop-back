from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

User = get_user_model()


class CustomUserModelTest(TestCase):
    def test_create_user_with_phone(self):
        """Test creating a user with phone number"""
        user = User.objects.create_user(
            phone='09123456789',
            password='testpass123'
        )
        self.assertEqual(user.phone, '09123456789')
        self.assertTrue(user.check_password('testpass123'))
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        
    def test_create_superuser(self):
        """Test creating a superuser"""
        admin_user = User.objects.create_superuser(
            phone='09123456780',
            password='adminpass123'
        )
        self.assertEqual(admin_user.phone, '09123456780')
        self.assertTrue(admin_user.is_active)
        self.assertTrue(admin_user.is_staff)
        self.assertTrue(admin_user.is_superuser)
        
    def test_user_string_representation(self):
        """Test user string representation"""
        user = User.objects.create_user(
            phone='09123456789',
            password='testpass123'
        )
        self.assertEqual(str(user), '09123456789')
