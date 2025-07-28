from django.contrib import admin
from .models import SocialMediaAccount, SocialMediaPost, SocialMediaFile, SocialMediaImportSession

@admin.register(SocialMediaAccount)
class SocialMediaAccountAdmin(admin.ModelAdmin):
    list_display = ['store', 'platform', 'username', 'is_active', 'last_sync', 'created_at']
    list_filter = ['platform', 'is_active', 'created_at']
    search_fields = ['username', 'store__name_fa']
    readonly_fields = ['last_sync', 'created_at', 'updated_at']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        # Only show accounts for stores owned by current user
        return qs.filter(store__owner=request.user)

@admin.register(SocialMediaPost)
class SocialMediaPostAdmin(admin.ModelAdmin):
    list_display = ['account', 'post_id', 'caption_preview', 'post_date', 'is_imported', 'likes_count']
    list_filter = ['account__platform', 'is_imported', 'post_date']
    search_fields = ['post_id', 'caption', 'account__username']
    readonly_fields = ['post_date', 'created_at', 'import_date']
    
    def caption_preview(self, obj):
        if obj.caption:
            return obj.caption[:50] + '...' if len(obj.caption) > 50 else obj.caption
        return '-'
    caption_preview.short_description = 'Caption Preview'

@admin.register(SocialMediaFile)
class SocialMediaFileAdmin(admin.ModelAdmin):
    list_display = ['post', 'file_type', 'is_selected', 'downloaded_at', 'file_size']
    list_filter = ['file_type', 'is_selected', 'downloaded_at']
    readonly_fields = ['downloaded_at', 'created_at']

@admin.register(SocialMediaImportSession)
class SocialMediaImportSessionAdmin(admin.ModelAdmin):
    list_display = ['account', 'status', 'posts_found', 'posts_imported', 'started_at', 'completed_at']
    list_filter = ['status', 'started_at']
    readonly_fields = ['started_at', 'completed_at']
