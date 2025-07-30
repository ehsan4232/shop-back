from rest_framework import serializers
from .models import SocialMediaAccount, SocialMediaPost, SocialMediaImportJob

class SocialMediaAccountSerializer(serializers.ModelSerializer):
    """Social media account management"""
    platform_display = serializers.CharField(source='get_platform_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_token_valid = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = SocialMediaAccount
        fields = [
            'id', 'platform', 'platform_display', 'username', 'display_name',
            'account_id', 'status', 'status_display', 'is_auto_import',
            'last_import', 'import_settings', 'is_token_valid',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'account_id', 'last_import', 'created_at', 'updated_at'
        ]

class SocialMediaAccountCreateSerializer(serializers.ModelSerializer):
    """Create social media account connection"""
    class Meta:
        model = SocialMediaAccount
        fields = [
            'platform', 'username', 'access_token', 'import_settings'
        ]
    
    def create(self, validated_data):
        validated_data['store'] = self.context['request'].user.store
        return super().create(validated_data)

class SocialMediaPostSerializer(serializers.ModelSerializer):
    """Social media post display"""
    account_username = serializers.CharField(source='account.username', read_only=True)
    platform = serializers.CharField(source='account.platform', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    post_type_display = serializers.CharField(source='get_post_type_display', read_only=True)
    
    class Meta:
        model = SocialMediaPost
        fields = [
            'id', 'platform_post_id', 'content', 'post_type', 'post_type_display',
            'media_url', 'thumbnail_url', 'local_media', 'permalink',
            'posted_at', 'status', 'status_display', 'created_product',
            'account_username', 'platform', 'extracted_text',
            'detected_products', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'platform_post_id', 'extracted_text', 'detected_products',
            'created_at', 'updated_at'
        ]

class ProductConversionSerializer(serializers.Serializer):
    """Convert social media post to product"""
    post_id = serializers.UUIDField()
    category_id = serializers.UUIDField()
    product_class_id = serializers.UUIDField()
    name = serializers.CharField(max_length=200, required=False)
    price = serializers.DecimalField(max_digits=12, decimal_places=0, required=False)
    description = serializers.CharField(required=False)
    
    def validate_post_id(self, value):
        try:
            post = SocialMediaPost.objects.get(id=value)
            if post.status == 'converted':
                raise serializers.ValidationError("این پست قبلاً به محصول تبدیل شده است")
            self.post = post
            return value
        except SocialMediaPost.DoesNotExist:
            raise serializers.ValidationError("پست یافت نشد")
    
    def validate_category_id(self, value):
        from apps.products.models import ProductCategory
        try:
            category = ProductCategory.objects.get(id=value)
            self.category = category
            return value
        except ProductCategory.DoesNotExist:
            raise serializers.ValidationError("دسته‌بندی یافت نشد")
    
    def validate_product_class_id(self, value):
        from apps.products.models import ProductClass
        try:
            product_class = ProductClass.objects.get(id=value)
            if not product_class.is_leaf:
                raise serializers.ValidationError("کلاس محصول باید پایانی باشد")
            self.product_class = product_class
            return value
        except ProductClass.DoesNotExist:
            raise serializers.ValidationError("کلاس محصول یافت نشد")
    
    def create(self, validated_data):
        # Extract additional data for product creation
        additional_data = {
            'product_class': self.product_class,
            'name': validated_data.get('name'),
            'base_price': validated_data.get('price'),
            'description': validated_data.get('description'),
        }
        
        # Convert post to product
        product = self.post.convert_to_product(
            category=self.category,
            additional_data=additional_data
        )
        
        return product

class SocialMediaImportJobSerializer(serializers.ModelSerializer):
    """Import job management"""
    account_username = serializers.CharField(source='account.username', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    job_type_display = serializers.CharField(source='get_job_type_display', read_only=True)
    
    class Meta:
        model = SocialMediaImportJob
        fields = [
            'id', 'job_type', 'job_type_display', 'status', 'status_display',
            'limit', 'filters', 'total_posts', 'imported_posts',
            'error_message', 'account_username', 'created_at',
            'started_at', 'completed_at'
        ]
        read_only_fields = [
            'id', 'status', 'total_posts', 'imported_posts', 'error_message',
            'started_at', 'completed_at'
        ]

class BulkImportSerializer(serializers.Serializer):
    """Bulk import from social media"""
    account_id = serializers.UUIDField()
    limit = serializers.IntegerField(min_value=1, max_value=50, default=10)
    filters = serializers.DictField(required=False)
    
    def validate_account_id(self, value):
        try:
            account = SocialMediaAccount.objects.get(id=value)
            if account.status != 'active':
                raise serializers.ValidationError("اکانت فعال نیست")
            self.account = account
            return value
        except SocialMediaAccount.DoesNotExist:
            raise serializers.ValidationError("اکانت یافت نشد")

class SocialMediaPostCreateSerializer(serializers.ModelSerializer):
    """Create social media post manually"""
    class Meta:
        model = SocialMediaPost
        fields = [
            'content', 'post_type', 'media_url', 'permalink'
        ]
    
    def create(self, validated_data):
        # Auto-assign account and other fields
        account = self.context.get('account')
        validated_data['account'] = account
        validated_data['platform_post_id'] = f"manual_{timezone.now().timestamp()}"
        validated_data['posted_at'] = timezone.now()
        return super().create(validated_data)

class SocialMediaAnalyticsSerializer(serializers.Serializer):
    """Analytics for social media performance"""
    total_accounts = serializers.IntegerField()
    active_accounts = serializers.IntegerField()
    total_posts = serializers.IntegerField()
    converted_posts = serializers.IntegerField()
    conversion_rate = serializers.FloatField()
    platforms = serializers.DictField()
    recent_imports = serializers.ListField()
