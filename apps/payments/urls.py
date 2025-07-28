from django.urls import path
from . import views

urlpatterns = [
    # Payment Gateways
    path('gateways/', views.PaymentGatewayListView.as_view(), name='payment-gateways-list'),
    path('gateways/<uuid:pk>/', views.PaymentGatewayDetailView.as_view(), name='payment-gateway-detail'),
    
    # Payments
    path('', views.PaymentListView.as_view(), name='payments-list'),
    path('<uuid:pk>/', views.PaymentDetailView.as_view(), name='payment-detail'),
    
    # Payment Processing
    path('request/', views.create_payment_request, name='payment-request'),
    path('verify/', views.verify_payment, name='payment-verify'),
    
    # Refunds
    path('refunds/', views.RefundListCreateView.as_view(), name='refunds-list'),
]
