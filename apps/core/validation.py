"""
Enhanced validation utilities for Mall platform
Consolidates and improves validation logic across the platform
"""

from django.core.exceptions import ValidationError
from django.db.models import Sum
from decimal import Decimal
import re
from typing import Dict, Any, Optional


class ProductValidationService:
    """
    Centralized validation service for product-related operations
    Eliminates validation duplication across serializers and models
    """
    
    @staticmethod
    def validate_product_class_hierarchy(product_class_id: str, category_id: str, store_id: str = None):
        """
        Comprehensive validation for product class and category compatibility
        """
        from apps.products.models import ProductClass, ProductCategory
        
        errors = {}
        
        # Validate product class exists and is leaf
        try:
            product_class = ProductClass.objects.get(id=product_class_id)
            if not product_class.is_leaf:
                errors['product_class'] = "محصول فقط می‌تواند به کلاس‌های پایانی اختصاص یابد"
        except ProductClass.DoesNotExist:
            errors['product_class'] = "کلاس محصول معتبر نیست"
            return errors
        
        # Validate category exists
        try:
            category = ProductCategory.objects.get(id=category_id)
        except ProductCategory.DoesNotExist:
            errors['category'] = "دسته‌بندی معتبر نیست"
            return errors
        
        # Validate store consistency
        if store_id:
            if str(product_class.store_id) != str(store_id):
                errors['product_class'] = "کلاس محصول باید به همان فروشگاه تعلق داشته باشد"
            if str(category.store_id) != str(store_id):
                errors['category'] = "دسته‌بندی باید به همان فروشگاه تعلق داشته باشد"
        
        if product_class.store != category.store:
            errors['general'] = "کلاس محصول و دسته‌بندی باید به یک فروشگاه تعلق داشته باشند"
        
        if errors:
            raise ValidationError(errors)
        
        return {
            'product_class': product_class,
            'category': category,
            'valid': True
        }
    
    @staticmethod
    def validate_stock_consistency(product):
        """
        Validate stock consistency across product variants
        """
        if product.product_type == 'variable':
            total_variant_stock = product.variants.aggregate(
                total=Sum('stock_quantity')
            )['total'] or 0
            
            if product.manage_stock and product.stock_quantity != total_variant_stock:
                raise ValidationError({
                    'stock_quantity': f"موجودی محصول ({product.stock_quantity}) باید برابر مجموع موجودی انواع آن ({total_variant_stock}) باشد"
                })
    
    @staticmethod
    def validate_price_hierarchy(product_class, base_price: Decimal = None):
        """
        Validate price hierarchy and inheritance rules
        """
        if base_price is None and not product_class.get_effective_price():
            raise ValidationError({
                'base_price': "قیمت باید تعریف شود یا از کلاس والد به ارث برسد"
            })
        
        # Check for reasonable price ranges
        if base_price and base_price < 0:
            raise ValidationError({
                'base_price': "قیمت نمی‌تواند منفی باشد"
            })
        
        if base_price and base_price > 999999999:
            raise ValidationError({
                'base_price': "قیمت خیلی زیاد است"
            })
    
    @staticmethod
    def validate_attribute_values(product, attribute_values: list):
        """
        Validate product attribute values against inherited attributes
        """
        # Get required attributes from product class hierarchy
        inherited_attrs = product.product_class.get_inherited_attributes()
        required_attr_ids = set(
            attr.attribute_type.id for attr in inherited_attrs 
            if attr.is_required
        )
        
        # Get provided attribute IDs
        provided_attr_ids = set(
            attr_val.get('attribute_id') or attr_val.get('attribute', {}).get('id')
            for attr_val in attribute_values
        )
        
        missing_attrs = required_attr_ids - provided_attr_ids
        if missing_attrs:
            from apps.products.models import AttributeType
            missing_names = AttributeType.objects.filter(
                id__in=missing_attrs
            ).values_list('name_fa', flat=True)
            
            raise ValidationError({
                'attribute_values': f"ویژگی‌های اجباری ناقص: {', '.join(missing_names)}"
            })


