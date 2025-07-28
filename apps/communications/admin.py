from django.contrib import admin
from .models import *

@admin.register(SMSTemplate)
class SMSTemplateAdmin(admin.ModelAdmin):
    list_display = ['store', 'name', 'template_type', 'is_active', 'usage_count']
    list_filter = ['template_type', 'is_active']
    search_fields = ['name', 'store__name_fa']

@admin.register(SMSMessage)
class SMSMessageAdmin(admin.ModelAdmin):
    list_display = ['recipient', 'store', 'status', 'cost', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['recipient', 'content']
    readonly_fields = ['created_at', 'sent_at', 'delivered_at']

@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ['store', 'name', 'template_type', 'is_active', 'usage_count']
    list_filter = ['template_type', 'is_active']
    search_fields = ['name', 'subject', 'store__name_fa']

@admin.register(PushNotification)
class PushNotificationAdmin(admin.ModelAdmin):
    list_display = ['store', 'title', 'target_type', 'status', 'sent_count', 'scheduled_at']
    list_filter = ['target_type', 'status']
    search_fields = ['title', 'body']
    readonly_fields = ['sent_count', 'created_at', 'sent_at']
