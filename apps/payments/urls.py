from django.urls import path
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'payments'

router = DefaultRouter()

urlpatterns = [
    path('gateways/', views.PaymentGatewayListView.as_view(), name='gateway-list'),
    path('gateways/<uuid:pk>/', views.PaymentGatewayDetailView.as_view(), name='gateway-detail'),
    path('process/', views.ProcessPaymentView.as_view(), name='process-payment'),
    path('verify/', views.VerifyPaymentView.as_view(), name='verify-payment'),
    path('webhook/', views.PaymentWebhookView.as_view(), name='webhook'),
    path('refund/', views.RefundPaymentView.as_view(), name='refund-payment'),
] + router.urls
