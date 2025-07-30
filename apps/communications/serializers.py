from rest_framework import serializers
from .models import (
    SMSTemplate, SMSMessage, EmailTemplate, EmailMessage,
    PushNotification, Newsletter, NotificationLog
)

class SMSTemplateSerializer(serializers.ModelSerializer):
    """SMS template management"""
    usage_count = serializers.ReadOnlyField()
    
    class Meta:
        model = SMSTemplate
        fields = [
            'id', 'name', 'code', 'template_type', 'content', 'variables',
            'is_active', 'usage_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'usage_count', 'created_at', 'updated_at']

class SMSMessageSerializer(serializers.ModelSerializer):
    """SMS message tracking"""
    template_name = serializers.CharField(source='template.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = SMSMessage
        fields = [
            'id', 'recipient', 'content', 'template', 'template_name',
            'status', 'status_display', 'provider_message_id', 'cost',
            'error_message', 'created_at', 'sent_at', 'delivered_at'
        ]
        read_only_fields = [
            'id', 'provider_message_id', 'cost', 'error_message',
            'created_at', 'sent_at', 'delivered_at'
        ]

class BulkSMSSerializer(serializers.Serializer):
    """Send bulk SMS"""
    recipients = serializers.ListField(
        child=serializers.CharField(max_length=15),
        min_length=1,
        max_length=100
    )
    message = serializers.CharField(max_length=160)
    template_id = serializers.UUIDField(required=False)
    variables = serializers.DictField(required=False)
    
    def validate_recipients(self, value):
        from apps.core.validators import MallValidators
        validated_recipients = []
        for phone in value:
            try:
                validated_phone = MallValidators.validate_iranian_phone(phone)
                validated_recipients.append(validated_phone)
            except serializers.ValidationError:
                continue  # Skip invalid numbers
        
        if not validated_recipients:
            raise serializers.ValidationError("هیچ شماره معتبری یافت نشد")
        
        return validated_recipients

class EmailTemplateSerializer(serializers.ModelSerializer):
    """Email template management"""
    class Meta:
        model = EmailTemplate
        fields = [
            'id', 'name', 'code', 'template_type', 'subject', 'content',
            'html_template', 'variables', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

class EmailMessageSerializer(serializers.ModelSerializer):
    """Email message tracking"""
    template_name = serializers.CharField(source='template.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = EmailMessage
        fields = [
            'id', 'recipient', 'subject', 'content', 'html_content',
            'template', 'template_name', 'status', 'status_display',
            'error_message', 'created_at', 'sent_at'
        ]
        read_only_fields = [
            'id', 'error_message', 'created_at', 'sent_at'
        ]

class PushNotificationSerializer(serializers.ModelSerializer):
    """Push notification management"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    target_type_display = serializers.CharField(source='get_target_type_display', read_only=True)
    
    class Meta:
        model = PushNotification
        fields = [
            'id', 'title', 'body', 'target_type', 'target_type_display',
            'target_users', 'action_url', 'image_url', 'status',
            'status_display', 'sent_count', 'opened_count',
            'scheduled_at', 'created_at', 'sent_at'
        ]
        read_only_fields = [
            'id', 'sent_count', 'opened_count', 'created_at', 'sent_at'
        ]

class NewsletterSerializer(serializers.ModelSerializer):
    """Newsletter management"""
    subscriber_count = serializers.ReadOnlyField()
    
    class Meta:
        model = Newsletter
        fields = [
            'id', 'title', 'content', 'html_content', 'scheduled_at',
            'status', 'subscriber_count', 'sent_count', 'opened_count',
            'created_at', 'sent_at'
        ]
        read_only_fields = [
            'id', 'subscriber_count', 'sent_count', 'opened_count',
            'created_at', 'sent_at'
        ]

class NotificationLogSerializer(serializers.ModelSerializer):
    """Notification log tracking"""
    class Meta:
        model = NotificationLog
        fields = [
            'id', 'notification_type', 'recipient', 'title', 'content',
            'status', 'delivery_method', 'error_message', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

class CommunicationStatsSerializer(serializers.Serializer):
    """Communication statistics"""
    total_sms_sent = serializers.IntegerField()
    total_emails_sent = serializers.IntegerField()
    total_push_notifications = serializers.IntegerField()
    sms_success_rate = serializers.FloatField()
    email_success_rate = serializers.FloatField()
    push_success_rate = serializers.FloatField()
    monthly_stats = serializers.DictField()
