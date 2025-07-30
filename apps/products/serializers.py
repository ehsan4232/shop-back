from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator
from django.db.models import Sum
from .models import (
    AttributeType, Tag, ProductClass, ProductClassAttribute,
    ProductCategory, ProductAttribute, Brand,
    Product, ProductVariant, ProductAttributeValue, ProductImage, Collection
)

class AttributeTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttributeType
        fields = '__all__'

class TagSerializer(serializers.ModelSerializer):
    usage_count = serializers.ReadOnlyField()
    
    class Meta:
        model = Tag
        fields = [
            'id', 'name', 'name_fa', 'slug', 'description', 'tag_type', 
            'color', 'is_featured', 'is_filterable', 'usage_count', 'created_at'
        ]

class ProductClassAttributeSerializer(serializers.ModelSerializer):
    attribute_type = AttributeTypeSerializer(read_only=True)
    
    class Meta:
        model = ProductClassAttribute
        fields = [
            'id', 'attribute_type', 'default_value', 'is_required', 
            'is_inherited', 'display_order'
        ]

class ProductClassSerializer(serializers.ModelSerializer):
    attributes = ProductClassAttributeSerializer(many=True, read_only=True)
    children = serializers.SerializerMethodField()
    parent_name = serializers.CharField(source='parent.name_fa', read_only=True)
    inherited_attributes = serializers.SerializerMethodField()
    effective_price = serializers.ReadOnlyField(source='get_effective_price')
    
    class Meta:
        model = ProductClass
        fields = [
            'id', 'name', 'name_fa', 'slug', 'description', 'parent', 'parent_name',
            'base_price', 'icon', 'image', 'display_order', 'is_active', 'is_leaf',
            'product_count', 'attributes', 'children', 'inherited_attributes',
            'effective_price', 'created_at', 'updated_at'
        ]
        read_only_fields = ['is_leaf', 'product_count']
    
    def get_children(self, obj):
        """Get immediate children classes"""
        children = obj.get_children().filter(is_active=True)
        return ProductClassSerializer(children, many=True, context=self.context).data
    
    def get_inherited_attributes(self, obj):
        """Get all inherited attributes from ancestors"""
        return ProductClassAttributeSerializer(obj.get_inherited_attributes(), many=True).data

class ProductAttributeSerializer(serializers.ModelSerializer):
    attribute_type = AttributeTypeSerializer(read_only=True)
    attribute_type_id = serializers.UUIDField(write_only=True)
    
    class Meta:
        model = ProductAttribute
        fields = [
            'id', 'attribute_type', 'attribute_type_id', 'is_required',
            'default_value', 'display_order'
        ]

class ProductCategorySerializer(serializers.ModelSerializer):
    attributes = ProductAttributeSerializer(many=True, read_only=True)
    children = serializers.SerializerMethodField()
    parent_name = serializers.CharField(source='parent.name_fa', read_only=True)
    
    class Meta:
        model = ProductCategory
        fields = [
            'id', 'name', 'name_fa', 'slug', 'description', 'parent', 'parent_name',
            'icon', 'image', 'display_order', 'is_active', 'product_count',
            'attributes', 'children', 'created_at', 'updated_at'
        ]
        read_only_fields = ['product_count']
    
    def get_children(self, obj):
        """Get immediate children categories"""
        children = obj.get_children().filter(is_active=True)
        return ProductCategorySerializer(children, many=True, context=self.context).data

class BrandSerializer(serializers.ModelSerializer):
    product_count = serializers.ReadOnlyField()
    
    class Meta:
        model = Brand
        fields = [
            'id', 'name', 'name_fa', 'slug', 'logo', 'description',
            'is_active', 'product_count', 'created_at', 'updated_at'
        ]

class ProductAttributeValueSerializer(serializers.ModelSerializer):
    attribute_name = serializers.CharField(source='attribute.attribute_type.name_fa', read_only=True)
    attribute_type = serializers.CharField(source='attribute.attribute_type.data_type', read_only=True)
    display_value = serializers.SerializerMethodField()
    
    class Meta:
        model = ProductAttributeValue
        fields = [
            'id', 'attribute', 'attribute_name', 'attribute_type',
            'value_text', 'value_number', 'value_boolean', 'value_date',
            'display_value'
        ]
    
    def get_display_value(self, obj):
        """Get display value based on attribute type"""
        return obj.get_value()

class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = [
            'id', 'image', 'alt_text', 'is_featured', 'display_order',
            'imported_from_social', 'social_media_url'
        ]

class ProductVariantSerializer(serializers.ModelSerializer):
    attribute_values = ProductAttributeValueSerializer(many=True, read_only=True)
    attribute_summary = serializers.SerializerMethodField()
    in_stock = serializers.ReadOnlyField()
    discount_percentage = serializers.ReadOnlyField()
    images = ProductImageSerializer(many=True, read_only=True)
    
    class Meta:
        model = ProductVariant
        fields = [
            'id', 'sku', 'price', 'compare_price', 'stock_quantity',
            'image', 'is_active', 'is_default', 'attribute_values',
            'attribute_summary', 'in_stock', 'discount_percentage', 'images',
            'created_at', 'updated_at'
        ]
    
    def get_attribute_summary(self, obj):
        """Get a summary of variant attributes"""
        return ", ".join([
            f"{val.attribute.attribute_type.name_fa}: {val.get_value()}"
            for val in obj.attribute_values.all()
        ])

