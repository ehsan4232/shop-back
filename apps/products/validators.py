"""
Centralized validators for products app to eliminate code duplication
"""
from rest_framework import serializers
from django.core.exceptions import ValidationError as DjangoValidationError
from .models import ProductClass, ProductCategory, Product, Brand


class ProductValidators:
    """Centralized validation logic for products"""
    
    @staticmethod
    def validate_leaf_product_class(value):
        """Validate that product class is a leaf node (can have products)"""
        if not value.is_leaf:
            raise serializers.ValidationError(
                "فقط کلاس‌های پایانی می‌توانند محصول داشته باشند"
            )
        return value
    
    @staticmethod
    def validate_store_ownership(user, store_related_object):
        """Validate that user owns the store of the related object"""
        if hasattr(store_related_object, 'store'):
            store = store_related_object.store
        else:
            store = store_related_object
            
        if store.owner != user:
            raise serializers.ValidationError("دسترسی غیرمجاز - شما مالک این فروشگاه نیستید")
        return store_related_object
    
    @staticmethod
    def validate_product_class_store_match(product_class, store):
        """Validate that product class belongs to the same store"""
        if product_class.store != store:
            raise serializers.ValidationError(
                "کلاس محصول باید متعلق به همین فروشگاه باشد"
            )
        return product_class
    
    @staticmethod
    def validate_category_store_match(category, store):
        """Validate that category belongs to the same store"""
        if category.store != store:
            raise serializers.ValidationError(
                "دسته‌بندی باید متعلق به همین فروشگاه باشد"
            )
        return category
    
    @staticmethod
    def validate_brand_store_match(brand, store):
        """Validate that brand belongs to the same store (if provided)"""
        if brand and brand.store != store:
            raise serializers.ValidationError(
                "برند باید متعلق به همین فروشگاه باشد"
            )
        return brand
    
    @staticmethod
    def validate_sku_uniqueness(sku, store, product_instance=None):
        """Validate SKU uniqueness within store"""
        if not sku:
            return sku
            
        existing_products = Product.objects.filter(
            store=store,
            sku=sku
        )
        
        # Exclude current product if updating
        if product_instance:
            existing_products = existing_products.exclude(id=product_instance.id)
        
        if existing_products.exists():
            raise serializers.ValidationError(
                f"کد محصول '{sku}' قبلاً در این فروشگاه استفاده شده است"
            )
        return sku
    
    @staticmethod
    def validate_stock_quantity(quantity):
        """Validate stock quantity"""
        if quantity < 0:
            raise serializers.ValidationError("موجودی نمی‌تواند منفی باشد")
        return quantity
    
    @staticmethod
    def validate_price(price):
        """Validate price values"""
        if price < 0:
            raise serializers.ValidationError("قیمت نمی‌تواند منفی باشد")
        return price
    
    @staticmethod
    def validate_variants_data_for_variable_product(product_type, variants_data):
        """Validate that variable products have variant data"""
        if product_type == 'variable' and not variants_data:
            raise serializers.ValidationError(
                "محصولات متغیر باید حداقل یک نوع داشته باشند"
            )
        return variants_data
    
    @staticmethod
    def validate_weight(weight):
        """Validate product weight"""
        if weight is not None and weight < 0:
            raise serializers.ValidationError("وزن نمی‌تواند منفی باشد")
        return weight


class CategoryValidators:
    """Centralized validation logic for categories"""
    
    @staticmethod
    def validate_parent_same_store(parent, store):
        """Validate that parent category is in the same store"""
        if parent and parent.store != store:
            raise serializers.ValidationError(
                "دسته‌بندی والد باید در همین فروشگاه باشد"
            )
        return parent
    
    @staticmethod
    def validate_not_self_parent(category_instance, parent):
        """Validate that category is not its own parent"""
        if category_instance and parent and category_instance.id == parent.id:
            raise serializers.ValidationError(
                "دسته‌بندی نمی‌تواند والد خودش باشد"
            )
        return parent
    
    @staticmethod
    def validate_no_circular_reference(category_instance, parent):
        """Validate no circular reference in category hierarchy"""
        if category_instance and parent:
            # Check if proposed parent is a descendant of current category
            if category_instance.get_descendants().filter(id=parent.id).exists():
                raise serializers.ValidationError(
                    "ایجاد مرجع دایره‌ای در ساختار دسته‌بندی‌ها ممکن نیست"
                )
        return parent


