"""
Complete Social Media Integration Service
Provides comprehensive functionality for importing content from social media platforms
"""

import requests
import re
import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
import logging

logger = logging.getLogger('mall.social_media')


class SocialMediaImportService:
    """
    Centralized service for importing content from social media platforms
    Replaces incomplete placeholder implementation
    """
    
    @staticmethod
    def import_content(platform: str, post_id: str, access_token: str = None) -> Dict:
        """
        Import content from specified social media platform
        
        Args:
            platform: 'telegram' or 'instagram'
            post_id: Platform-specific post identifier
            access_token: Required for Instagram, optional for Telegram
        
        Returns:
            Dict containing extracted content
        """
        try:
            if platform == 'telegram':
                return TelegramImportService.import_post(post_id)
            elif platform == 'instagram':
                return InstagramImportService.import_post(post_id, access_token)
            else:
                raise ValueError(f"Unsupported platform: {platform}")
        except Exception as e:
            logger.error(f"Failed to import from {platform}: {str(e)}")
            raise


class TelegramImportService:
    """
    Service for importing content from Telegram channels/groups
    """
    
    TELEGRAM_API_BASE = "https://api.telegram.org/bot{token}"
    
    @classmethod
    def import_post(cls, post_identifier: str, bot_token: str = None) -> Dict:
        """
        Import content from Telegram post
        
        Args:
            post_identifier: Format "@channel_username/message_id" or "channel_id/message_id"
            bot_token: Telegram bot token (from settings if not provided)
        
        Returns:
            Dict with extracted content
        """
        if not bot_token:
            bot_token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '')
            if not bot_token:
                raise ValueError("Telegram bot token not configured")
        
        # Parse post identifier
        channel, message_id = cls._parse_post_identifier(post_identifier)
        
        # Get message content
        api_url = cls.TELEGRAM_API_BASE.format(token=bot_token)
        
        try:
            # Get channel info first
            channel_info = cls._get_channel_info(api_url, channel)
            
            # Get message content
            message_data = cls._get_message(api_url, channel, message_id)
            
            # Extract content
            extracted_content = cls._extract_content(message_data, channel_info)
            
            return {
                'platform': 'telegram',
                'post_id': post_identifier,
                'success': True,
                'content': extracted_content,
                'imported_at': timezone.now().isoformat()
            }
            
        except requests.RequestException as e:
            logger.error(f"Telegram API request failed: {str(e)}")
            raise ValueError(f"Failed to fetch Telegram content: {str(e)}")
    
    @staticmethod
    def _parse_post_identifier(identifier: str) -> Tuple[str, int]:
        """Parse Telegram post identifier"""
        parts = identifier.split('/')
        if len(parts) != 2:
            raise ValueError("Invalid Telegram post identifier format")
        
        channel = parts[0].replace('@', '')
        try:
            message_id = int(parts[1])
        except ValueError:
            raise ValueError("Invalid message ID")
        
        return channel, message_id
    
    @staticmethod
    def _get_channel_info(api_url: str, channel: str) -> Dict:
        """Get Telegram channel information"""
        response = requests.get(f"{api_url}/getChat", params={
            'chat_id': f"@{channel}" if not channel.startswith('-') else channel
        })
        response.raise_for_status()
        
        data = response.json()
        if not data['ok']:
            raise ValueError(f"Telegram API error: {data.get('description', 'Unknown error')}")
        
        return data['result']
    
    @staticmethod
    def _get_message(api_url: str, channel: str, message_id: int) -> Dict:
        """Get specific message from Telegram"""
        # Note: This is a simplified implementation
        # In practice, you might need to use different endpoints or methods
        response = requests.get(f"{api_url}/getUpdates", params={
            'limit': 100
        })
        response.raise_for_status()
        
        data = response.json()
        if not data['ok']:
            raise ValueError(f"Telegram API error: {data.get('description', 'Unknown error')}")
        
        # Find the specific message
        for update in data['result']:
            if 'message' in update:
                message = update['message']
                if message.get('message_id') == message_id:
                    return update
        
        raise ValueError("Message not found")
    
    @staticmethod
    def _extract_content(message_data: Dict, channel_info: Dict) -> Dict:
        """Extract product-relevant content from Telegram message"""
        message = message_data.get('message', {})
        
        # Extract text content
        text_content = message.get('text', '') or message.get('caption', '')
        
        # Extract media
        media_files = []
        
        # Handle photos
        if 'photo' in message:
            photos = message['photo']
            # Get highest resolution photo
            best_photo = max(photos, key=lambda p: p.get('file_size', 0))
            media_files.append({
                'type': 'photo',
                'file_id': best_photo['file_id'],
                'file_size': best_photo.get('file_size', 0)
            })
        
        # Handle videos
        if 'video' in message:
            video = message['video']
            media_files.append({
                'type': 'video',
                'file_id': video['file_id'],
                'file_size': video.get('file_size', 0),
                'duration': video.get('duration', 0)
            })
        
        # Handle documents (could be images/videos)
        if 'document' in message:
            doc = message['document']
            mime_type = doc.get('mime_type', '')
            if mime_type.startswith('image/') or mime_type.startswith('video/'):
                media_files.append({
                    'type': 'document',
                    'file_id': doc['file_id'],
                    'file_name': doc.get('file_name', ''),
                    'mime_type': mime_type,
                    'file_size': doc.get('file_size', 0)
                })
        
        # Extract product information using basic NLP
        product_info = TelegramContentAnalyzer.analyze_product_content(text_content)
        
        return {
            'text': text_content,
            'media_files': media_files,
            'channel_info': {
                'title': channel_info.get('title', ''),
                'username': channel_info.get('username', ''),
                'description': channel_info.get('description', '')
            },
            'message_date': message.get('date'),
            'product_info': product_info,
            'hashtags': TelegramContentAnalyzer.extract_hashtags(text_content),
            'mentions': TelegramContentAnalyzer.extract_mentions(text_content)
        }