class StoreValidationService:
    """
    Validation service for store-related operations
    """
    
    @staticmethod
    def validate_store_limits(store, product_count: int = None):
        """
        Validate store against platform limits
        """
        from django.conf import settings
        
        # Check product limit
        current_products = store.products.filter(status='published').count()
        if product_count:
            current_products += product_count
        
        max_products = getattr(settings, 'MAX_PRODUCTS_PER_STORE', 1000)
        if current_products > max_products:
            raise ValidationError({
                'products': f"حداکثر تعداد محصولات ({max_products}) در فروشگاه فراتر رفته است"
            })
        
        # Check customer limit
        customer_count = store.customers.count()
        max_customers = getattr(settings, 'MAX_CUSTOMERS_PER_STORE', 1000)
        if customer_count > max_customers:
            raise ValidationError({
                'customers': f"حداکثر تعداد مشتریان ({max_customers}) در فروشگاه فراتر رفته است"
            })
    
    @staticmethod
    def validate_domain(domain: str, store_id: str = None):
        """
        Validate store domain uniqueness and format
        """
        from apps.stores.models import Store
        
        # Domain format validation
        domain_pattern = re.compile(
            r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?$'
        )
        if not domain_pattern.match(domain):
            raise ValidationError({
                'domain': "فرمت دامنه معتبر نیست"
            })
        
        # Check uniqueness
        existing_stores = Store.objects.filter(domain=domain)
        if store_id:
            existing_stores = existing_stores.exclude(id=store_id)
        
        if existing_stores.exists():
            raise ValidationError({
                'domain': "این دامنه قبلاً استفاده شده است"
            })


class SocialMediaValidationService:
    """
    Validation service for social media integration
    """
    
    @staticmethod
    def validate_social_media_post(platform: str, post_id: str, access_token: str = None):
        """
        Validate social media post exists and is accessible
        """
        if platform == 'telegram':
            return SocialMediaValidationService._validate_telegram_post(post_id)
        elif platform == 'instagram':
            return SocialMediaValidationService._validate_instagram_post(post_id, access_token)
        else:
            raise ValidationError({
                'platform': "پلتفرم شبکه اجتماعی پشتیبانی نمی‌شود"
            })
    
    @staticmethod
    def _validate_telegram_post(post_id: str):
        """Validate Telegram post ID format"""
        # Telegram post ID format: channel_username/message_id
        pattern = re.compile(r'^@?[a-zA-Z0-9_]{5,32}/\d+$')
        if not pattern.match(post_id):
            raise ValidationError({
                'post_id': "فرمت شناسه پست تلگرام معتبر نیست (مثال: @channel/123)"
            })
        return True
    
    @staticmethod
    def _validate_instagram_post(post_id: str, access_token: str):
        """Validate Instagram post ID and access token"""
        if not access_token:
            raise ValidationError({
                'access_token': "توکن دسترسی اینستاگرام الزامی است"
            })
        
        # Instagram post ID validation
        pattern = re.compile(r'^\d{10,20}$')
        if not pattern.match(post_id):
            raise ValidationError({
                'post_id': "فرمت شناسه پست اینستاگرام معتبر نیست"
            })
        return True


