import requests
import json
import logging
from typing import Dict, List, Optional, Tuple
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from .models import SocialMediaAccount, SocialMediaPost
from apps.products.models import Product, ProductImage

logger = logging.getLogger(__name__)

class SocialMediaImportError(Exception):
    """Custom exception for social media import errors"""
    pass

class TelegramImporter:
    """
    Telegram Bot API integration for importing posts and media
    """
    
    def __init__(self, bot_token: str):
        self.bot_token = bot_token
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
    
    def get_channel_posts(self, channel_username: str, limit: int = 5) -> List[Dict]:
        """
        Get recent posts from a Telegram channel
        Note: This requires the bot to be an admin in the channel
        """
        try:
            # Get channel info first
            response = requests.get(
                f"{self.base_url}/getChat",
                params={"chat_id": f"@{channel_username}"},
                timeout=30
            )
            response.raise_for_status()
            channel_data = response.json()
            
            if not channel_data.get('ok'):
                raise SocialMediaImportError(f"Failed to get channel info: {channel_data.get('description')}")
            
            channel_id = channel_data['result']['id']
            
            # Get recent messages
            # Note: This is a simplified implementation
            # In practice, you'd need to store message IDs and iterate through them
            posts = []
            
            # For demo purposes, we'll return mock data
            # In real implementation, you'd use getUpdates or webhook to get messages
            mock_posts = [
                {
                    'message_id': 1,
                    'text': 'محصول جدید: کیف چرمی فوق‌العاده #bag #leather',
                    'date': 1640995200,
                    'photo': [
                        {
                            'file_id': 'mock_file_id_1',
                            'file_unique_id': 'mock_unique_1',
                            'width': 1280,
                            'height': 960,
                            'file_size': 125000
                        }
                    ]
                }
            ]
            
            return mock_posts[:limit]
            
        except requests.RequestException as e:
            logger.error(f"Telegram API error: {e}")
            raise SocialMediaImportError(f"Failed to connect to Telegram: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in Telegram import: {e}")
            raise SocialMediaImportError(f"Unexpected error: {e}")
    
    def download_file(self, file_id: str) -> Tuple[bytes, str]:
        """
        Download file from Telegram
        """
        try:
            # Get file info
            response = requests.get(
                f"{self.base_url}/getFile",
                params={"file_id": file_id},
                timeout=30
            )
            response.raise_for_status()
            file_data = response.json()
            
            if not file_data.get('ok'):
                raise SocialMediaImportError(f"Failed to get file info: {file_data.get('description')}")
            
            file_path = file_data['result']['file_path']
            file_url = f"https://api.telegram.org/file/bot{self.bot_token}/{file_path}"
            
            # Download the actual file
            file_response = requests.get(file_url, timeout=60)
            file_response.raise_for_status()
            
            return file_response.content, file_path.split('/')[-1]
            
        except requests.RequestException as e:
            logger.error(f"File download error: {e}")
            raise SocialMediaImportError(f"Failed to download file: {e}")

