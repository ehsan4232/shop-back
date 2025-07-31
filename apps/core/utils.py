"""
Core utility functions for Mall platform
"""
import requests
import logging
from django.conf import settings
from typing import Optional
from datetime import datetime
import re

logger = logging.getLogger(__name__)


def send_sms(phone_number: str, message: str) -> bool:
    """
    Send SMS using Iranian SMS providers
    Product description requirement: OTP-based authentication
    """
    
    # Configuration for Iranian SMS providers
    SMS_PROVIDERS = {
        'kavenegar': {
            'url': 'https://api.kavenegar.com/v1/{api_key}/sms/send.json',
            'method': 'POST',
            'api_key': getattr(settings, 'KAVENEGAR_API_KEY', None),
        },
        'smsir': {
            'url': 'https://ws.sms.ir/api/MessageSend',
            'method': 'POST', 
            'api_key': getattr(settings, 'SMSIR_API_KEY', None),
        },
        'melipayamak': {
            'url': 'https://rest.payamak-panel.com/api/SendSMS/SendSMS',
            'method': 'POST',
            'username': getattr(settings, 'MELIPAYAMAK_USERNAME', None),
            'password': getattr(settings, 'MELIPAYAMAK_PASSWORD', None),
        }
    }
    
    # Get active SMS provider from settings
    active_provider = getattr(settings, 'SMS_PROVIDER', 'kavenegar')
    provider_config = SMS_PROVIDERS.get(active_provider)
    
    if not provider_config:
        logger.error(f"SMS provider '{active_provider}' not configured")
        return False
    
    try:
        if active_provider == 'kavenegar':
            return _send_sms_kavenegar(phone_number, message, provider_config)
        elif active_provider == 'smsir':
            return _send_sms_smsir(phone_number, message, provider_config)
        elif active_provider == 'melipayamak':
            return _send_sms_melipayamak(phone_number, message, provider_config)
        else:
            logger.error(f"SMS provider '{active_provider}' not implemented")
            return False
            
    except Exception as e:
        logger.error(f"Error sending SMS: {str(e)}")
        return False


def _send_sms_kavenegar(phone_number: str, message: str, config: dict) -> bool:
    """Send SMS via Kavenegar"""
    if not config['api_key']:
        logger.error("Kavenegar API key not configured")
        return False
    
    url = config['url'].format(api_key=config['api_key'])
    data = {
        'receptor': phone_number,
        'message': message,
        'sender': getattr(settings, 'SMS_SENDER_NUMBER', '10008663')
    }
    
    response = requests.post(url, data=data, timeout=30)
    
    if response.status_code == 200:
        result = response.json()
        if result.get('return', {}).get('status') == 200:
            logger.info(f"SMS sent successfully to {phone_number}")
            return True
        else:
            logger.error(f"Kavenegar error: {result}")
            return False
    else:
        logger.error(f"Kavenegar HTTP error: {response.status_code}")
        return False


def _send_sms_smsir(phone_number: str, message: str, config: dict) -> bool:
    """Send SMS via SMS.ir"""
    if not config['api_key']:
        logger.error("SMS.ir API key not configured")
        return False
    
    headers = {
        'Content-Type': 'application/json',
        'x-sms-ir-secure-token': config['api_key']
    }
    
    data = {
        'Messages': [message],
        'MobileNumbers': [phone_number],
        'LineNumber': getattr(settings, 'SMS_SENDER_NUMBER', '30007732')
    }
    
    response = requests.post(config['url'], json=data, headers=headers, timeout=30)
    
    if response.status_code == 201:
        result = response.json()
        if result.get('IsSuccessful'):
            logger.info(f"SMS sent successfully to {phone_number}")
            return True
        else:
            logger.error(f"SMS.ir error: {result}")
            return False
    else:
        logger.error(f"SMS.ir HTTP error: {response.status_code}")
        return False


def _send_sms_melipayamak(phone_number: str, message: str, config: dict) -> bool:
    """Send SMS via Melipayamak"""
    if not config['username'] or not config['password']:
        logger.error("Melipayamak credentials not configured")
        return False
    
    data = {
        'username': config['username'],
        'password': config['password'],
        'to': phone_number,
        'from': getattr(settings, 'SMS_SENDER_NUMBER', '50004001'),
        'text': message,
        'isFlash': False
    }
    
    response = requests.post(config['url'], json=data, timeout=30)
    
    if response.status_code == 200:
        result = response.json()
        if result.get('Value') > 0:  # Positive value means success
            logger.info(f"SMS sent successfully to {phone_number}")
            return True
        else:
            logger.error(f"Melipayamak error: {result}")
            return False
    else:
        logger.error(f"Melipayamak HTTP error: {response.status_code}")
        return False


def format_iranian_phone(phone_number: str) -> Optional[str]:
    """Format Iranian phone number to standard format"""
    if not phone_number:
        return None
        
    # Remove any non-digit characters
    phone = ''.join(filter(str.isdigit, phone_number))
    
    # Handle different input formats
    if phone.startswith('98'):
        phone = phone[2:]  # Remove country code
    elif phone.startswith('0'):
        phone = phone[1:]  # Remove leading zero
    
    # Add leading 09 if not present
    if not phone.startswith('9'):
        return None  # Invalid format
    
    formatted = f"0{phone}"
    
    # Validate final format
    if len(formatted) == 11 and formatted.startswith('09'):
        return formatted
    
    return None


