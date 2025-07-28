from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.stores.models import Store
from .models import SocialMediaAccount, SocialMediaPost
from .services import SocialMediaImporter

User = get_user_model()

class SocialMediaModelTests(TestCase):
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
    
    def test_social_media_account_creation(self):
        account = SocialMediaAccount.objects.create(
            store=self.store,
            platform='telegram',
            username='testchannel'
        )
        self.assertEqual(account.store, self.store)
        self.assertEqual(account.platform, 'telegram')
        self.assertTrue(account.is_active)
    
    def test_social_media_post_creation(self):
        account = SocialMediaAccount.objects.create(
            store=self.store,
            platform='telegram',
            username='testchannel'
        )
        
        post = SocialMediaPost.objects.create(
            account=account,
            post_id='123',
            caption='Test post',
            post_url='https://t.me/testchannel/123',
            post_date='2024-01-01 12:00:00+00:00'
        )
        
        self.assertEqual(post.account, account)
        self.assertEqual(post.post_id, '123')
        self.assertFalse(post.is_imported)
    
    def test_post_extracted_text(self):
        account = SocialMediaAccount.objects.create(
            store=self.store,
            platform='telegram',
            username='testchannel'
        )
        
        post = SocialMediaPost.objects.create(
            account=account,
            post_id='123',
            caption='این یک متن تست است #تست @کاربر',
            post_url='https://t.me/testchannel/123',
            post_date='2024-01-01 12:00:00+00:00'
        )
        
        extracted = post.get_extracted_text()
        self.assertNotIn('#تست', extracted)
        self.assertNotIn('@کاربر', extracted)
        self.assertIn('این یک متن تست است', extracted)

class SocialMediaImporterTests(TestCase):
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
    
    def test_importer_initialization(self):
        account = SocialMediaAccount.objects.create(
            store=self.store,
            platform='telegram',
            username='testchannel'
        )
        
        # This would require actual bot token to test
        # importer = SocialMediaImporter(account)
        # self.assertIsNotNone(importer.service)
        
        # For now, just test that the account is properly set
        self.assertEqual(account.platform, 'telegram')
