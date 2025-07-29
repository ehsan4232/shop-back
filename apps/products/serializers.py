from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator
from .models import (
    ProductCategory, AttributeType, ProductAttribute, Brand, Tag,
    Product, ProductVariant, ProductAttributeValue, ProductImage, Collection
)

class AttributeTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttributeType
        fields = '__all__'

class ProductAttributeSerializer(serializers.ModelSerializer):
    attribute_type = AttributeTypeSerializer(read_only=True)
    attribute_type_id = serializers.UUIDField(write_only=True)
    effective_choices = serializers.ReadOnlyField()
    
    class Meta:
        model = ProductAttribute
        fields = [
            'id', 'attribute_type', 'attribute_type_id', 'is_required',
            'display_order', 'custom_choices', 'min_value', 'max_value',
            'is_inherited', 'inherited_from', 'effective_choices', 'is_variant_creating'
        ]

class ProductCategorySerializer(serializers.ModelSerializer):
    attributes = ProductAttributeSerializer(many=True, read_only=True)
    children = serializers.SerializerMethodField()
    parent_name = serializers.CharField(source='parent.name_fa', read_only=True)
    all_attributes = serializers.SerializerMethodField()
    product_count = serializers.ReadOnlyField(source='product_count_cache')
    
    class Meta:
        model = ProductCategory
        fields = [
            'id', 'name', 'name_fa', 'slug', 'description', 'parent', 'parent_name',
            'category_type', 'icon', 'banner_image', 'display_order', 'show_in_menu',
            'is_active', 'meta_title', 'meta_description', 'product_count',
            'view_count', 'is_leaf', 'attributes', 'all_attributes', 'children',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['is_leaf', 'product_count']
    
    def get_children(self, obj):
        """Get immediate children categories"""
        children = obj.get_children().filter(is_active=True)
        return ProductCategorySerializer(children, many=True, context=self.context).data
    
    def get_all_attributes(self, obj):
        """Get all attributes including inherited ones"""
        return ProductAttributeSerializer(obj.get_all_attributes(), many=True).data

class BrandSerializer(serializers.ModelSerializer):
    product_count = serializers.ReadOnlyField()
    
    class Meta:
        model = Brand
        fields = [
            'id', 'name', 'name_fa', 'slug', 'logo', 'description',
            'website', 'country_of_origin', 'is_featured', 'is_active',
            'display_order', 'product_count', 'view_count',
            'created_at', 'updated_at'
        ]

class TagSerializer(serializers.ModelSerializer):
    usage_count = serializers.ReadOnlyField()
    
    class Meta:
        model = Tag
        fields = [
            'id', 'name', 'name_fa', 'slug', 'tag_type', 'color',
            'icon', 'description', 'is_featured', 'is_filterable',
            'usage_count', 'created_at'
        ]

class ProductAttributeValueSerializer(serializers.ModelSerializer):
    attribute_name = serializers.CharField(source='attribute.attribute_type.name_fa', read_only=True)
    attribute_type = serializers.CharField(source='attribute.attribute_type.display_type', read_only=True)
    display_value = serializers.ReadOnlyField()
    
    class Meta:
        model = ProductAttributeValue
        fields = [
            'id', 'attribute', 'attribute_name', 'attribute_type',
            'value_text', 'value_number', 'value_boolean', 'value_json',
            'color_hex', 'color_image', 'value_image', 'display_value'
        ]

class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = [
            'id', 'image', 'alt_text', 'title', 'is_featured',
            'display_order', 'imported_from_social', 'social_media_url'
        ]

class ProductVariantSerializer(serializers.ModelSerializer):
    attribute_values = ProductAttributeValueSerializer(many=True, read_only=True)
    attribute_summary = serializers.ReadOnlyField(source='get_attribute_summary')
    in_stock = serializers.ReadOnlyField()
    discount_percentage = serializers.ReadOnlyField()
    images = ProductImageSerializer(many=True, read_only=True)
    
    class Meta:
        model = ProductVariant
        fields = [
            'id', 'sku', 'barcode', 'price', 'compare_price', 'cost_price',
            'stock_quantity', 'weight', 'dimensions', 'image', 'is_active',
            'is_default', 'attribute_values', 'attribute_summary', 'in_stock',
            'discount_percentage', 'images', 'created_at', 'updated_at'
        ]

class ProductListSerializer(serializers.ModelSerializer):
    """Serializer for product list views with minimal data"""
    category_name = serializers.CharField(source='category.name_fa', read_only=True)
    brand_name = serializers.CharField(source='brand.name_fa', read_only=True)
    price_range = serializers.ReadOnlyField(source='get_price_range')
    discount_percentage = serializers.ReadOnlyField()
    in_stock = serializers.ReadOnlyField()
    featured_image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'name_fa', 'slug', 'short_description',
            'category_name', 'brand_name', 'product_type', 'base_price',
            'compare_price', 'price_range', 'discount_percentage', 'sku',
            'stock_quantity', 'featured_image_url', 'is_featured',
            'in_stock', 'status', 'view_count', 'sales_count',
            'rating_average', 'rating_count', 'created_at'
        ]
    
    def get_featured_image_url(self, obj):
        if obj.featured_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.featured_image.url)
        return None

class ProductDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for single product view"""
    category = ProductCategorySerializer(read_only=True)
    brand = BrandSerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    variants = ProductVariantSerializer(many=True, read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    attribute_values = ProductAttributeValueSerializer(many=True, read_only=True)
    available_attributes = serializers.SerializerMethodField()
    price_range = serializers.ReadOnlyField(source='get_price_range')
    discount_percentage = serializers.ReadOnlyField()
    in_stock = serializers.ReadOnlyField()
    related_products = ProductListSerializer(many=True, read_only=True)
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'name_fa', 'slug', 'description', 'short_description',
            'category', 'brand', 'product_type', 'base_price', 'compare_price',
            'cost_price', 'sku', 'stock_quantity', 'manage_stock',
            'low_stock_threshold', 'digital_file', 'download_limit',
            'download_expiry_days', 'weight', 'dimensions', 'featured_image',
            'meta_title', 'meta_description', 'meta_keywords', 'status',
            'is_featured', 'is_digital', 'tags', 'variants', 'images',
            'attribute_values', 'available_attributes', 'price_range',
            'discount_percentage', 'in_stock', 'related_products',
            'view_count', 'sales_count', 'rating_average', 'rating_count',
            'imported_from_social', 'social_media_source', 'social_media_post_id',
            'created_at', 'updated_at', 'published_at'
        ]
    
    def get_available_attributes(self, obj):
        """Get all available attributes for this product from category hierarchy"""
        return ProductAttributeSerializer(obj.get_available_attributes(), many=True).data

class ProductCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating products"""
    attribute_values = ProductAttributeValueSerializer(many=True, required=False)
    variants_data = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        write_only=True,
        help_text="List of variant data for variable products"
    )
    create_another = serializers.BooleanField(default=False, write_only=True)
    
    class Meta:
        model = Product
        fields = [
            'name', 'name_fa', 'slug', 'description', 'short_description',
            'category', 'brand', 'product_type', 'base_price', 'compare_price',
            'cost_price', 'sku', 'stock_quantity', 'manage_stock',
            'low_stock_threshold', 'digital_file', 'download_limit',
            'download_expiry_days', 'weight', 'dimensions', 'featured_image',
            'meta_title', 'meta_description', 'meta_keywords', 'status',
            'is_featured', 'is_digital', 'tags', 'attribute_values',
            'variants_data', 'create_another'
        ]
    
    def validate_category(self, value):
        """Validate that category is a leaf node"""
        if not value.is_leaf:
            raise serializers.ValidationError("فقط دسته‌بندی‌های پایانی می‌توانند محصول داشته باشند")
        return value
    
    def validate_variants_data(self, value):
        """Validate variants data for variable products"""
        if self.initial_data.get('product_type') == 'variable' and not value:
            raise serializers.ValidationError("محصولات متغیر باید حداقل یک نوع داشته باشند")
        return value
    
    def create(self, validated_data):
        """Create product with variants and attribute values"""
        attribute_values_data = validated_data.pop('attribute_values', [])
        variants_data = validated_data.pop('variants_data', [])
        create_another = validated_data.pop('create_another', False)
        tags_data = validated_data.pop('tags', [])
        
        # Create product
        product = Product.objects.create(**validated_data)
        
        # Add tags
        if tags_data:
            product.tags.set(tags_data)
        
        # Create attribute values
        for attr_value_data in attribute_values_data:
            ProductAttributeValue.objects.create(
                product=product,
                **attr_value_data
            )
        
        # Create variants if this is a variable product
        if product.product_type == 'variable' and variants_data:
            self.create_variants(product, variants_data)
        
        return product
    
    def create_variants(self, product, variants_data):
        """Create product variants"""
        for variant_data in variants_data:
            # Extract attribute values for this variant
            variant_attributes = variant_data.pop('attributes', {})
            
            # Create variant
            variant = ProductVariant.objects.create(
                product=product,
                **variant_data
            )
            
            # Create attribute values for variant
            for attr_name, attr_value in variant_attributes.items():
                try:
                    attribute = ProductAttribute.objects.get(
                        category=product.category,
                        attribute_type__name=attr_name
                    )
                    
                    ProductAttributeValue.objects.create(
                        variant=variant,
                        attribute=attribute,
                        value_text=str(attr_value)
                    )
                except ProductAttribute.DoesNotExist:
                    continue