def validate_iranian_phone(phone_number: str) -> bool:
    """Validate Iranian phone number format"""
    if not phone_number:
        return False
    
    formatted = format_iranian_phone(phone_number)
    return formatted is not None


def create_thumbnail(image_path: str, size: tuple = (300, 300)) -> Optional[str]:
    """Create thumbnail for product images"""
    try:
        from PIL import Image
        import os
        
        if not os.path.exists(image_path):
            return None
            
        # Open and resize image
        with Image.open(image_path) as img:
            img.thumbnail(size, Image.Resampling.LANCZOS)
            
            # Generate thumbnail path
            path_parts = image_path.rsplit('.', 1)
            thumbnail_path = f"{path_parts[0]}_thumb.{path_parts[1]}"
            
            # Save thumbnail
            img.save(thumbnail_path, optimize=True, quality=85)
            return thumbnail_path
            
    except Exception as e:
        logger.error(f"Error creating thumbnail: {str(e)}")
        return None


def generate_sku() -> str:
    """Generate unique SKU for products"""
    import uuid
    return f"P{uuid.uuid4().hex[:8].upper()}"


def calculate_shipping_cost(weight: float, city: str, shipping_method: str = 'standard') -> int:
    """Calculate shipping cost based on weight and destination"""
    # Base shipping rates for Iran (in Tomans)
    BASE_RATES = {
        'standard': 50000,  # Standard post
        'express': 120000,  # Express delivery
        'same_day': 200000, # Same day delivery (only major cities)
    }
    
    # Weight multiplier (per kg)
    WEIGHT_MULTIPLIER = {
        'standard': 15000,
        'express': 25000,
        'same_day': 30000,
    }
    
    # Major cities get better rates
    MAJOR_CITIES = ['تهران', 'مشهد', 'اصفهان', 'شیراز', 'تبریز', 'کرج', 'اهواز']
    
    base_cost = BASE_RATES.get(shipping_method, BASE_RATES['standard'])
    weight_cost = weight * WEIGHT_MULTIPLIER.get(shipping_method, WEIGHT_MULTIPLIER['standard'])
    
    # Apply city modifier
    if city not in MAJOR_CITIES:
        base_cost *= 1.2  # 20% extra for smaller cities
    
    return int(base_cost + weight_cost)


def persian_to_english_numbers(text: str) -> str:
    """Convert Persian numbers to English"""
    persian_digits = '۰۱۲۳۴۵۶۷۸۹'
    english_digits = '0123456789'
    
    for persian, english in zip(persian_digits, english_digits):
        text = text.replace(persian, english)
    
    return text


def english_to_persian_numbers(text: str) -> str:
    """Convert English numbers to Persian"""
    english_digits = '0123456789'
    persian_digits = '۰۱۲۳۴۵۶۷۸۹'
    
    for english, persian in zip(english_digits, persian_digits):
        text = text.replace(english, persian)
    
    return text


def format_price(price: int) -> str:
    """Format price with Persian thousand separators"""
    if price == 0:
        return 'رایگان'
    
    # Add thousand separators
    formatted = f"{price:,}".replace(',', '،')
    return f"{formatted} تومان"


def clean_html_tags(text: str) -> str:
    """Remove HTML tags from text"""
    import re
    clean = re.compile('<.*?>')
    return re.sub(clean, '', text)


def truncate_text(text: str, max_length: int = 100, suffix: str = '...') -> str:
    """Truncate text to specified length"""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def validate_national_id(national_id: str) -> bool:
    """Validate Iranian national ID"""
    if not national_id or len(national_id) != 10:
        return False
    
    # Convert to digits
    try:
        digits = [int(d) for d in national_id]
    except ValueError:
        return False
    
    # Check for same digits
    if len(set(digits)) == 1:
        return False
    
    # Calculate checksum
    checksum = 0
    for i in range(9):
        checksum += digits[i] * (10 - i)
    
    remainder = checksum % 11
    
    if remainder < 2:
        return digits[9] == remainder
    else:
        return digits[9] == 11 - remainder


def get_jalali_date(date_obj=None) -> str:
    """Convert Gregorian date to Jalali (Persian) date"""
    try:
        import jdatetime
        if date_obj is None:
            date_obj = datetime.now()
        
        jalali_date = jdatetime.datetime.fromgregorian(datetime=date_obj)
        return jalali_date.strftime('%Y/%m/%d')
    except ImportError:
        # Fallback to Gregorian if jdatetime not available
        if date_obj is None:
            date_obj = datetime.now()
        return date_obj.strftime('%Y/%m/%d')


def extract_social_media_content(post_data: dict) -> dict:
    """
    Extract and parse social media content for product import
    Product description: "get from social media button" functionality
    """
    extracted = {
        'texts': [],
        'images': [],
        'videos': [],
        'hashtags': [],
        'mentions': []
    }
    
    # Extract text content
    text = post_data.get('text', '') or post_data.get('caption', '')
    if text:
        extracted['texts'].append(text)
        
        # Extract hashtags
        hashtags = re.findall(r'#\w+', text)
        extracted['hashtags'].extend(hashtags)
        
        # Extract mentions
        mentions = re.findall(r'@\w+', text)
        extracted['mentions'].extend(mentions)
    
    # Extract media URLs
    media = post_data.get('media', [])
    if isinstance(media, list):
        for item in media:
            if item.get('type') == 'photo':
                extracted['images'].append(item.get('url'))
            elif item.get('type') == 'video':
                extracted['videos'].append(item.get('url'))
    
    return extracted