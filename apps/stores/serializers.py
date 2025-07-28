from rest_framework import serializers
from .models import Store, StoreTheme, StoreSettings, StoreAnalytics

class StoreThemeSerializer(serializers.ModelSerializer):
    class Meta:
        model = StoreTheme
        fields = [
            'id', 'name', 'primary_color', 'secondary_color', 'accent_color',
            'background_color', 'text_color', 'font_family', 'font_size_base',
            'layout', 'header_style', 'footer_style', 'products_per_page',
            'product_card_style', 'show_product_badges', 'custom_css',
            'homepage_banner'
        ]

class StoreSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = StoreSettings
        fields = [
            'id', 'meta_title', 'meta_description', 'meta_keywords',
            'google_analytics_id', 'facebook_pixel_id', 'zarinpal_merchant_id',
            'parsian_pin', 'sms_provider', 'sms_api_key', 'sms_sender_number',
            'sms_welcome_template', 'sms_order_confirmation_template',
            'sms_shipping_template', 'logistics_provider', 'logistics_api_key',
            'return_policy', 'privacy_policy', 'terms_of_service',
            'working_hours', 'enable_chat', 'enable_reviews', 'enable_wishlist',
            'enable_compare', 'low_stock_threshold', 'auto_reduce_stock',
            'allow_backorders'
        ]

class StoreAnalyticsSerializer(serializers.ModelSerializer):
    class Meta:
        model = StoreAnalytics
        fields = [
            'id', 'date', 'visitors', 'page_views', 'unique_visitors',
            'bounce_rate', 'orders_count', 'revenue', 'conversion_rate',
            'average_order_value', 'products_viewed', 'cart_additions',
            'cart_abandonment_rate'
        ]

class StoreListSerializer(serializers.ModelSerializer):
    full_domain = serializers.ReadOnlyField()
    url = serializers.ReadOnlyField()
    
    class Meta:
        model = Store
        fields = [
            'id', 'name', 'name_fa', 'slug', 'description', 'description_fa',
            'logo', 'subdomain', 'domain', 'full_domain', 'url', 'currency',
            'is_active', 'is_verified', 'is_premium', 'total_orders',
            'total_revenue', 'view_count', 'created_at'
        ]

class StoreDetailSerializer(serializers.ModelSerializer):
    theme = StoreThemeSerializer(read_only=True)
    settings = StoreSettingsSerializer(read_only=True)
    full_domain = serializers.ReadOnlyField()
    url = serializers.ReadOnlyField()
    
    class Meta:
        model = Store
        fields = [
            'id', 'name', 'name_fa', 'slug', 'description', 'description_fa',
            'logo', 'banner', 'favicon', 'domain', 'subdomain', 'full_domain',
            'url', 'phone', 'email', 'address', 'city', 'state', 'postal_code',
            'instagram_username', 'telegram_username', 'telegram_channel_id',
            'currency', 'tax_rate', 'is_active', 'is_verified', 'is_premium',
            'total_orders', 'total_revenue', 'view_count', 'theme', 'settings',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'total_orders', 'total_revenue', 'view_count', 'created_at', 'updated_at']

class StoreCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Store
        fields = [
            'name', 'name_fa', 'slug', 'description', 'description_fa',
            'logo', 'banner', 'favicon', 'subdomain', 'domain', 'phone',
            'email', 'address', 'city', 'state', 'postal_code',
            'instagram_username', 'telegram_username', 'telegram_channel_id',
            'currency', 'tax_rate'
        ]
    
    def validate_subdomain(self, value):
        """Ensure subdomain uniqueness"""
        qs = Store.objects.filter(subdomain=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('این زیردامنه قبلاً استفاده شده است.')
        return value
    
    def validate_domain(self, value):
        """Ensure domain uniqueness"""
        if value:
            qs = Store.objects.filter(domain=value)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError('این دامنه قبلاً استفاده شده است.')
        return value

class StoreStatsSerializer(serializers.Serializer):
    """Serializer for store statistics summary"""
    total_products = serializers.IntegerField()
    total_orders = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=15, decimal_places=0)
    total_customers = serializers.IntegerField()
    monthly_revenue = serializers.DecimalField(max_digits=15, decimal_places=0)
    monthly_orders = serializers.IntegerField()
    conversion_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    average_order_value = serializers.DecimalField(max_digits=12, decimal_places=0)
