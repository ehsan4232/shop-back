from rest_framework import serializers
from .models import *

class SMSTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SMSTemplate
        fields = [
            'id', 'name', 'template_type', 'content', 'is_active',
            'usage_count', 'created_at', 'updated_at'
        ]

class SMSMessageSerializer(serializers.ModelSerializer):
    template_name = serializers.CharField(source='template.name', read_only=True)
    
    class Meta:
        model = SMSMessage
        fields = [
            'id', 'recipient', 'content', 'template', 'template_name',
            'status', 'cost', 'created_at', 'sent_at', 'delivered_at'
        ]

class EmailTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailTemplate
        fields = [
            'id', 'name', 'template_type', 'subject', 'html_content',
            'is_active', 'created_at', 'updated_at'
        ]

class PushNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PushNotification
        fields = [
            'id', 'title', 'body', 'target_type', 'action_url',
            'image_url', 'status', 'sent_count', 'scheduled_at',
            'created_at', 'sent_at'
        ]