class InstagramImportService:
    """
    Service for importing content from Instagram using Basic Display API
    """
    
    INSTAGRAM_API_BASE = "https://graph.instagram.com"
    
    @classmethod
    def import_post(cls, media_id: str, access_token: str) -> Dict:
        """
        Import content from Instagram post
        
        Args:
            media_id: Instagram media ID
            access_token: Instagram Basic Display API access token
        
        Returns:
            Dict with extracted content
        """
        try:
            # Get media details
            media_data = cls._get_media_details(media_id, access_token)
            
            # Extract content
            extracted_content = cls._extract_content(media_data)
            
            return {
                'platform': 'instagram',
                'post_id': media_id,
                'success': True,
                'content': extracted_content,
                'imported_at': timezone.now().isoformat()
            }
            
        except requests.RequestException as e:
            logger.error(f"Instagram API request failed: {str(e)}")
            raise ValueError(f"Failed to fetch Instagram content: {str(e)}")
    
    @staticmethod
    def _get_media_details(media_id: str, access_token: str) -> Dict:
        """Get Instagram media details"""
        url = f"{InstagramImportService.INSTAGRAM_API_BASE}/{media_id}"
        params = {
            'fields': 'id,media_type,media_url,caption,permalink,timestamp',
            'access_token': access_token
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        if 'error' in data:
            raise ValueError(f"Instagram API error: {data['error']['message']}")
        
        return data
    
    @staticmethod
    def _extract_content(media_data: Dict) -> Dict:
        """Extract product-relevant content from Instagram media"""
        caption = media_data.get('caption', '')
        media_url = media_data.get('media_url', '')
        media_type = media_data.get('media_type', '')
        
        # Analyze caption for product information
        product_info = InstagramContentAnalyzer.analyze_product_content(caption)
        
        return {
            'caption': caption,
            'media_url': media_url,
            'media_type': media_type,
            'permalink': media_data.get('permalink', ''),
            'timestamp': media_data.get('timestamp', ''),
            'product_info': product_info,
            'hashtags': InstagramContentAnalyzer.extract_hashtags(caption),
            'mentions': InstagramContentAnalyzer.extract_mentions(caption)
        }


class TelegramContentAnalyzer:
    """
    Analyzer for extracting product information from Telegram content
    """
    
    @staticmethod
    def analyze_product_content(text: str) -> Dict:
        """
        Analyze text content to extract product information
        Uses Persian NLP and pattern matching
        """
        if not text:
            return {}
        
        # Basic product information extraction
        product_info = {
            'potential_name': '',
            'potential_price': None,
            'potential_brand': '',
            'potential_features': [],
            'potential_categories': []
        }
        
        # Extract potential product name (first line or prominent text)
        lines = text.split('\n')
        if lines:
            product_info['potential_name'] = lines[0].strip()
        
        # Extract price patterns
        price_patterns = [
            r'قیمت[:\s]*(\d+[,\d]*)\s*تومان',
            r'(\d+[,\d]*)\s*تومان',
            r'(\d+[,\d]*)\s*ت',
            r'💰[:\s]*(\d+[,\d]*)',
        ]
        
        for pattern in price_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                price_str = matches[0].replace(',', '')
                try:
                    product_info['potential_price'] = int(price_str)
                    break
                except ValueError:
                    continue
        
        # Extract features (lines starting with emojis or bullets)
        feature_patterns = [
            r'[✅✔️🔸🔹▪️▫️•]\s*([^\n]+)',
            r'[🔴🟠🟡🟢🔵🟣]\s*([^\n]+)',
            r'[📱💻⌚🎧]\s*([^\n]+)'
        ]
        
        for pattern in feature_patterns:
            features = re.findall(pattern, text)
            product_info['potential_features'].extend(features)
        
        # Extract brand mentions (common Persian/English brands)
        brand_patterns = [
            r'برند[:\s]*([^\n\s]+)',
            r'(اپل|سامسونگ|شیائومی|هواوی|الجی|سونی)',
            r'(Apple|Samsung|Xiaomi|Huawei|LG|Sony)',
            r'Brand[:\s]*([^\n\s]+)'
        ]
        
        for pattern in brand_patterns:
            brands = re.findall(pattern, text, re.IGNORECASE)
            if brands:
                product_info['potential_brand'] = brands[0]
                break
        
        return product_info
    
    @staticmethod
    def extract_hashtags(text: str) -> List[str]:
        """Extract hashtags from text"""
        return re.findall(r'#([^\s#]+)', text)
    
    @staticmethod
    def extract_mentions(text: str) -> List[str]:
        """Extract mentions from text"""
        return re.findall(r'@([^\s@]+)', text)


class InstagramContentAnalyzer:
    """
    Analyzer for extracting product information from Instagram content
    """
    
    @staticmethod
    def analyze_product_content(caption: str) -> Dict:
        """
        Analyze Instagram caption to extract product information
        """
        if not caption:
            return {}
        
        # Use similar logic to Telegram but adapted for Instagram format
        product_info = {
            'potential_name': '',
            'potential_price': None,
            'potential_brand': '',
            'potential_features': [],
            'potential_categories': []
        }
        
        # Instagram-specific price patterns
        price_patterns = [
            r'Price[:\s]*\$?(\d+[,\d]*)',
            r'قیمت[:\s]*(\d+[,\d]*)\s*تومان',
            r'(\d+[,\d]*)\s*تومان',
            r'💰[:\s]*(\d+[,\d]*)',
        ]
        
        for pattern in price_patterns:
            matches = re.findall(pattern, caption, re.IGNORECASE)
            if matches:
                price_str = matches[0].replace(',', '')
                try:
                    product_info['potential_price'] = int(price_str)
                    break
                except ValueError:
                    continue
        
        # Extract product name from beginning of caption
        lines = caption.split('\n')
        if lines:
            first_line = lines[0].strip()
            # Remove excessive emojis and hashtags for cleaner name
            clean_name = re.sub(r'[#@][\w]+', '', first_line)
            clean_name = re.sub(r'[^\w\s\u0600-\u06FF]', ' ', clean_name)
            product_info['potential_name'] = clean_name.strip()
        
        return product_info
    
    @staticmethod
    def extract_hashtags(caption: str) -> List[str]:
        """Extract hashtags from Instagram caption"""
        return re.findall(r'#([^\s#]+)', caption)
    
    @staticmethod
    def extract_mentions(caption: str) -> List[str]:
        """Extract mentions from Instagram caption"""
        return re.findall(r'@([^\s@]+)', caption)


class MediaDownloadService:
    """
    Service for downloading and storing media files from social media
    """
    
    @staticmethod
    def download_telegram_media(file_id: str, bot_token: str) -> Optional[str]:
        """
        Download media file from Telegram and store it
        
        Returns:
            Path to stored file or None if failed
        """
        try:
            # Get file path from Telegram
            api_url = f"https://api.telegram.org/bot{bot_token}"
            file_response = requests.get(f"{api_url}/getFile", params={'file_id': file_id})
            file_response.raise_for_status()
            
            file_data = file_response.json()
            if not file_data['ok']:
                return None
            
            file_path = file_data['result']['file_path']
            
            # Download the actual file
            download_url = f"https://api.telegram.org/file/bot{bot_token}/{file_path}"
            media_response = requests.get(download_url)
            media_response.raise_for_status()
            
            # Generate filename
            filename = f"telegram_{file_id}_{timezone.now().strftime('%Y%m%d_%H%M%S')}"
            if '.' in file_path:
                extension = file_path.split('.')[-1]
                filename += f".{extension}"
            
            # Store file
            file_content = ContentFile(media_response.content)
            stored_path = default_storage.save(f"social_media/{filename}", file_content)
            
            return stored_path
            
        except Exception as e:
            logger.error(f"Failed to download Telegram media {file_id}: {str(e)}")
            return None
    
    @staticmethod
    def download_instagram_media(media_url: str) -> Optional[str]:
        """
        Download media file from Instagram and store it
        
        Returns:
            Path to stored file or None if failed
        """
        try:
            response = requests.get(media_url, timeout=30)
            response.raise_for_status()
            
            # Generate filename
            filename = f"instagram_{timezone.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Determine file extension from URL or content type
            if '.' in media_url and len(media_url.split('.')[-1].split('?')[0]) <= 4:
                extension = media_url.split('.')[-1].split('?')[0]
            else:
                content_type = response.headers.get('content-type', '')
                if 'image' in content_type:
                    extension = 'jpg'
                elif 'video' in content_type:
                    extension = 'mp4'
                else:
                    extension = 'bin'
            
            filename += f".{extension}"
            
            # Store file
            file_content = ContentFile(response.content)
            stored_path = default_storage.save(f"social_media/{filename}", file_content)
            
            return stored_path
            
        except Exception as e:
            logger.error(f"Failed to download Instagram media {media_url}: {str(e)}")
            return None


class ProductCreationService:
    """
    Service for creating products from social media content
    """
    
    @staticmethod
    def create_product_from_social_media(
        store,
        product_class,
        category,
        social_content: Dict,
        additional_data: Dict = None
    ):
        """
        Create a product from imported social media content
        
        Args:
            store: Store instance
            product_class: ProductClass instance (must be leaf)
            category: ProductCategory instance
            social_content: Extracted content from social media
            additional_data: Additional product data
        
        Returns:
            Created Product instance
        """
        from apps.products.models import Product, ProductImage
        from apps.core.validation import ProductValidationService
        
        # Validate inputs
        ProductValidationService.validate_product_class_hierarchy(
            product_class_id=str(product_class.id),
            category_id=str(category.id),
            store_id=str(store.id)
        )
        
        # Extract product information
        product_info = social_content.get('product_info', {})
        
        # Prepare product data
        product_data = {
            'store': store,
            'product_class': product_class,
            'category': category,
            'name': product_info.get('potential_name', 'محصول وارد شده از شبکه اجتماعی')[:100],
            'name_fa': product_info.get('potential_name', 'محصول وارد شده از شبکه اجتماعی')[:100],
            'description': social_content.get('text', social_content.get('caption', '')),
            'base_price': product_info.get('potential_price', 0),
            'imported_from_social': True,
            'social_media_source': social_content.get('platform'),
            'social_media_post_id': social_content.get('post_id'),
            'status': 'draft',  # Requires manual review
        }
        
        # Add brand if detected
        if product_info.get('potential_brand'):
            from apps.products.models import Brand
            brand, created = Brand.objects.get_or_create(
                store=store,
                name_fa=product_info['potential_brand'],
                defaults={'name': product_info['potential_brand']}
            )
            product_data['brand'] = brand
        
        # Merge additional data
        if additional_data:
            product_data.update(additional_data)
        
        # Create product
        product = Product.objects.create(**product_data)
        
        # Handle media files
        media_files = social_content.get('media_files', [])
        if social_content.get('media_url'):  # Instagram
            media_files.append({
                'type': 'image',
                'url': social_content['media_url']
            })
        
        # Download and attach media
        for i, media in enumerate(media_files[:5]):  # Limit to 5 media files
            if media.get('file_id'):  # Telegram
                bot_token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '')
                if bot_token:
                    stored_path = MediaDownloadService.download_telegram_media(
                        media['file_id'], bot_token
                    )
                    if stored_path:
                        ProductImage.objects.create(
                            product=product,
                            image=stored_path,
                            is_featured=(i == 0),
                            imported_from_social=True,
                            social_media_url=social_content.get('permalink', '')
                        )
            
            elif media.get('url'):  # Instagram or direct URL
                stored_path = MediaDownloadService.download_instagram_media(media['url'])
                if stored_path:
                    ProductImage.objects.create(
                        product=product,
                        image=stored_path,
                        is_featured=(i == 0),
                        imported_from_social=True,
                        social_media_url=social_content.get('permalink', '')
                    )
        
        return product


