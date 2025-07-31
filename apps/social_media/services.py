# Complete social media integration services
import requests
import json
import tempfile
import os
from typing import List, Dict, Any, Optional
from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone
from django.core.cache import cache
from apps.products.models import Product, ProductImage
import logging

logger = logging.getLogger(__name__)

class SocialMediaError(Exception):
    """Custom exception for social media operations"""
    pass

class TelegramService:
    """Service for Telegram integration"""
    
    def __init__(self):
        self.bot_token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}" if self.bot_token else None
        
        if not self.bot_token:
            logger.warning("Telegram bot token not configured")
    
    def _make_request(self, method: str, params: Dict = None) -> Dict:
        """Make authenticated request to Telegram API"""
        if not self.base_url:
            raise SocialMediaError("Telegram bot token not configured")
        
        url = f"{self.base_url}/{method}"
        
        try:
            response = requests.get(url, params=params or {}, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Telegram API error: {str(e)}")
            raise SocialMediaError(f"Telegram API request failed: {str(e)}")
    
    def get_channel_info(self, channel_username: str) -> Dict:
        """Get channel information"""
        try:
            result = self._make_request('getChat', {
                'chat_id': f"@{channel_username.lstrip('@')}"
            })
            return result.get('result', {})
        except SocialMediaError:
            return {}
    
    def get_channel_posts(self, channel_username: str, limit: int = 5) -> List[Dict]:
        """
        Get recent posts from Telegram channel
        Note: This requires the bot to be admin of the channel or use unofficial APIs
        """
        # Cache key for rate limiting
        cache_key = f"telegram_posts_{channel_username}_{limit}"
        cached_posts = cache.get(cache_key)
        
        if cached_posts:
            return cached_posts
        
        try:
            # For public channels, we can use getUpdates with specific chat_id
            # This is a simplified implementation - in production, use Telegram Bot API properly
            
            # Alternative: Use MTProto API or scraping (requires different approach)
            posts = self._get_channel_posts_via_updates(channel_username, limit)
            
            # Cache for 15 minutes
            cache.set(cache_key, posts, timeout=900)
            return posts
            
        except Exception as e:
            logger.error(f"Error fetching Telegram posts: {str(e)}")
            return []
    
    def _get_channel_posts_via_updates(self, channel_username: str, limit: int) -> List[Dict]:
        """Get posts using getUpdates method (limited functionality)"""
        try:
            updates = self._make_request('getUpdates', {
                'limit': limit * 2,  # Get more to filter channel posts
                'allowed_updates': json.dumps(['channel_post'])
            })
            
            posts = []
            for update in updates.get('result', []):
                if 'channel_post' in update:
                    post = update['channel_post']
                    if post.get('chat', {}).get('username') == channel_username.lstrip('@'):
                        posts.append({
                            'id': post.get('message_id'),
                            'text': post.get('text', ''),
                            'caption': post.get('caption', ''),
                            'date': post.get('date'),
                            'media': self._extract_media_from_post(post),
                            'platform': 'telegram'
                        })
                        
                        if len(posts) >= limit:
                            break
            
            return posts[:limit]
            
        except Exception as e:
            logger.error(f"Error processing Telegram updates: {str(e)}")
            return []
    
    def _extract_media_from_post(self, post: Dict) -> List[Dict]:
        """Extract media URLs from Telegram post"""
        media = []
        
        # Handle photos
        if 'photo' in post:
            # Get the largest photo size
            photo = max(post['photo'], key=lambda x: x.get('file_size', 0))
            media.append({
                'type': 'photo',
                'file_id': photo.get('file_id'),
                'file_size': photo.get('file_size')
            })
        
        # Handle videos
        if 'video' in post:
            media.append({
                'type': 'video',
                'file_id': post['video'].get('file_id'),
                'duration': post['video'].get('duration'),
                'file_size': post['video'].get('file_size')
            })
        
        # Handle documents (could be images/videos)
        if 'document' in post:
            media.append({
                'type': 'document',
                'file_id': post['document'].get('file_id'),
                'file_name': post['document'].get('file_name'),
                'mime_type': post['document'].get('mime_type'),
                'file_size': post['document'].get('file_size')
            })
        
        return media
    
    def download_file(self, file_id: str) -> Optional[bytes]:
        """Download file from Telegram servers"""
        try:
            # Get file path
            file_info = self._make_request('getFile', {'file_id': file_id})
            file_path = file_info.get('result', {}).get('file_path')
            
            if not file_path:
                return None
            
            # Download file
            download_url = f"https://api.telegram.org/file/bot{self.bot_token}/{file_path}"
            response = requests.get(download_url, timeout=60)
            response.raise_for_status()
            
            return response.content
            
        except Exception as e:
            logger.error(f"Error downloading Telegram file {file_id}: {str(e)}")
            return None

class InstagramService:
    """Service for Instagram Basic Display API integration"""
    
    def __init__(self):
        self.access_token = getattr(settings, 'INSTAGRAM_ACCESS_TOKEN', None)
        self.base_url = "https://graph.instagram.com"
        
        if not self.access_token:
            logger.warning("Instagram access token not configured")
    
    def _make_request(self, endpoint: str, params: Dict = None) -> Dict:
        """Make authenticated request to Instagram API"""
        if not self.access_token:
            raise SocialMediaError("Instagram access token not configured")
        
        url = f"{self.base_url}/{endpoint}"
        params = params or {}
        params['access_token'] = self.access_token
        
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Instagram API error: {str(e)}")
            raise SocialMediaError(f"Instagram API request failed: {str(e)}")
    
    def get_user_media(self, user_id: str = 'me', limit: int = 5) -> List[Dict]:
        """Get user's recent media posts"""
        cache_key = f"instagram_media_{user_id}_{limit}"
        cached_media = cache.get(cache_key)
        
        if cached_media:
            return cached_media
        
        try:
            result = self._make_request(f"{user_id}/media", {
                'fields': 'id,caption,media_type,media_url,thumbnail_url,timestamp,permalink',
                'limit': limit
            })
            
            media_list = []
            for item in result.get('data', []):
                media_list.append({
                    'id': item.get('id'),
                    'caption': item.get('caption', ''),
                    'media_type': item.get('media_type'),
                    'media_url': item.get('media_url'),
                    'thumbnail_url': item.get('thumbnail_url'),
                    'timestamp': item.get('timestamp'),
                    'permalink': item.get('permalink'),
                    'platform': 'instagram'
                })
            
            # Cache for 30 minutes
            cache.set(cache_key, media_list, timeout=1800)
            return media_list
            
        except SocialMediaError as e:
            logger.error(f"Error fetching Instagram media: {str(e)}")
            return []

class SocialMediaImporter:
    """Main service for importing content from social media platforms"""
    
    def __init__(self):
        self.telegram = TelegramService()
        self.instagram = InstagramService()
    
    def get_platform_content(self, platform: str, source_id: str, limit: int = 5) -> List[Dict]:
        """Get content from specified platform"""
        if platform.lower() == 'telegram':
            return self.telegram.get_channel_posts(source_id, limit)
        elif platform.lower() == 'instagram':
            return self.instagram.get_user_media(source_id, limit)
        else:
            raise SocialMediaError(f"Unsupported platform: {platform}")
    
    def import_content_to_product(self, product: Product, platform: str, content_data: List[Dict]) -> Dict:
        """
        Import social media content to product
        Returns summary of imported items
        """
        imported_images = []
        imported_texts = []
        errors = []
        
        for item in content_data:
            try:
                # Import text content
                text_content = item.get('caption') or item.get('text', '')
                if text_content:
                    imported_texts.append({
                        'content': text_content[:500],  # Limit length
                        'source_id': item.get('id'),
                        'platform': platform,
                        'timestamp': item.get('timestamp') or item.get('date')
                    })
                
                # Import media
                if platform == 'instagram':
                    media_url = item.get('media_url')
                    if media_url and item.get('media_type') in ['IMAGE', 'CAROUSEL_ALBUM']:
                        image = self._download_and_save_image(
                            product, media_url, platform, item.get('id')
                        )
                        if image:
                            imported_images.append(image)
                
                elif platform == 'telegram':
                    for media_item in item.get('media', []):
                        if media_item.get('type') == 'photo':
                            file_content = self.telegram.download_file(media_item.get('file_id'))
                            if file_content:
                                image = self._save_image_from_content(
                                    product, file_content, platform, 
                                    f"{item.get('id')}_{media_item.get('file_id')}"
                                )
                                if image:
                                    imported_images.append(image)
                
            except Exception as e:
                logger.error(f"Error importing item {item.get('id')}: {str(e)}")
                errors.append(str(e))
        
        # Update product social media data
        if imported_images or imported_texts:
            self._update_product_social_data(product, platform, {
                'imported_images': len(imported_images),
                'imported_texts': len(imported_texts),
                'last_import': timezone.now().isoformat(),
                'errors': errors
            })
        
        return {
            'success': True,
            'imported_images': len(imported_images),
            'imported_texts': len(imported_texts),
            'errors': errors,
            'total_processed': len(content_data)
        }
    
    def _download_and_save_image(self, product: Product, url: str, platform: str, source_id: str) -> Optional[ProductImage]:
        """Download image from URL and save to product"""
        try:
            response = requests.get(url, timeout=60)
            response.raise_for_status()
            
            return self._save_image_from_content(product, response.content, platform, source_id)
            
        except Exception as e:
            logger.error(f"Error downloading image from {url}: {str(e)}")
            return None
    
    def _save_image_from_content(self, product: Product, content: bytes, platform: str, source_id: str) -> Optional[ProductImage]:
        """Save image content to ProductImage model"""
        try:
            # Create ProductImage instance
            product_image = ProductImage(
                product=product,
                alt_text=f"Imported from {platform} - {source_id}"[:200],
                imported_from_social=True,
                social_media_url=f"{platform}://{source_id}"
            )
            
            # Save image file
            filename = f"social_{platform}_{source_id}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            product_image.image.save(
                filename,
                ContentFile(content),
                save=False
            )
            
            product_image.save()
            return product_image
            
        except Exception as e:
            logger.error(f"Error saving image for product {product.id}: {str(e)}")
            return None
    
    def _update_product_social_data(self, product: Product, platform: str, import_data: Dict):
        """Update product's social media data"""
        try:
            if not product.social_media_data:
                product.social_media_data = {}
            
            if platform not in product.social_media_data:
                product.social_media_data[platform] = {}
            
            product.social_media_data[platform].update(import_data)
            product.imported_from_social = True
            product.social_media_source = platform
            product.last_social_import = timezone.now()
            
            product.save(update_fields=[
                'social_media_data', 'imported_from_social', 
                'social_media_source', 'last_social_import'
            ])
            
        except Exception as e:
            logger.error(f"Error updating product social data: {str(e)}")

# Convenience function for easy import
def import_social_media_content(product_id: str, platform: str, source_id: str, limit: int = 5) -> Dict:
    """
    Convenience function to import social media content for a product
    
    Args:
        product_id: UUID of the product
        platform: 'telegram' or 'instagram'
        source_id: Channel username for Telegram, user ID for Instagram
        limit: Number of posts to import (default 5)
    
    Returns:
        Dict with import results
    """
    try:
        product = Product.objects.get(id=product_id)
        importer = SocialMediaImporter()
        
        # Get content from platform
        content = importer.get_platform_content(platform, source_id, limit)
        
        if not content:
            return {
                'success': False,
                'error': f'No content found from {platform} source: {source_id}'
            }
        
        # Import content to product
        result = importer.import_content_to_product(product, platform, content)
        
        return result
        
    except Product.DoesNotExist:
        return {
            'success': False,
            'error': f'Product with ID {product_id} not found'
        }
    except Exception as e:
        logger.error(f"Error in import_social_media_content: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }
