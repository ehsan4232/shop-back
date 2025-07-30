"""
Social media integration services
Handles importing content from various social media platforms
"""

from typing import Dict, Any, List, Optional
from django.core.exceptions import ValidationError
import re
import requests
from urllib.parse import urlparse


class SocialMediaImportService:
    """
    Service for importing content from social media platforms
    """
    
    @staticmethod
    def import_content(platform: str, post_id: str, access_token: str = None) -> Dict[str, Any]:
        """
        Import content from specified social media platform
        """
        if platform == 'telegram':
            return SocialMediaImportService._import_telegram_content(post_id)
        elif platform == 'instagram':
            return SocialMediaImportService._import_instagram_content(post_id, access_token)
        else:
            raise ValidationError(f"Unsupported platform: {platform}")
    
    @staticmethod
    def _import_telegram_content(post_id: str) -> Dict[str, Any]:
        """
        Import content from Telegram post
        Note: This is a simplified implementation
        Real implementation would use Telegram Bot API
        """
        # Parse post ID (format: @channel/message_id)
        match = re.match(r'^@?([a-zA-Z0-9_]+)/(\d+)$', post_id)
        if not match:
            raise ValidationError("Invalid Telegram post ID format")
        
        channel, message_id = match.groups()
        
        # For now, return mock data
        # Real implementation would fetch from Telegram API
        return {
            'platform': 'telegram',
            'post_id': post_id,
            'channel': channel,
            'message_id': message_id,
            'title': 'محصول وارداتی از تلگرام',
            'title_fa': 'محصول وارداتی از تلگرام',
            'description': 'توضیحات محصول وارد شده از تلگرام',
            'summary': 'خلاصه محصول',
            'images': [],
            'videos': [],
            'suggested_price': None,
            'extracted_at': '2025-07-30T20:00:00Z'
        }
    
    @staticmethod
    def _import_instagram_content(post_id: str, access_token: str) -> Dict[str, Any]:
        """
        Import content from Instagram post
        Note: This is a simplified implementation
        Real implementation would use Instagram Basic Display API
        """
        if not access_token:
            raise ValidationError("Instagram access token is required")
        
        # For now, return mock data
        # Real implementation would fetch from Instagram API
        return {
            'platform': 'instagram',
            'post_id': post_id,
            'title': 'محصول وارداتی از اینستاگرام',
            'title_fa': 'محصول وارداتی از اینستاگرام',
            'description': 'توضیحات محصول وارد شده از اینستاگرام',
            'summary': 'خلاصه محصول',
            'images': [],
            'videos': [],
            'suggested_price': None,
            'extracted_at': '2025-07-30T20:00:00Z'
        }


class SocialMediaContentExtractor:
    """
    Service for extracting and processing social media content
    """
    
    @staticmethod
    def extract_product_info(content: str) -> Dict[str, Any]:
        """
        Extract product information from social media content
        """
        extracted = {
            'title': None,
            'description': content,
            'price': None,
            'features': [],
            'hashtags': []
        }
        
        # Extract hashtags
        hashtag_pattern = r'#([\w\u0600-\u06FF]+)'
        hashtags = re.findall(hashtag_pattern, content)
        extracted['hashtags'] = hashtags
        
        # Extract price (Persian and English numbers)
        price_patterns = [
            r'(\d+)\s*تومان',
            r'(\d+)\s*ریال',
            r'قیمت[:\s]*(\d+)',
            r'(\d+)\s*T',
        ]
        
        for pattern in price_patterns:
            match = re.search(pattern, content)
            if match:
                extracted['price'] = int(match.group(1))
                break
        
        # Extract product title (first line or sentence)
        lines = content.strip().split('\n')
        if lines:
            first_line = lines[0].strip()
            if len(first_line) > 5 and len(first_line) < 100:
                extracted['title'] = first_line
        
        return extracted
    
    @staticmethod
    def process_media_urls(media_urls: List[str]) -> List[Dict[str, Any]]:
        """
        Process and categorize media URLs
        """
        processed_media = []
        
        for url in media_urls:
            media_info = {
                'url': url,
                'type': SocialMediaContentExtractor._detect_media_type(url),
                'accessible': SocialMediaContentExtractor._check_url_accessibility(url)
            }
            processed_media.append(media_info)
        
        return processed_media
    
    @staticmethod
    def _detect_media_type(url: str) -> str:
        """
        Detect media type from URL
        """
        parsed = urlparse(url)
        path = parsed.path.lower()
        
        if path.endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
            return 'image'
        elif path.endswith(('.mp4', '.avi', '.mov', '.webm')):
            return 'video'
        else:
            return 'unknown'
    
    @staticmethod
    def _check_url_accessibility(url: str) -> bool:
        """
        Check if URL is accessible
        """
        try:
            response = requests.head(url, timeout=5, allow_redirects=True)
            return response.status_code == 200
        except:
            return False


class SocialMediaAccountService:
    """
    Service for managing social media accounts and connections
    """
    
    @staticmethod
    def validate_account_connection(platform: str, account_data: Dict[str, Any]) -> bool:
        """
        Validate social media account connection
        """
        if platform == 'telegram':
            return SocialMediaAccountService._validate_telegram_account(account_data)
        elif platform == 'instagram':
            return SocialMediaAccountService._validate_instagram_account(account_data)
        return False
    
    @staticmethod
    def _validate_telegram_account(account_data: Dict[str, Any]) -> bool:
        """
        Validate Telegram account data
        """
        required_fields = ['username', 'bot_token']
        return all(field in account_data for field in required_fields)
    
    @staticmethod
    def _validate_instagram_account(account_data: Dict[str, Any]) -> bool:
        """
        Validate Instagram account data
        """
        required_fields = ['username', 'access_token']
        return all(field in account_data for field in required_fields)
    
    @staticmethod
    def get_recent_posts(platform: str, account_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent posts from a social media account
        """
        # This would integrate with actual social media APIs
        # For now, return mock data
        return [
            {
                'post_id': f'post_{i}',
                'content': f'نمونه پست شماره {i}',
                'media_urls': [],
                'created_at': '2025-07-30T20:00:00Z',
                'engagement': {
                    'likes': 10 * i,
                    'comments': 2 * i,
                    'shares': i
                }
            }
            for i in range(1, limit + 1)
        ]


# Mock service implementations for missing dependencies
class MockProductCreationService:
    """Mock service to prevent import errors"""
    
    @staticmethod
    def create_product_from_social_media(store, product_class, category, social_content, additional_data=None):
        """Mock implementation"""
        from apps.products.models import Product
        
        return Product.objects.create(
            store=store,
            product_class=product_class,
            category=category,
            name=social_content.get('title', 'محصول وارداتی'),
            name_fa=social_content.get('title_fa', 'محصول وارداتی'),
            description=social_content.get('description', ''),
            imported_from_social=True,
            social_media_source=social_content.get('platform'),
            social_media_post_id=social_content.get('post_id'),
            status='draft'
        )


# Export services for use in other modules
__all__ = [
    'SocialMediaImportService',
    'SocialMediaContentExtractor', 
    'SocialMediaAccountService',
    'MockProductCreationService'
]