class ProductListSerializer(serializers.ModelSerializer):
    """Serializer for product list views with minimal data"""
    category_name = serializers.CharField(source='category.name_fa', read_only=True)
    brand_name = serializers.CharField(source='brand.name_fa', read_only=True)
    product_class_name = serializers.CharField(source='product_class.name_fa', read_only=True)
    effective_price = serializers.ReadOnlyField(source='get_effective_price')
    discount_percentage = serializers.ReadOnlyField()
    in_stock = serializers.ReadOnlyField()
    featured_image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'name_fa', 'slug', 'short_description',
            'category_name', 'brand_name', 'product_class_name', 
            'product_type', 'base_price', 'effective_price', 'compare_price',
            'discount_percentage', 'sku', 'stock_quantity', 'featured_image_url',
            'is_featured', 'in_stock', 'status', 'view_count', 'sales_count',
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
    product_class = ProductClassSerializer(read_only=True)
    category = ProductCategorySerializer(read_only=True)
    brand = BrandSerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    variants = ProductVariantSerializer(many=True, read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    attribute_values = ProductAttributeValueSerializer(many=True, read_only=True)
    inherited_attributes = serializers.SerializerMethodField()
    effective_price = serializers.ReadOnlyField(source='get_effective_price')
    discount_percentage = serializers.ReadOnlyField()
    in_stock = serializers.ReadOnlyField()
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'name_fa', 'slug', 'description', 'short_description',
            'product_class', 'category', 'brand', 'product_type', 'base_price',
            'effective_price', 'compare_price', 'cost_price', 'sku', 'stock_quantity',
            'manage_stock', 'low_stock_threshold', 'weight', 'featured_image',
            'meta_title', 'meta_description', 'status', 'is_featured', 'tags',
            'variants', 'images', 'attribute_values', 'inherited_attributes',
            'discount_percentage', 'in_stock', 'view_count', 'sales_count',
            'rating_average', 'rating_count', 'imported_from_social',
            'social_media_source', 'social_media_post_id', 'created_at',
            'updated_at', 'published_at'
        ]
    
    def get_inherited_attributes(self, obj):
        """Get all inherited attributes from product class"""
        return ProductClassAttributeSerializer(obj.get_inherited_attributes(), many=True).data

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
            'product_class', 'category', 'brand', 'product_type', 'base_price',
            'compare_price', 'cost_price', 'sku', 'stock_quantity', 'manage_stock',
            'low_stock_threshold', 'weight', 'featured_image', 'meta_title',
            'meta_description', 'status', 'is_featured', 'tags',
            'attribute_values', 'variants_data', 'create_another'
        ]
    
    def validate_product_class(self, value):
        """Validate that product class is a leaf node"""
        if not value.is_leaf:
            raise serializers.ValidationError("فقط کلاس‌های پایانی می‌توانند محصول داشته باشند")
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
            'price', 'compare_price', 'stock_quantity', 'image',
            'is_active', 'is_default', 'attribute_values'
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
    product_class_id = serializers.UUIDField()
    category_id = serializers.UUIDField()
    additional_data = serializers.DictField(required=False)
    
    def validate_social_media_post_id(self, value):
        """Validate that the social media post exists"""
        # This would integrate with social media app when implemented
        return value
    
    def validate_product_class_id(self, value):
        """Validate product class exists and is leaf"""
        try:
            product_class = ProductClass.objects.get(id=value)
            if not product_class.is_leaf:
                raise serializers.ValidationError("کلاس محصول باید پایانی باشد")
            self.product_class = product_class
            return value
        except ProductClass.DoesNotExist:
            raise serializers.ValidationError("کلاس محصول یافت نشد")
    
    def validate_category_id(self, value):
        """Validate category exists"""
        try:
            category = ProductCategory.objects.get(id=value)
            self.category = category
            return value
        except ProductCategory.DoesNotExist:
            raise serializers.ValidationError("دسته‌بندی یافت نشد")
    
    def create(self, validated_data):
        """Convert social media post to product"""
        additional_data = validated_data.get('additional_data', {})
        # Implementation would depend on social media integration
        # For now, create a basic product
        return Product.objects.create(
            name=f"Product from social media",
            name_fa=f"محصول از شبکه اجتماعی",
            product_class=self.product_class,
            category=self.category,
            imported_from_social=True,
            social_media_post_id=validated_data['social_media_post_id'],
            **additional_data
        )

class CollectionSerializer(serializers.ModelSerializer):
    products_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Collection
        fields = [
            'id', 'name', 'name_fa', 'slug', 'description',
            'featured_image', 'is_featured', 'display_order',
            'is_active', 'products', 'products_count', 
            'created_at', 'updated_at'
        ]
    
    def get_products_count(self, obj):
        """Get count of products in collection"""
        return obj.products.count()

class ProductSearchSerializer(serializers.Serializer):
    """Serializer for product search parameters"""
    query = serializers.CharField(required=False, allow_blank=True)
    product_class_id = serializers.UUIDField(required=False)
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
    total_product_classes = serializers.IntegerField()
    total_categories = serializers.IntegerField()
    total_brands = serializers.IntegerField()
    avg_price = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_views = serializers.IntegerField()
    total_sales = serializers.IntegerField()