class BulkProductCreateSerializer(serializers.Serializer):
    """Serializer for bulk product creation"""
    products = ProductCreateSerializer(many=True)
    
    def create(self, validated_data):
        """Create multiple products in bulk"""
        products_data = validated_data['products']
        created_products = []
        
        for product_data in products_data:
            # Use ProductCreateSerializer to create each product
            serializer = ProductCreateSerializer(data=product_data)
            serializer.is_valid(raise_exception=True)
            product = serializer.save()
            created_products.append(product)
        
        return created_products

class ProductVariantCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating product variants"""
    attribute_values = ProductAttributeValueSerializer(many=True, required=False)
    
    class Meta:
        model = ProductVariant
        fields = [
            'price', 'compare_price', 'cost_price', 'stock_quantity',
            'weight', 'dimensions', 'image', 'is_active', 'is_default',
            'attribute_values'
        ]
    
    def create(self, validated_data):
        """Create variant with attribute values"""
        attribute_values_data = validated_data.pop('attribute_values', [])
        variant = ProductVariant.objects.create(**validated_data)
        
        # Create attribute values
        for attr_value_data in attribute_values_data:
            ProductAttributeValue.objects.create(
                variant=variant,
                **attr_value_data
            )
        
        return variant

class ProductImportSerializer(serializers.Serializer):
    """Serializer for importing products from social media"""
    social_media_post_id = serializers.CharField()
    category_id = serializers.UUIDField()
    additional_data = serializers.DictField(required=False)
    
    def validate_social_media_post_id(self, value):
        """Validate that the social media post exists"""
        from apps.social_media.models import SocialMediaPost
        try:
            post = SocialMediaPost.objects.get(
                id=value,
                status='imported'
            )
            self.post = post
            return value
        except SocialMediaPost.DoesNotExist:
            raise serializers.ValidationError("پست شبکه اجتماعی یافت نشد")
    
    def validate_category_id(self, value):
        """Validate category exists and is leaf"""
        try:
            category = ProductCategory.objects.get(id=value)
            if not category.is_leaf:
                raise serializers.ValidationError("دسته‌بندی باید پایانی باشد")
            self.category = category
            return value
        except ProductCategory.DoesNotExist:
            raise serializers.ValidationError("دسته‌بندی یافت نشد")
    
    def create(self, validated_data):
        """Convert social media post to product"""
        additional_data = validated_data.get('additional_data', {})
        return self.post.convert_to_product(self.category, additional_data)

class CollectionSerializer(serializers.ModelSerializer):
    products_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Collection
        fields = [
            'id', 'name', 'name_fa', 'slug', 'description', 'collection_type',
            'auto_rules', 'featured_image', 'is_featured', 'display_order',
            'is_active', 'products', 'meta_title', 'meta_description',
            'products_count', 'created_at', 'updated_at'
        ]
    
    def get_products_count(self, obj):
        """Get count of products in collection"""
        return obj.get_products().count()

class ProductSearchSerializer(serializers.Serializer):
    """Serializer for product search parameters"""
    query = serializers.CharField(required=False, allow_blank=True)
    category_id = serializers.UUIDField(required=False)
    brand_id = serializers.UUIDField(required=False)
    tags = serializers.ListField(
        child=serializers.CharField(),
        required=False
    )
    min_price = serializers.DecimalField(max_digits=12, decimal_places=0, required=False)
    max_price = serializers.DecimalField(max_digits=12, decimal_places=0, required=False)
    in_stock = serializers.BooleanField(required=False)
    is_featured = serializers.BooleanField(required=False)
    status = serializers.ChoiceField(choices=Product.STATUS_CHOICES, required=False)
    sort_by = serializers.ChoiceField(
        choices=[
            'created_at', '-created_at',
            'price', '-price',
            'name_fa', '-name_fa',
            'view_count', '-view_count',
            'sales_count', '-sales_count',
            'rating_average', '-rating_average'
        ],
        default='-created_at',
        required=False
    )
    
    # Attribute filters (dynamic based on category)
    attributes = serializers.DictField(required=False)

class ProductStatisticsSerializer(serializers.Serializer):
    """Serializer for product statistics"""
    total_products = serializers.IntegerField()
    published_products = serializers.IntegerField()
    draft_products = serializers.IntegerField()
    out_of_stock_products = serializers.IntegerField()
    low_stock_products = serializers.IntegerField()
    featured_products = serializers.IntegerField()
    total_variants = serializers.IntegerField()
    total_categories = serializers.IntegerField()
    total_brands = serializers.IntegerField()
    avg_price = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_views = serializers.IntegerField()
    total_sales = serializers.IntegerField()
