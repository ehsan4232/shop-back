from rest_framework import serializers
from .models import ProductCategory, ProductAttribute, Product, ProductInstance, ProductInstanceAttribute

class ProductAttributeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductAttribute
        fields = '__all__'

class ProductCategorySerializer(serializers.ModelSerializer):
    attributes = ProductAttributeSerializer(many=True, read_only=True)
    is_leaf = serializers.ReadOnlyField()
    
    class Meta:
        model = ProductCategory
        fields = '__all__'

class ProductInstanceAttributeSerializer(serializers.ModelSerializer):
    attribute = ProductAttributeSerializer(read_only=True)
    
    class Meta:
        model = ProductInstanceAttribute
        fields = '__all__'

class ProductInstanceSerializer(serializers.ModelSerializer):
    attributes = ProductInstanceAttributeSerializer(many=True, read_only=True)
    final_price = serializers.ReadOnlyField()
    is_low_stock = serializers.ReadOnlyField()
    
    class Meta:
        model = ProductInstance
        fields = '__all__'

class ProductSerializer(serializers.ModelSerializer):
    instances = ProductInstanceSerializer(many=True, read_only=True)
    category = ProductCategorySerializer(read_only=True)
    
    class Meta:
        model = Product
        fields = '__all__'