class ProductClassValidators:
    """Centralized validation logic for product classes"""
    
    @staticmethod
    def validate_parent_same_store(parent, store):
        """Validate that parent class is in the same store"""
        if parent and parent.store != store:
            raise serializers.ValidationError(
                "کلاس والد باید در همین فروشگاه باشد"
            )
        return parent
    
    @staticmethod
    def validate_not_self_parent(class_instance, parent):
        """Validate that class is not its own parent"""
        if class_instance and parent and class_instance.id == parent.id:
            raise serializers.ValidationError(
                "کلاس نمی‌تواند والد خودش باشد"
            )
        return parent
    
    @staticmethod
    def validate_no_circular_reference(class_instance, parent):
        """Validate no circular reference in class hierarchy"""
        if class_instance and parent:
            # Check if proposed parent is a descendant of current class
            if class_instance.get_descendants().filter(id=parent.id).exists():
                raise serializers.ValidationError(
                    "ایجاد مرجع دایره‌ای در ساختار کلاس‌ها ممکن نیست"
                )
        return parent
    
    @staticmethod
    def validate_base_price_inheritance(base_price, parent):
        """Validate base price inheritance logic"""
        if base_price is None and parent and parent.get_effective_price() == 0:
            raise serializers.ValidationError(
                "قیمت پایه الزامی است زیرا کلاس والد قیمت ندارد"
            )
        return base_price


class SlugValidators:
    """Centralized validation logic for slugs"""
    
    @staticmethod
    def validate_slug_format(slug):
        """Validate slug format"""
        import re
        if not re.match(r'^[a-z0-9]+(?:-[a-z0-9]+)*$', slug):
            raise serializers.ValidationError(
                "نامک باید شامل حروف کوچک انگلیسی، اعداد و خط تیره باشد"
            )
        return slug
    
    @staticmethod
    def validate_slug_uniqueness(model_class, slug, store, instance=None):
        """Validate slug uniqueness within store"""
        existing = model_class.objects.filter(store=store, slug=slug)
        
        if instance:
            existing = existing.exclude(id=instance.id)
        
        if existing.exists():
            raise serializers.ValidationError(
                f"نامک '{slug}' قبلاً در این فروشگاه استفاده شده است"
            )
        return slug


class AttributeValidators:
    """Centralized validation logic for attributes"""
    
    @staticmethod
    def validate_attribute_value_type(attribute_type, value):
        """Validate attribute value matches its type"""
        if not value:
            return value
            
        data_type = attribute_type.data_type
        
        try:
            if data_type == 'number':
                float(value)
            elif data_type == 'boolean':
                if value.lower() not in ['true', 'false', '1', '0', 'yes', 'no']:
                    raise ValueError()
            elif data_type == 'date':
                from datetime import datetime
                datetime.strptime(value, '%Y-%m-%d')
            # For text, color, size, choice - any string is acceptable
        except (ValueError, TypeError):
            raise serializers.ValidationError(
                f"مقدار '{value}' برای نوع '{data_type}' معتبر نیست"
            )
        
        return value
    
    @staticmethod
    def validate_color_value(value):
        """Validate color value (hex format)"""
        if value and not value.startswith('#'):
            raise serializers.ValidationError("رنگ باید در فرمت hex باشد (مثل #FF0000)")
        
        if value and len(value) != 7:
            raise serializers.ValidationError("رنگ باید 7 کاراکتر باشد (#RRGGBB)")
        
        return value


# Utility function to apply common validations
def apply_store_validations(serializer_instance, validated_data, user):
    """Apply common store-related validations"""
    store = validated_data.get('store')
    
    if store:
        ProductValidators.validate_store_ownership(user, store)
    
    # Validate related objects belong to same store
    if 'product_class' in validated_data and store:
        ProductValidators.validate_product_class_store_match(
            validated_data['product_class'], store
        )
    
    if 'category' in validated_data and store:
        ProductValidators.validate_category_store_match(
            validated_data['category'], store
        )
    
    if 'brand' in validated_data and store:
        ProductValidators.validate_brand_store_match(
            validated_data['brand'], store
        )
    
    return validated_data
