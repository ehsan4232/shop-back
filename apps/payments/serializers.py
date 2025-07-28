from rest_framework import serializers
from .models import *

class PaymentGatewaySerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentGateway
        fields = [
            'id', 'gateway', 'merchant_id', 'is_active', 'is_sandbox',
            'created_at', 'updated_at'
        ]
        extra_kwargs = {
            'api_key': {'write_only': True},
            'username': {'write_only': True},
            'password': {'write_only': True},
        }

class PaymentSerializer(serializers.ModelSerializer):
    gateway_name = serializers.CharField(source='gateway.get_gateway_display', read_only=True)
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    
    class Meta:
        model = Payment
        fields = [
            'id', 'order', 'order_number', 'gateway', 'gateway_name',
            'amount', 'status', 'transaction_id', 'authority', 
            'reference_id', 'tracking_code', 'created_at', 'paid_at'
        ]

class RefundSerializer(serializers.ModelSerializer):
    payment_order_number = serializers.CharField(source='payment.order.order_number', read_only=True)
    
    class Meta:
        model = Refund
        fields = [
            'id', 'payment', 'payment_order_number', 'amount', 'reason',
            'status', 'refund_id', 'created_at', 'processed_at'
        ]
