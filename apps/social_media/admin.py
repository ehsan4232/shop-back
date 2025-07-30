from django.contrib import admin
from .models import SocialMediaAccount, SocialMediaPost

@admin.register(SocialMediaAccount)
class SocialMediaAccountAdmin(admin.ModelAdmin):
    list_display = ['username', 'platform', 'store', 'is_active', 'last_sync_at']
    list_filter = ['platform', 'is_active', 'created_at']
    search_fields = ['username', 'account_id']
    readonly_fields = ['created_at', 'updated_at', 'last_sync_at']

@admin.register(SocialMediaPost)
class SocialMediaPostAdmin(admin.ModelAdmin):
    list_display = ['external_id', 'account', 'published_at', 'is_processed']
    list_filter = ['account__platform', 'is_processed', 'published_at']
    search_fields = ['external_id', 'content']
    readonly_fields = ['created_at', 'updated_at']