class InstagramImporter:
    """
    Instagram Basic Display API integration
    """
    
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.base_url = "https://graph.instagram.com"
    
    def get_user_media(self, limit: int = 5) -> List[Dict]:
        """
        Get user's recent media posts
        """
        try:
            response = requests.get(
                f"{self.base_url}/me/media",
                params={
                    "fields": "id,media_type,media_url,thumbnail_url,caption,timestamp,permalink",
                    "limit": limit,
                    "access_token": self.access_token
                },
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            if 'error' in data:
                raise SocialMediaImportError(f"Instagram API error: {data['error']['message']}")
            
            return data.get('data', [])
            
        except requests.RequestException as e:
            logger.error(f"Instagram API error: {e}")
            raise SocialMediaImportError(f"Failed to connect to Instagram: {e}")
    
    def download_media(self, media_url: str) -> Tuple[bytes, str]:
        """
        Download media from Instagram
        """
        try:
            response = requests.get(media_url, timeout=60)
            response.raise_for_status()
            
            # Extract filename from URL
            filename = media_url.split('/')[-1].split('?')[0]
            if not filename or '.' not in filename:
                filename = f"instagram_media.jpg"
            
            return response.content, filename
            
        except requests.RequestException as e:
            logger.error(f"Media download error: {e}")
            raise SocialMediaImportError(f"Failed to download media: {e}")

class SocialMediaService:
    """
    Main service for social media integration
    """
    
    def __init__(self):
        self.telegram_bot_token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
        self.instagram_app_id = getattr(settings, 'INSTAGRAM_APP_ID', None)
    
    def import_from_telegram(self, store, channel_username: str, limit: int = 5) -> Dict:
        """
        Import posts from Telegram channel
        """
        if not self.telegram_bot_token:
            raise SocialMediaImportError("Telegram bot token not configured")
        
        importer = TelegramImporter(self.telegram_bot_token)
        results = {
            'imported': 0,
            'failed': 0,
            'errors': []
        }
        
        try:
            posts = importer.get_channel_posts(channel_username, limit)
            
            for post_data in posts:
                try:
                    # Create social media post record
                    social_post = SocialMediaPost.objects.create(
                        store=store,
                        platform='telegram',
                        external_id=str(post_data['message_id']),
                        content=post_data.get('text', ''),
                        post_url=f"https://t.me/{channel_username}/{post_data['message_id']}",
                        published_at=post_data['date'],
                        raw_data=post_data
                    )
                    
                    # Process media if available
                    if 'photo' in post_data:
                        try:
                            photo = post_data['photo'][-1]  # Get largest photo
                            file_content, filename = importer.download_file(photo['file_id'])
                            
                            # Save file
                            file_path = default_storage.save(
                                f"social_media/telegram/{filename}",
                                ContentFile(file_content)
                            )
                            
                            social_post.media_files.append({
                                'type': 'image',
                                'file_path': file_path,
                                'original_url': f"telegram_file_{photo['file_id']}"
                            })
                            social_post.save()
                            
                        except Exception as e:
                            logger.error(f"Failed to download media for post {post_data['message_id']}: {e}")
                    
                    results['imported'] += 1
                    
                except Exception as e:
                    logger.error(f"Failed to import post {post_data.get('message_id')}: {e}")
                    results['failed'] += 1
                    results['errors'].append(str(e))
            
        except SocialMediaImportError as e:
            results['errors'].append(str(e))
        
        return results
    
    def import_from_instagram(self, store, access_token: str, limit: int = 5) -> Dict:
        """
        Import posts from Instagram
        """
        importer = InstagramImporter(access_token)
        results = {
            'imported': 0,
            'failed': 0,
            'errors': []
        }
        
        try:
            posts = importer.get_user_media(limit)
            
            for post_data in posts:
                try:
                    # Create social media post record
                    social_post = SocialMediaPost.objects.create(
                        store=store,
                        platform='instagram',
                        external_id=post_data['id'],
                        content=post_data.get('caption', ''),
                        post_url=post_data.get('permalink', ''),
                        published_at=post_data.get('timestamp'),
                        raw_data=post_data
                    )
                    
                    # Process media
                    if post_data.get('media_url'):
                        try:
                            file_content, filename = importer.download_media(post_data['media_url'])
                            
                            # Save file
                            file_path = default_storage.save(
                                f"social_media/instagram/{filename}",
                                ContentFile(file_content)
                            )
                            
                            social_post.media_files.append({
                                'type': post_data.get('media_type', 'image').lower(),
                                'file_path': file_path,
                                'original_url': post_data['media_url']
                            })
                            social_post.save()
                            
                        except Exception as e:
                            logger.error(f"Failed to download media for post {post_data['id']}: {e}")
                    
                    results['imported'] += 1
                    
                except Exception as e:
                    logger.error(f"Failed to import post {post_data.get('id')}: {e}")
                    results['failed'] += 1
                    results['errors'].append(str(e))
            
        except SocialMediaImportError as e:
            results['errors'].append(str(e))
        
        return results
    
    def create_product_from_social_post(self, store, social_post: SocialMediaPost, category_id: str) -> Optional[Product]:
        """
        Create a product from a social media post
        """
        try:
            from apps.products.models import ProductCategory
            
            category = ProductCategory.objects.get(id=category_id, store=store)
            
            # Extract product name from content
            content = social_post.content or ""
            lines = content.split('\n')
            product_name = lines[0] if lines else f"محصول از {social_post.platform}"
            
            # Clean up name (remove hashtags, mentions, etc.)
            import re
            product_name = re.sub(r'#\w+', '', product_name)
            product_name = re.sub(r'@\w+', '', product_name)
            product_name = product_name.strip()
            
            if not product_name:
                product_name = f"محصول از {social_post.platform}"
            
            # Create product
            product = Product.objects.create(
                store=store,
                category=category,
                name=product_name[:100],  # Limit length
                name_fa=product_name[:100],
                description=content,
                price=0,  # Will need to be set manually
                status='draft',
                imported_from_social=True,
                social_media_source=social_post.platform,
                social_media_post_id=social_post.external_id
            )
            
            # Add images from social post
            for media in social_post.media_files:
                if media['type'] == 'image':
                    ProductImage.objects.create(
                        product=product,
                        image=media['file_path'],
                        imported_from_social=True,
                        social_media_url=media['original_url']
                    )
            
            # Mark social post as processed
            social_post.is_processed = True
            social_post.created_product = product
            social_post.save()
            
            return product
            
        except Exception as e:
            logger.error(f"Failed to create product from social post {social_post.id}: {e}")
            return None
    
    def bulk_import_as_products(self, store, social_post_ids: List[str], category_id: str) -> Dict:
        """
        Bulk import social posts as products
        """
        results = {
            'created': 0,
            'failed': 0,
            'errors': []
        }
        
        social_posts = SocialMediaPost.objects.filter(
            id__in=social_post_ids,
            store=store,
            is_processed=False
        )
        
        for social_post in social_posts:
            product = self.create_product_from_social_post(store, social_post, category_id)
            if product:
                results['created'] += 1
            else:
                results['failed'] += 1
                results['errors'].append(f"Failed to create product from post {social_post.id}")
        
        return results
    
    def get_account_connection_url(self, platform: str, store_id: str) -> str:
        """
        Get URL for connecting social media accounts
        """
        if platform == 'instagram':
            if not self.instagram_app_id:
                raise SocialMediaImportError("Instagram app ID not configured")
            
            redirect_uri = f"{settings.SITE_URL}/api/social-media/instagram/callback/"
            scope = "user_profile,user_media"
            
            return (
                f"https://api.instagram.com/oauth/authorize"
                f"?client_id={self.instagram_app_id}"
                f"&redirect_uri={redirect_uri}"
                f"&scope={scope}"
                f"&response_type=code"
                f"&state={store_id}"
            )
        elif platform == 'telegram':
            # For Telegram, users need to add the bot to their channel
            bot_username = getattr(settings, 'TELEGRAM_BOT_USERNAME', 'your_bot')
            return f"https://t.me/{bot_username}?startgroup=true"
        
        raise SocialMediaImportError(f"Unsupported platform: {platform}")

# Utility functions for content processing
def extract_hashtags(text: str) -> List[str]:
    """Extract hashtags from text"""
    import re
    return re.findall(r'#(\w+)', text)

def extract_mentions(text: str) -> List[str]:
    """Extract mentions from text"""
    import re
    return re.findall(r'@(\w+)', text)

def clean_product_name(text: str) -> str:
    """Clean text to make it suitable for product name"""
    import re
    # Remove hashtags and mentions
    text = re.sub(r'#\w+', '', text)
    text = re.sub(r'@\w+', '', text)
    # Remove extra whitespace
    text = ' '.join(text.split())
    return text.strip()

def detect_price_in_text(text: str) -> Optional[int]:
    """Try to detect price in text (Persian/English numbers)"""
    import re
    
    # Persian to English number conversion
    persian_to_english = {
        '۰': '0', '۱': '1', '۲': '2', '۳': '3', '۴': '4',
        '۵': '5', '۶': '6', '۷': '7', '۸': '8', '۹': '9'
    }
    
    # Convert Persian numbers to English
    for persian, english in persian_to_english.items():
        text = text.replace(persian, english)
    
    # Look for price patterns
    patterns = [
        r'(\d{1,3}(?:,\d{3})*)\s*(?:تومان|ریال|درهم)',
        r'قیمت[:\s]*(\d{1,3}(?:,\d{3})*)',
        r'(\d{1,3}(?:,\d{3})*)\s*(?:هزار\s*)?تومان'
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text)
        if matches:
            try:
                # Remove commas and convert to int
                price_str = matches[0].replace(',', '')
                return int(price_str)
            except ValueError:
                continue
    
    return None