class PersianTextValidator:
    """
    Enhanced Persian text validation
    """
    
    @staticmethod
    def validate_persian_content(text: str, field_name: str = 'text'):
        """
        Validate Persian text content with comprehensive checks
        """
        if not text or not text.strip():
            return True  # Empty is allowed unless specified otherwise
        
        # Persian character pattern
        persian_pattern = re.compile(
            r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]'
        )
        
        # Check for Persian characters
        if not persian_pattern.search(text):
            raise ValidationError({
                field_name: 'متن باید شامل حروف فارسی باشد'
            })
        
        # Check for inappropriate content (basic)
        inappropriate_words = ['spam', 'test123']  # Extend as needed
        text_lower = text.lower()
        for word in inappropriate_words:
            if word in text_lower:
                raise ValidationError({
                    field_name: 'متن شامل محتوای نامناسب است'
                })
        
        return True
    
    @staticmethod
    def validate_slug_persian(slug: str, original_text: str = None):
        """
        Validate Persian-compatible slug
        """
        # Basic slug pattern (allowing Persian and English)
        slug_pattern = re.compile(r'^[\u0600-\u06FFa-zA-Z0-9\-_]+$')
        if not slug_pattern.match(slug):
            raise ValidationError({
                'slug': 'نامک فقط می‌تواند شامل حروف، اعداد و خط تیره باشد'
            })
        
        # Length validation
        if len(slug) < 2:
            raise ValidationError({
                'slug': 'نامک باید حداقل ۲ کاراکتر باشد'
            })
        
        if len(slug) > 100:
            raise ValidationError({
                'slug': 'نامک باید حداکثر ۱۰۰ کاراکتر باشد'
            })


class FileValidationService:
    """
    File upload validation service
    """
    
    @staticmethod
    def validate_image(image_file, max_size_mb: int = 10):
        """
        Validate uploaded image files
        """
        if not image_file:
            return True
        
        # Size validation
        max_size = max_size_mb * 1024 * 1024  # Convert to bytes
        if image_file.size > max_size:
            raise ValidationError({
                'image': f'حجم تصویر باید کمتر از {max_size_mb} مگابایت باشد'
            })
        
        # Type validation
        allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp']
        if hasattr(image_file, 'content_type'):
            if image_file.content_type not in allowed_types:
                raise ValidationError({
                    'image': 'فرمت تصویر باید JPEG، PNG یا WebP باشد'
                })
        
        return True
    
    @staticmethod
    def validate_video(video_file, max_size_mb: int = 100):
        """
        Validate uploaded video files
        """
        if not video_file:
            return True
        
        # Size validation
        max_size = max_size_mb * 1024 * 1024  # Convert to bytes
        if video_file.size > max_size:
            raise ValidationError({
                'video': f'حجم ویدیو باید کمتر از {max_size_mb} مگابایت باشد'
            })
        
        # Type validation
        allowed_types = ['video/mp4', 'video/webm', 'video/ogg']
        if hasattr(video_file, 'content_type'):
            if video_file.content_type not in allowed_types:
                raise ValidationError({
                    'video': 'فرمت ویدیو باید MP4، WebM یا OGG باشد'
                })
        
        return True


def validate_business_rules(model_instance, action: str = 'create', **kwargs):
    """
    Central business rules validation
    """
    from apps.products.models import Product, ProductClass
    from apps.stores.models import Store
    
    if isinstance(model_instance, Product):
        if action in ['create', 'update']:
            # Product-specific validations
            ProductValidationService.validate_product_class_hierarchy(
                product_class_id=model_instance.product_class_id,
                category_id=model_instance.category_id,
                store_id=model_instance.store_id
            )
            
            ProductValidationService.validate_price_hierarchy(
                product_class=model_instance.product_class,
                base_price=model_instance.base_price
            )
            
            ProductValidationService.validate_stock_consistency(model_instance)
            
            # Store limits validation
            if action == 'create':
                StoreValidationService.validate_store_limits(
                    store=model_instance.store,
                    product_count=1
                )
    
    elif isinstance(model_instance, Store):
        if action in ['create', 'update']:
            if hasattr(model_instance, 'domain') and model_instance.domain:
                StoreValidationService.validate_domain(
                    domain=model_instance.domain,
                    store_id=model_instance.id if action == 'update' else None
                )


# Decorator for automatic validation
def validate_on_save(func):
    """
    Decorator to automatically run business rule validation on model save
    """
    def wrapper(self, *args, **kwargs):
        # Run validation before save
        if hasattr(self, 'id') and self.id:
            action = 'update'
        else:
            action = 'create'
        
        try:
            validate_business_rules(self, action=action)
        except ValidationError as e:
            # Re-raise with model context
            raise ValidationError(f"Validation failed for {self.__class__.__name__}: {e}")
        
        return func(self, *args, **kwargs)
    
    return wrapper
