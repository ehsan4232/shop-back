from rest_framework import serializers
from .models import Store, StoreSettings

class StoreSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = StoreSettings
        fields = '__all__'

class StoreSerializer(serializers.ModelSerializer):
    settings = StoreSettingsSerializer(read_only=True)
    full_domain = serializers.ReadOnlyField()
    
    class Meta:
        model = Store
        fields = ['id', 'name', 'name_fa', 'description', 'description_fa', 'logo', 'banner',
                 'theme', 'layout', 'domain', 'subdomain', 'full_domain', 'currency',
                 'phone_number', 'email', 'address', 'instagram_username', 'telegram_username',
                 'is_active', 'created_at', 'updated_at', 'settings']
        read_only_fields = ['id', 'created_at', 'updated_at']