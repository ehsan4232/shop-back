"""
Social Media Integration Service
Handles Telegram and Instagram API integration for content import
"""
import requests
import json
from datetime import datetime, timedelta
from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone
from .models import SocialMediaAccount, SocialMediaPost, ImportSession, MediaDownload
import logging

logger = logging.getLogger(__name__)


class TelegramService:
    """Telegram Bot API integration"""
    
    def __init__(self):
        self.token = settings.TELEGRAM_BOT_TOKEN
        self.base_url = f"https://api.telegram.org/bot{self.token}"
    
    def get_channel_posts(self, channel_username, limit=50):
        """Get posts from a Telegram channel"""
        try:
            # Note: This requires the bot to be admin of the channel
            # Alternative: Use unofficial Telegram API or MTProto
            url = f"{self.base_url}/getUpdates"
            response = requests.get(url)
            
            if response.status_code == 200:
                data = response.json()
                posts = []
                
                for update in data.get('result', [])[:limit]:
                    if 'channel_post' in update:
                        post = update['channel_post']
                        posts.append(self._parse_telegram_post(post))
                
                return posts
            else:
                logger.error(f"Telegram API error: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Error fetching Telegram posts: {e}")
            return []
    
    def _parse_telegram_post(self, post):
        """Parse Telegram post data"""
        media_urls = []
        
        # Handle different media types
        if 'photo' in post:
            # Get the largest photo
            photos = post['photo']
            largest_photo = max(photos, key=lambda x: x.get('file_size', 0))
            media_urls.append(self._get_file_url(largest_photo['file_id']))
        
        if 'video' in post:
            video = post['video']
            media_urls.append(self._get_file_url(video['file_id']))
        
        if 'document' in post:
            document = post['document']
            media_urls.append(self._get_file_url(document['file_id']))
        
        # Extract hashtags from caption
        caption = post.get('caption', '')
        hashtags = [word[1:] for word in caption.split() if word.startswith('#')]
        
        return {
            'post_id': str(post['message_id']),
            'post_type': self._determine_post_type(post),
            'caption': caption,
            'media_urls': media_urls,
            'hashtags': hashtags,
            'posted_at': datetime.fromtimestamp(post['date']),
        }
    
    def _get_file_url(self, file_id):
        """Get file URL from Telegram"""
        try:
            url = f"{self.base_url}/getFile"
            response = requests.get(url, params={'file_id': file_id})
            
            if response.status_code == 200:
                file_path = response.json()['result']['file_path']
                return f"https://api.telegram.org/file/bot{self.token}/{file_path}"
            
        except Exception as e:
            logger.error(f"Error getting Telegram file URL: {e}")
        
        return None
    
    def _determine_post_type(self, post):
        """Determine post type from Telegram post"""
        if 'photo' in post:
            return 'photo'
        elif 'video' in post:
            return 'video'
        elif 'document' in post:
            return 'post'
        else:
            return 'post'


class InstagramService:
    """Instagram Basic Display API integration"""
    
    def __init__(self):
        self.app_id = settings.INSTAGRAM_APP_ID
        self.app_secret = settings.INSTAGRAM_APP_SECRET
        self.base_url = "https://graph.instagram.com"
    
    def get_user_media(self, access_token, limit=50):
        """Get user's Instagram media"""
        try:
            url = f"{self.base_url}/me/media"
            params = {
                'fields': 'id,caption,media_type,media_url,permalink,timestamp,thumbnail_url',
                'access_token': access_token,
                'limit': limit
            }
            
            response = requests.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                posts = []
                
                for media in data.get('data', []):
                    posts.append(self._parse_instagram_media(media))
                
                return posts
            else:
                logger.error(f"Instagram API error: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Error fetching Instagram posts: {e}")
            return []
    
    def _parse_instagram_media(self, media):
        """Parse Instagram media data"""
        caption = media.get('caption', '')
        hashtags = [word[1:] for word in caption.split() if word.startswith('#')]
        
        media_urls = [media.get('media_url')]
        if media.get('thumbnail_url'):
            media_urls.append(media.get('thumbnail_url'))
        
        return {
            'post_id': media['id'],
            'post_type': media.get('media_type', 'IMAGE').lower(),
            'caption': caption,
            'media_urls': [url for url in media_urls if url],
            'hashtags': hashtags,
            'posted_at': datetime.fromisoformat(media['timestamp'].replace('Z', '+00:00')),
        }
    
    def refresh_access_token(self, access_token):
        """Refresh Instagram access token"""
        try:
            url = f"{self.base_url}/refresh_access_token"
            params = {
                'grant_type': 'ig_refresh_token',
                'access_token': access_token
            }
            
            response = requests.get(url, params=params)
            
            if response.status_code == 200:
                return response.json()['access_token']
            
        except Exception as e:
            logger.error(f"Error refreshing Instagram token: {e}")
        
        return None


class SocialMediaImporter:
    """Main service for importing social media content"""
    
    def __init__(self):
        self.telegram_service = TelegramService()
        self.instagram_service = InstagramService()
    
    def import_account_posts(self, account, limit=50, create_products=False):
        """Import posts from a social media account"""
        try:
            # Create import session
            session = ImportSession.objects.create(
                store=account.store,
                account=account,
                status='processing',
                import_limit=limit,
                create_products=create_products
            )
            session.started_at = timezone.now()
            session.save()
            
            posts = []
            
            # Fetch posts based on platform
            if account.platform == 'telegram':
                posts = self.telegram_service.get_channel_posts(
                    account.username, 
                    limit
                )
            elif account.platform == 'instagram':
                posts = self.instagram_service.get_user_media(
                    account.access_token, 
                    limit
                )
            
            session.posts_found = len(posts)
            session.save()
            
            # Process each post
            for post_data in posts:
                try:
                    post = self._create_or_update_post(account, post_data)
                    if post:
                        session.posts_imported += 1
                        
                        # Download media if requested
                        if session.import_media:
                            self._download_post_media(post)
                        
                        # Create product if requested
                        if create_products and not post.is_imported:
                            product = self._create_product_from_post(post)
                            if product:
                                post.imported_to_product = product
                                post.is_imported = True
                                post.save()
                                session.products_created += 1
                
                except Exception as e:
                    logger.error(f"Error processing post {post_data.get('post_id')}: {e}")
                    session.error_count += 1
            
            # Complete session
            session.status = 'completed'
            session.completed_at = timezone.now()
            session.save()
            
            # Update account last sync
            account.last_sync = timezone.now()
            account.save()
            
            return session
            
        except Exception as e:
            logger.error(f"Error importing account {account.username}: {e}")
            if 'session' in locals():
                session.status = 'failed'
                session.error_message = str(e)
                session.save()
            return None
    
    def _create_or_update_post(self, account, post_data):
        """Create or update social media post"""
        try:
            post, created = SocialMediaPost.objects.get_or_create(
                account=account,
                post_id=post_data['post_id'],
                defaults={
                    'post_type': post_data['post_type'],
                    'caption': post_data['caption'],
                    'media_urls': post_data['media_urls'],
                    'hashtags': post_data['hashtags'],
                    'posted_at': post_data['posted_at'],
                }
            )
            
            if not created:
                # Update existing post
                post.caption = post_data['caption']
                post.media_urls = post_data['media_urls']
                post.hashtags = post_data['hashtags']
                post.save()
            
            return post
            
        except Exception as e:
            logger.error(f"Error creating post: {e}")
            return None
    
    def _download_post_media(self, post):
        """Download media files from social media post"""
        for media_url in post.media_urls:
            try:
                # Create media download record
                download = MediaDownload.objects.create(
                    post=post,
                    original_url=media_url,
                    media_type=self._detect_media_type(media_url),
                    status='downloading'
                )
                
                # Download file
                response = requests.get(media_url, timeout=30)
                if response.status_code == 200:
                    # Generate filename
                    extension = self._get_file_extension(media_url)
                    filename = f"{post.account.platform}_{post.post_id}_{download.id}.{extension}"
                    
                    # Save file
                    content = ContentFile(response.content, name=filename)
                    download.local_file.save(filename, content)
                    download.file_size = len(response.content)
                    download.status = 'completed'
                    download.downloaded_at = timezone.now()
                    download.save()
                
                else:
                    download.status = 'failed'
                    download.error_message = f"HTTP {response.status_code}"
                    download.save()
                    
            except Exception as e:
                logger.error(f"Error downloading media {media_url}: {e}")
                if 'download' in locals():
                    download.status = 'failed'
                    download.error_message = str(e)
                    download.save()
    
    def _create_product_from_post(self, post):
        """Create product from social media post"""
        try:
            from apps.products.models import Product, ProductCategory
            
            # Find or create a default category for social imports
            category, _ = ProductCategory.objects.get_or_create(
                store=post.account.store,
                name='social_import',
                defaults={
                    'name_fa': 'واردات از شبکه‌های اجتماعی',
                    'slug': 'social-import',
                    'description': 'محصولات وارد شده از شبکه‌های اجتماعی'
                }
            )
            
            # Extract product info from caption
            product_name = self._extract_product_name(post.caption)
            if not product_name:
                product_name = f"محصول {post.post_id}"
            
            # Create product
            product = Product.objects.create(
                store=post.account.store,
                category=category,
                name=product_name[:100],  # Limit length
                name_fa=product_name[:100],
                slug=f"social-{post.account.platform}-{post.post_id}",
                description=post.caption,
                short_description=post.caption[:200],
                base_price=0,  # Store owner needs to set price
                status='draft',  # Start as draft
                imported_from_social=True,
                social_media_source=post.account.platform,
                social_media_post_id=post.post_id
            )
            
            # Import media as product images
            self._import_post_media_to_product(post, product)
            
            return product
            
        except Exception as e:
            logger.error(f"Error creating product from post: {e}")
            return None
    
    def _import_post_media_to_product(self, post, product):
        """Import post media as product images"""
        try:
            from apps.products.models import ProductImage
            
            downloads = post.downloads.filter(status='completed', local_file__isnull=False)
            for i, download in enumerate(downloads):
                ProductImage.objects.create(
                    product=product,
                    image=download.local_file,
                    alt_text=f"{product.name_fa} - تصویر {i+1}",
                    is_featured=(i == 0),  # First image as featured
                    display_order=i,
                    imported_from_social=True,
                    social_media_url=download.original_url
                )
                
        except Exception as e:
            logger.error(f"Error importing media to product: {e}")
    
    def _extract_product_name(self, caption):
        """Extract product name from caption"""
        if not caption:
            return None
        
        # Simple extraction - take first line or sentence
        lines = caption.split('\n')
        first_line = lines[0].strip()
        
        # Remove hashtags and mentions
        words = []
        for word in first_line.split():
            if not word.startswith('#') and not word.startswith('@'):
                words.append(word)
        
        result = ' '.join(words[:8])  # Limit to 8 words
        return result if result else None
    
    def _detect_media_type(self, url):
        """Detect media type from URL"""
        url = url.lower()
        if any(ext in url for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
            return 'image'
        elif any(ext in url for ext in ['.mp4', '.mov', '.avi', '.webm']):
            return 'video'
        else:
            return 'image'  # Default to image
    
    def _get_file_extension(self, url):
        """Get file extension from URL"""
        url = url.lower()
        if '.jpg' in url or '.jpeg' in url:
            return 'jpg'
        elif '.png' in url:
            return 'png'
        elif '.gif' in url:
            return 'gif'
        elif '.webp' in url:
            return 'webp'
        elif '.mp4' in url:
            return 'mp4'
        elif '.mov' in url:
            return 'mov'
        else:
            return 'jpg'  # Default


# Celery tasks for background processing
def import_social_media_posts(account_id, limit=50, create_products=False):
    """Celery task to import social media posts"""
    try:
        account = SocialMediaAccount.objects.get(id=account_id)
        importer = SocialMediaImporter()
        session = importer.import_account_posts(account, limit, create_products)
        return {
            'session_id': str(session.id) if session else None,
            'success': session is not None
        }
    except Exception as e:
        logger.error(f"Error in import task: {e}")
        return {'success': False, 'error': str(e)}


def sync_all_active_accounts():
    """Celery task to sync all active accounts"""
    accounts = SocialMediaAccount.objects.filter(
        is_active=True, 
        auto_import=True
    )
    
    results = []
    for account in accounts:
        try:
            result = import_social_media_posts(account.id, limit=20)
            results.append({
                'account_id': str(account.id),
                'username': account.username,
                'result': result
            })
        except Exception as e:
            logger.error(f"Error syncing account {account.username}: {e}")
            results.append({
                'account_id': str(account.id),
                'username': account.username,
                'error': str(e)
            })
    
    return results
