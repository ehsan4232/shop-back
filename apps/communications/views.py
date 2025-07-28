from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import *
from .serializers import *

class SMSTemplateListView(generics.ListCreateAPIView):
    serializer_class = SMSTemplateSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return SMSTemplate.objects.filter(store__owner=self.request.user)

class EmailTemplateListView(generics.ListCreateAPIView):
    serializer_class = EmailTemplateSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return EmailTemplate.objects.filter(store__owner=self.request.user)

class NotificationListView(generics.ListAPIView):
    serializer_class = PushNotificationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return PushNotification.objects.filter(store__owner=self.request.user)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def SendSMSView(request):
    """Send SMS message"""
    recipient = request.data.get('recipient')
    content = request.data.get('content')
    template_id = request.data.get('template_id')
    
    store = request.user.stores.first()
    if not store:
        return Response({'error': 'Store not found'}, status=400)
    
    # Use template if provided
    if template_id:
        try:
            template = SMSTemplate.objects.get(id=template_id, store=store)
            content = template.content
            template.increment_usage()
        except SMSTemplate.DoesNotExist:
            return Response({'error': 'Template not found'}, status=404)
    
    # Create SMS message
    sms = SMSMessage.objects.create(
        store=store,
        recipient=recipient,
        content=content,
        template_id=template_id if template_id else None,
        status='pending'
    )
    
    # Here you would integrate with SMS provider
    sms.status = 'sent'
    sms.save()
    
    return Response({'message_id': sms.id, 'status': 'sent'})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def SendEmailView(request):
    """Send email message"""
    recipient = request.data.get('recipient')
    subject = request.data.get('subject')
    content = request.data.get('content')
    
    store = request.user.stores.first()
    if not store:
        return Response({'error': 'Store not found'}, status=400)
    
    # Here you would integrate with email service
    return Response({'status': 'sent'})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def SendPushNotificationView(request):
    """Send push notification"""
    title = request.data.get('title')
    body = request.data.get('body')
    target_type = request.data.get('target_type', 'all_users')
    
    store = request.user.stores.first()
    if not store:
        return Response({'error': 'Store not found'}, status=400)
    
    notification = PushNotification.objects.create(
        store=store,
        title=title,
        body=body,
        target_type=target_type,
        status='pending'
    )
    
    # Here you would integrate with push notification service
    notification.status = 'sent'
    notification.sent_count = 1
    notification.save()
    
    return Response({'notification_id': notification.id, 'status': 'sent'})
