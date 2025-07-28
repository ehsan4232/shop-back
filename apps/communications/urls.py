from django.urls import path
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'communications'

router = DefaultRouter()

urlpatterns = [
    path('sms/templates/', views.SMSTemplateListView.as_view(), name='sms-template-list'),
    path('sms/send/', views.SendSMSView.as_view(), name='send-sms'),
    path('email/templates/', views.EmailTemplateListView.as_view(), name='email-template-list'),
    path('email/send/', views.SendEmailView.as_view(), name='send-email'),
    path('push/send/', views.SendPushNotificationView.as_view(), name='send-push'),
    path('notifications/', views.NotificationListView.as_view(), name='notification-list'),
] + router.urls
