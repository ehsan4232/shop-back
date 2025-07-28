"""
Store Serializers
"""
from rest_framework import serializers
from .models import Store, StoreTheme, StoreSettings, StoreAnalytics


class StoreSerializer(serializers.ModelSerializer):
    """Basic store serializer"""
    full_domain = serializers.ReadOnlyField()
    url = serializers.ReadOnlyField()
    
    class Meta:
        model = Store
        fields = [
            'id', 'name', 'name_fa', 'slug', 'description', 'description_fa',
            'logo', 'banner', 'subdomain', 'domain', 'full_domain', 'url',
            'phone', 'email', 'city', 'state', 'currency', 'is_active',
            'is_verified', 'is_premium', 'total_orders', 'total_revenue',
            'view_count', 'created_at'
        ]
        read_only_fields = [
            'id', 'total_orders', 'total_revenue', 'view_count', 'created_at'
        ]


class StoreDetailSerializer(StoreSerializer):
    """Detailed store serializer with theme and settings"""
    theme = serializers.SerializerMethodField()
    settings = serializers.SerializerMethodField()
    
    class Meta(StoreSerializer.Meta):
        fields = StoreSerializer.Meta.fields + ['theme', 'settings']
    
    def get_theme(self, obj):
        try:
            return StoreThemeSerializer(obj.theme).data
        except AttributeError:
            return None
    
    def get_settings(self, obj):
        try:
            return StoreSettingsSerializer(obj.settings).data
        except AttributeError:
            return None


class StoreCreateSerializer(serializers.ModelSerializer):
    """Store creation serializer"""
    
    class Meta:
        model = Store
        fields = [
            'name', 'name_fa', 'slug', 'description', 'description_fa',
            'subdomain', 'phone', 'email', 'city', 'state'
        ]
    
    def validate_subdomain(self, value):
        """Validate subdomain uniqueness and format"""
        import re
        
        if not re.match(r'^[a-zA-Z0-9]([a-zA-Z0-9-]{0,48}[a-zA-Z0-9])?$', value):
            raise serializers.ValidationError('فرمت زیردامنه نامعتبر است')
        
        reserved = ['www', 'api', 'admin', 'mail', 'ftp', 'blog']
        if value.lower() in reserved:
            raise serializers.ValidationError('این زیردامنه رزرو شده است')
        
        if Store.objects.filter(subdomain=value).exists():
            raise serializers.ValidationError('این زیردامنه قبلاً استفاده شده است')
        
        return value.lower()
    
    def validate_slug(self, value):
        """Validate slug uniqueness"""
        if Store.objects.filter(slug=value).exists():
            raise serializers.ValidationError('این نامک قبلاً استفاده شده است')
        return value


class StoreThemeSerializer(serializers.ModelSerializer):
    """Store theme serializer"""
    
    class Meta:
        model = StoreTheme
        fields = [
            'id', 'name', 'primary_color', 'secondary_color', 'accent_color',
            'background_color', 'text_color', 'font_family', 'font_size_base',
            'layout', 'header_style', 'footer_style', 'products_per_page',
            'product_card_style', 'show_product_badges', 'custom_css',
            'homepage_banner'
        ]
    
    def validate_primary_color(self, value):
        """Validate hex color format"""
        import re
        if not re.match(r'^#[0-9A-Fa-f]{6}$', value):
            raise serializers.ValidationError('فرمت رنگ نامعتبر است (مثال: #FF0000)')
        return value
    
    def validate_secondary_color(self, value):
        """Validate hex color format"""
        import re
        if not re.match(r'^#[0-9A-Fa-f]{6}$', value):
            raise serializers.ValidationError('فرمت رنگ نامعتبر است')
        return value
    
    def validate_accent_color(self, value):
        """Validate hex color format"""
        import re
        if not re.match(r'^#[0-9A-Fa-f]{6}$', value):
            raise serializers.ValidationError('فرمت رنگ نامعتبر است')
        return value


class StoreSettingsSerializer(serializers.ModelSerializer):
    """Store settings serializer"""
    
    class Meta:
        model = StoreSettings
        fields = [
            'id', 'meta_title', 'meta_description', 'meta_keywords',
            'google_analytics_id', 'google_tag_manager_id', 'facebook_pixel_id',
            'zarinpal_merchant_id', 'parsian_pin', 'mellat_terminal_id',
            'sms_provider', 'sms_api_key', 'sms_sender_number',
            'sms_welcome_template', 'sms_order_confirmation_template',
            'sms_shipping_template', 'logistics_provider', 'logistics_api_key',
            'return_policy', 'privacy_policy', 'terms_of_service',
            'shipping_policy', 'working_hours', 'enable_chat', 'enable_reviews',
            'enable_wishlist', 'enable_compare', 'enable_social_login',
            'low_stock_threshold', 'auto_reduce_stock', 'allow_backorders'
        ]
        extra_kwargs = {
            'sms_api_key': {'write_only': True},
            'zarinpal_merchant_id': {'write_only': True},
            'parsian_pin': {'write_only': True},
            'mellat_terminal_id': {'write_only': True},
            'logistics_api_key': {'write_only': True},
        }


class StoreAnalyticsSerializer(serializers.ModelSerializer):
    """Store analytics serializer"""
    
    class Meta:
        model = StoreAnalytics
        fields = [
            'date', 'visitors', 'page_views', 'unique_visitors', 'bounce_rate',
            'orders_count', 'revenue', 'conversion_rate', 'average_order_value',
            'products_viewed', 'cart_additions', 'cart_abandonment_rate'
        ]


class StoreStatsSerializer(serializers.Serializer):
    """Store statistics serializer"""
    total_products = serializers.IntegerField()
    total_categories = serializers.IntegerField()
    total_brands = serializers.IntegerField()
    total_orders = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=15, decimal_places=0)
    monthly_revenue = serializers.DecimalField(max_digits=15, decimal_places=0)
    featured_products_count = serializers.IntegerField()
    out_of_stock_count = serializers.IntegerField()
    recent_orders_count = serializers.IntegerField()
    total_views = serializers.IntegerField()
    conversion_rate = serializers.FloatField()


class DomainValidationSerializer(serializers.Serializer):
    """Domain validation serializer"""
    domain = serializers.CharField(max_length=255)
    
    def validate_domain(self, value):
        """Validate domain format"""
        import re
        pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$'
        if not re.match(pattern, value):
            raise serializers.ValidationError('فرمت دامنه نامعتبر است')
        return value.lower()


class SubdomainValidationSerializer(serializers.Serializer):
    """Subdomain validation serializer"""
    subdomain = serializers.CharField(max_length=50)
    
    def validate_subdomain(self, value):
        """Validate subdomain format"""
        import re
        if not re.match(r'^[a-zA-Z0-9]([a-zA-Z0-9-]{0,48}[a-zA-Z0-9])?$', value):
            raise serializers.ValidationError('فرمت زیردامنه نامعتبر است')
        return value.lower()
