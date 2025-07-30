from rest_framework import serializers
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from typing import Any, Optional
import re

class MallValidators:
    """Centralized validation logic for Mall platform"""
    
    # Phone number validation for Iranian numbers
    IRANIAN_PHONE_REGEX = r'^(\+98|0)?9\d{9}$'
    
    @staticmethod
    def validate_iranian_phone(phone: str) -> str:
        """Validate Iranian phone number format"""
        if not re.match(MallValidators.IRANIAN_PHONE_REGEX, phone):
            raise serializers.ValidationError(
                "شماره تلفن باید به فرمت ایرانی باشد (مثال: 09123456789)"
            )
        # Normalize to +98 format
        if phone.startswith('0'):
            phone = '+98' + phone[1:]
        elif not phone.startswith('+98'):
            phone = '+98' + phone
        return phone
    
    @staticmethod
    def validate_leaf_product_class(value) -> Any:
        """Validate that product class is a leaf node (reusable)"""
        if hasattr(value, 'is_leaf') and not value.is_leaf:
            raise serializers.ValidationError(
                "فقط کلاس‌های پایانی می‌توانند محصول داشته باشند"
            )
        return value
    
    @staticmethod
    def validate_sku_format(sku: str) -> str:
        """Validate SKU format"""
        if not re.match(r'^[A-Z0-9-_]{3,20}$', sku.upper()):
            raise serializers.ValidationError(
                "کد محصول باید شامل حروف انگلیسی، اعداد و خط تیره باشد (3-20 کاراکتر)"
            )
        return sku.upper()
    
    @staticmethod
    def validate_persian_text(text: str, field_name: str = "متن") -> str:
        """Validate Persian text contains valid characters"""
        if not text.strip():
            raise serializers.ValidationError(f"{field_name} نمی‌تواند خالی باشد")
        
        # Check for minimum Persian characters (at least 50% should be Persian/Arabic)
        persian_chars = len(re.findall(r'[\u0600-\u06FF\u200C\u200D\s]', text))
        if persian_chars < len(text) * 0.3:  # At least 30% Persian chars
            raise serializers.ValidationError(
                f"{field_name} باید شامل متن فارسی باشد"
            )
        return text.strip()
    
    @staticmethod
    def validate_price_range(price: float, min_price: float = 0, max_price: float = 1000000000) -> float:
        """Validate price is within acceptable range"""
        if price < min_price:
            raise serializers.ValidationError(f"قیمت نمی‌تواند کمتر از {min_price:,} تومان باشد")
        if price > max_price:
            raise serializers.ValidationError(f"قیمت نمی‌تواند بیشتر از {max_price:,} تومان باشد")
        return price
    
    @staticmethod
    def validate_slug_uniqueness(slug: str, model_class, store_id: Optional[str] = None, exclude_id: Optional[str] = None):
        """Validate slug uniqueness within store context"""
        queryset = model_class.objects.filter(slug=slug)
        
        if store_id:
            queryset = queryset.filter(store_id=store_id)
        
        if exclude_id:
            queryset = queryset.exclude(id=exclude_id)
        
        if queryset.exists():
            raise serializers.ValidationError("این نامک قبلاً استفاده شده است")
        
        return slug

class StorePermissionValidator:
    """Store-specific permission validations"""
    
    @staticmethod
    def validate_store_owner(user, store):
        """Validate user is store owner"""
        if store.owner != user:
            raise serializers.ValidationError("شما مجاز به انجام این عمل نیستید")
        return True
    
    @staticmethod
    def validate_store_limits(store, limit_type: str, current_count: int):
        """Validate store hasn't exceeded limits"""
        from django.conf import settings
        
        limits = {
            'products': getattr(settings, 'MAX_PRODUCTS_PER_STORE', 1000),
            'customers': getattr(settings, 'MAX_CUSTOMERS_PER_STORE', 1000),
            'categories': 100,
            'brands': 50,
        }
        
        if current_count >= limits.get(limit_type, 1000):
            raise serializers.ValidationError(
                f"حداکثر تعداد {limit_type} برای فروشگاه شما {limits[limit_type]} است"
            )
        return True

# Custom field validators
persian_text_validator = RegexValidator(
    regex=r'[\u0600-\u06FF\u200C\u200D\s]+',
    message='متن باید شامل حروف فارسی باشد'
)

slug_validator = RegexValidator(
    regex=r'^[-a-zA-Z0-9_]+$',
    message='نامک فقط می‌تواند شامل حروف انگلیسی، اعداد و خط تیره باشد'
)
