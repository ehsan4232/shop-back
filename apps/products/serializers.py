from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import *

User = get_user_model()

class AttributeTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttributeType
        fields = [
            'id', 'name', 'name_fa', 'display_type', 'filter_type',
            'unit', 'predefined_choices', 'is_filterable', 'is_searchable',
            'show_in_listing', 'is_variant_creating'
        ]

class ProductAttributeSerializer(serializers.ModelSerializer):
    attribute_type = AttributeTypeSerializer(read_only=True)
    
    class Meta:
        model = ProductAttribute
        fields = [
            'id', 'attribute_type', 'is_required', 'display_order',
            'custom_choices', 'min_value', 'max_value', 'effective_choices',
            'is_variant_creating'
        ]

class CategorySerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()
    product_count = serializers.SerializerMethodField()
    path = serializers.SerializerMethodField()
    attributes = ProductAttributeSerializer(many=True, read_only=True)
    
    class Meta:
        model = ProductCategory
        fields = [
            'id', 'name', 'name_fa', 'slug', 'description', 'icon', 
            'banner_image', 'category_type', 'children', 'product_count', 
            'path', 'attributes', 'display_order', 'is_leaf'
        ]
    
    def get_children(self, obj):
        if obj.children.exists():
            return CategorySerializer(
                obj.children.filter(is_active=True), 
                many=True, 
                context=self.context
            ).data
        return []
    
    def get_product_count(self, obj):
        return obj.product_count_cache
    
    def get_path(self, obj):
        """Get category path for breadcrumbs"""
        path = []
        for ancestor in obj.get_ancestors(include_self=True):
            path.append({
                'id': str(ancestor.id),
                'name': ancestor.name,
                'name_fa': ancestor.name_fa,
                'slug': ancestor.slug
            })
        return path

class CategoryDetailSerializer(CategorySerializer):
    all_attributes = serializers.SerializerMethodField()
    
    class Meta(CategorySerializer.Meta):
        fields = CategorySerializer.Meta.fields + ['all_attributes']
    
    def get_all_attributes(self, obj):
        """Get all available attributes including inherited"""
        return ProductAttributeSerializer(obj.get_all_attributes(), many=True).data

class BrandSerializer(serializers.ModelSerializer):
    product_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Brand
        fields = [
            'id', 'name', 'name_fa', 'slug', 'logo', 'description',
            'website', 'country_of_origin', 'product_count', 'is_featured'
        ]
    
    def get_product_count(self, obj):
        return obj.product_count

class BrandDetailSerializer(BrandSerializer):
    class Meta(BrandSerializer.Meta):
        fields = BrandSerializer.Meta.fields + ['view_count']

class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = [
            'id', 'name', 'name_fa', 'slug', 'tag_type', 'color',
            'icon', 'description', 'usage_count', 'is_featured'
        ]

class AttributeValueSerializer(serializers.ModelSerializer):
    attribute_name = serializers.CharField(source='attribute.attribute_type.name_fa', read_only=True)
    attribute_type = serializers.CharField(source='attribute.attribute_type.display_type', read_only=True)
    unit = serializers.CharField(source='attribute.attribute_type.unit', read_only=True)
    
    class Meta:
        model = ProductAttributeValue
        fields = [
            'attribute_name', 'attribute_type', 'unit', 'display_value', 
            'color_hex', 'value_json', 'value_image'
        ]

class ProductVariantSerializer(serializers.ModelSerializer):
    attributes = AttributeValueSerializer(source='attribute_values', many=True, read_only=True)
    in_stock = serializers.SerializerMethodField()
    discount_percentage = serializers.SerializerMethodField()
    attribute_summary = serializers.SerializerMethodField()
    
    class Meta:
        model = ProductVariant
        fields = [
            'id', 'sku', 'price', 'compare_price', 'stock_quantity',
            'weight', 'dimensions', 'image', 'is_default', 'attributes', 
            'in_stock', 'discount_percentage', 'attribute_summary'
        ]
    
    def get_in_stock(self, obj):
        return obj.in_stock
    
    def get_discount_percentage(self, obj):
        return obj.discount_percentage
    
    def get_attribute_summary(self, obj):
        return obj.get_attribute_summary()

class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = [
            'id', 'image', 'alt_text', 'title', 'is_featured', 
            'display_order', 'imported_from_social', 'social_media_url'
        ]

