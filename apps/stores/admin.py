from django.contrib import admin
from .models import Store, StoreSettings

class StoreSettingsInline(admin.StackedInline):
    model = StoreSettings
    extra = 0

@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ('name_fa', 'name', 'owner', 'subdomain', 'is_active', 'created_at')
    list_filter = ('is_active', 'theme', 'layout', 'created_at')
    search_fields = ('name', 'name_fa', 'subdomain', 'owner__phone_number')
    readonly_fields = ('id', 'created_at', 'updated_at')
    inlines = [StoreSettingsInline]
    
    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('owner', 'name', 'name_fa', 'description', 'description_fa')
        }),
        ('تصاویر', {
            'fields': ('logo', 'banner')
        }),
        ('تنظیمات ظاهری', {
            'fields': ('theme', 'layout')
        }),
        ('دامنه و آدرس', {
            'fields': ('subdomain', 'domain')
        }),
        ('اطلاعات تماس', {
            'fields': ('phone_number', 'email', 'address', 'currency')
        }),
        ('شبکه‌های اجتماعی', {
            'fields': ('instagram_username', 'telegram_username')
        }),
        ('وضعیت', {
            'fields': ('is_active',)
        }),
        ('اطلاعات سیستم', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(StoreSettings)
class StoreSettingsAdmin(admin.ModelAdmin):
    list_display = ('store', 'google_analytics_id')
    search_fields = ('store__name_fa', 'store__name')