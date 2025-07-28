from django.contrib import admin
from .models import *

@admin.register(SocialMediaAccount)
class SocialMediaAccountAdmin(admin.ModelAdmin):
    list_display = ['store', 'platform', 'username', 'is_active', 'auto_import', 'last_sync']
    list_filter = ['platform', 'is_active', 'auto_import']
    search_fields = ['username', 'store__name_fa']
    readonly_fields = ['last_sync', 'created_at', 'updated_at']

@admin.register(SocialMediaPost)
class SocialMediaPostAdmin(admin.ModelAdmin):
    list_display = ['account', 'post_id', 'post_type', 'is_imported', 'posted_at', 'engagement_rate']
    list_filter = ['post_type', 'is_imported', 'account__platform']
    search_fields = ['post_id', 'caption']
    readonly_fields = ['engagement_rate', 'created_at', 'updated_at']
    date_hierarchy = 'posted_at'

@admin.register(ImportSession)
class ImportSessionAdmin(admin.ModelAdmin):
    list_display = ['account', 'status', 'posts_found', 'posts_imported', 'products_created', 'success_rate', 'created_at']
    list_filter = ['status', 'account__platform']
    readonly_fields = ['success_rate', 'duration', 'created_at', 'started_at', 'completed_at']
    date_hierarchy = 'created_at'

@admin.register(MediaDownload)
class MediaDownloadAdmin(admin.ModelAdmin):
    list_display = ['post', 'media_type', 'status', 'file_size_mb', 'downloaded_at']
    list_filter = ['media_type', 'status']
    readonly_fields = ['file_size_mb', 'downloaded_at']
