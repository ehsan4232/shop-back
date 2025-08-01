from rest_framework import serializers
from .models import ThemeCategory, Theme, StoreTheme, ThemeRating


class ThemeCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ThemeCategory
        fields = [
            'id', 'name', 'name_fa', 'category_type', 'description', 
            'icon', 'display_order'
        ]


class ThemeSerializer(serializers.ModelSerializer):
    category = ThemeCategorySerializer(read_only=True)
    rating_display = serializers.SerializerMethodField()
    
    class Meta:
        model = Theme
        fields = [
            'id', 'name', 'name_fa', 'description', 'version',
            'category', 'theme_type', 'compatibility', 'preview_image',
            'demo_url', 'price', 'is_featured', 'download_count',
            'usage_count', 'rating_average', 'rating_count', 'rating_display'
        ]
    
    def get_rating_display(self, obj):
        return {
            'average': float(obj.rating_average),
            'count': obj.rating_count,
            'stars': int(obj.rating_average) if obj.rating_count > 0 else 0
        }


class ThemeDetailSerializer(ThemeSerializer):
    customization_options = serializers.SerializerMethodField()
    
    class Meta(ThemeSerializer.Meta):
        fields = ThemeSerializer.Meta.fields + [
            'customizable_colors', 'customizable_fonts', 'layout_options',
            'customization_options'
        ]
    
    def get_customization_options(self, obj):
        return obj.get_customization_options()


class StoreThemeSerializer(serializers.ModelSerializer):
    theme = ThemeSerializer(read_only=True)
    compiled_config = serializers.SerializerMethodField()
    
    class Meta:
        model = StoreTheme
        fields = [
            'id', 'theme', 'custom_colors', 'layout_config',
            'font_selections', 'is_active', 'applied_at', 'compiled_config'
        ]
    
    def get_compiled_config(self, obj):
        return obj.get_compiled_config()


class StoreThemeCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = StoreTheme
        fields = [
            'theme', 'custom_colors', 'custom_css', 'custom_js',
            'layout_config', 'font_selections'
        ]
    
    def create(self, validated_data):
        # Automatically set store from request context
        store = self.context['request'].user.store
        validated_data['store'] = store
        
        # Deactivate previous themes
        StoreTheme.objects.filter(store=store, is_active=True).update(is_active=False)
        
        # Create new active theme
        return super().create(validated_data)


class ThemeRatingSerializer(serializers.ModelSerializer):
    store_name = serializers.CharField(source='store.name', read_only=True)
    
    class Meta:
        model = ThemeRating
        fields = ['id', 'rating', 'review', 'store_name', 'created_at']
        read_only_fields = ['store_name', 'created_at']


class ThemeRatingCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ThemeRating
        fields = ['theme', 'rating', 'review']
    
    def create(self, validated_data):
        store = self.context['request'].user.store
        validated_data['store'] = store
        return super().create(validated_data)