class ProductListSerializer(serializers.ModelSerializer):
    brand_name = serializers.CharField(source='brand.name_fa', read_only=True)
    brand_slug = serializers.CharField(source='brand.slug', read_only=True)
    category_name = serializers.CharField(source='category.name_fa', read_only=True)
    category_path = serializers.SerializerMethodField()
    price_range = serializers.SerializerMethodField()
    in_stock = serializers.SerializerMethodField()
    discount_percentage = serializers.SerializerMethodField()
    images = ProductImageSerializer(many=True, read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'name_fa', 'slug', 'short_description',
            'featured_image', 'brand_name', 'brand_slug', 'category_name', 
            'category_path', 'price_range', 'rating_average', 'rating_count', 
            'in_stock', 'discount_percentage', 'view_count', 'sales_count', 
            'images', 'tags', 'is_featured', 'is_digital', 'created_at'
        ]
    
    def get_category_path(self, obj):
        path = []
        for ancestor in obj.category.get_ancestors(include_self=True):
            path.append({
                'name': ancestor.name,
                'name_fa': ancestor.name_fa,
                'slug': ancestor.slug
            })
        return path
    
    def get_price_range(self, obj):
        min_price, max_price = obj.get_price_range()
        return {
            'min': min_price,
            'max': max_price,
            'formatted_min': f"{min_price:,} تومان",
            'formatted_max': f"{max_price:,} تومان"
        }
    
    def get_in_stock(self, obj):
        return obj.in_stock
    
    def get_discount_percentage(self, obj):
        return obj.discount_percentage

class ProductDetailSerializer(ProductListSerializer):
    variants = ProductVariantSerializer(many=True, read_only=True)
    attributes = AttributeValueSerializer(source='attribute_values', many=True, read_only=True)
    available_attributes = serializers.SerializerMethodField()
    variant_creating_attributes = serializers.SerializerMethodField()
    related_products = ProductListSerializer(many=True, read_only=True)
    brand = BrandSerializer(read_only=True)
    category = CategoryDetailSerializer(read_only=True)
    
    class Meta(ProductListSerializer.Meta):
        fields = ProductListSerializer.Meta.fields + [
            'description', 'base_price', 'compare_price', 'cost_price',
            'product_type', 'sku', 'stock_quantity', 'manage_stock',
            'low_stock_threshold', 'weight', 'dimensions', 'digital_file',
            'download_limit', 'download_expiry_days', 'variants', 'attributes', 
            'available_attributes', 'variant_creating_attributes', 'related_products',
            'brand', 'category', 'meta_title', 'meta_description', 'meta_keywords',
            'imported_from_social', 'social_media_source', 'published_at'
        ]
    
    def get_available_attributes(self, obj):
        """Get all available attributes for this product"""
        return ProductAttributeSerializer(obj.get_available_attributes(), many=True).data
    
    def get_variant_creating_attributes(self, obj):
        """Get attributes that create variants"""
        return ProductAttributeSerializer(obj.get_variant_creating_attributes(), many=True).data

class ProductCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = [
            'name', 'name_fa', 'slug', 'description', 'short_description',
            'category', 'brand', 'product_type', 'base_price', 'compare_price',
            'cost_price', 'sku', 'stock_quantity', 'manage_stock', 
            'low_stock_threshold', 'weight', 'dimensions', 'featured_image',
            'tags', 'related_products', 'meta_title', 'meta_description', 
            'meta_keywords', 'status', 'is_featured', 'is_digital'
        ]
    
    def validate_slug(self, value):
        """Ensure slug uniqueness within store"""
        store = self.context['request'].user.stores.first()
        qs = Product.objects.filter(store=store, slug=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('این نامک قبلاً استفاده شده است.')
        return value
    
    def validate_category(self, value):
        """Ensure category is a leaf node"""
        if not value.is_leaf:
            raise serializers.ValidationError('فقط می‌توان محصول را به دسته‌بندی‌های پایانی اختصاص داد.')
        return value

class CollectionSerializer(serializers.ModelSerializer):
    products_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Collection
        fields = [
            'id', 'name', 'name_fa', 'slug', 'description', 'collection_type',
            'featured_image', 'is_featured', 'display_order', 'products_count',
            'meta_title', 'meta_description'
        ]
    
    def get_products_count(self, obj):
        return obj.get_products().count()

class CollectionDetailSerializer(CollectionSerializer):
    products = ProductListSerializer(source='get_products', many=True, read_only=True)
    auto_rules = serializers.JSONField(read_only=True)
    
    class Meta(CollectionSerializer.Meta):
        fields = CollectionSerializer.Meta.fields + ['products', 'auto_rules']

# Utility Serializers for Filtering
class FilterChoiceSerializer(serializers.Serializer):
    value = serializers.CharField()
    label = serializers.CharField()
    count = serializers.IntegerField()

class FilterGroupSerializer(serializers.Serializer):
    name = serializers.CharField()
    type = serializers.CharField()
    choices = FilterChoiceSerializer(many=True, required=False)
    min_value = serializers.DecimalField(max_digits=12, decimal_places=0, required=False)
    max_value = serializers.DecimalField(max_digits=12, decimal_places=0, required=False)

# Statistics Serializers
class StoreStatisticsSerializer(serializers.Serializer):
    total_products = serializers.IntegerField()
    total_categories = serializers.IntegerField()
    total_brands = serializers.IntegerField()
    featured_products = serializers.IntegerField()
    recent_products = ProductListSerializer(many=True)
    popular_products = ProductListSerializer(many=True)
    featured_collections = CollectionSerializer(many=True)