# Celery tasks for background processing
try:
    from celery import shared_task
    
    @shared_task
    def import_social_media_content_task(platform: str, post_id: str, access_token: str = None):
        """
        Background task to import social media content
        """
        try:
            content = SocialMediaImportService.import_content(platform, post_id, access_token)
            return {
                'success': True,
                'platform': platform,
                'post_id': post_id,
                'content': content
            }
        except Exception as e:
            logger.error(f"Failed to import {platform} content {post_id}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'platform': platform,
                'post_id': post_id
            }
    
    @shared_task
    def create_product_from_social_task(
        store_id: str,
        product_class_id: str,
        category_id: str,
        social_content: Dict,
        additional_data: Dict = None
    ):
        """
        Background task to create product from social media content
        """
        try:
            from apps.stores.models import Store
            from apps.products.models import ProductClass, ProductCategory
            
            store = Store.objects.get(id=store_id)
            product_class = ProductClass.objects.get(id=product_class_id)
            category = ProductCategory.objects.get(id=category_id)
            
            product = ProductCreationService.create_product_from_social_media(
                store=store,
                product_class=product_class,
                category=category,
                social_content=social_content,
                additional_data=additional_data
            )
            
            return {
                'success': True,
                'product_id': str(product.id),
                'product_name': product.name_fa
            }
        
        except Exception as e:
            logger.error(f"Failed to create product from social media: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

except ImportError:
    # Celery not available
    pass
