from rest_framework import serializers
from .models import PaymentGateway, Payment, Refund

class PaymentGatewaySerializer(serializers.ModelSerializer):
    gateway_display = serializers.CharField(source='get_gateway_display', read_only=True)
    
    class Meta:
        model = PaymentGateway
        fields = [
            'id', 'gateway', 'gateway_display', 'merchant_id', 'is_active',
            'is_sandbox', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

class PaymentSerializer(serializers.ModelSerializer):
    gateway_name = serializers.CharField(source='gateway.get_gateway_display', read_only=True)
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Payment
        fields = [
            'id', 'order', 'order_number', 'gateway', 'gateway_name', 'amount',
            'status', 'status_display', 'transaction_id', 'authority',
            'reference_id', 'tracking_code', 'error_message', 'created_at',
            'paid_at', 'verified_at'
        ]
        read_only_fields = ['id', 'created_at', 'paid_at', 'verified_at']

class RefundSerializer(serializers.ModelSerializer):
    payment_order = serializers.CharField(source='payment.order.order_number', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Refund
        fields = [
            'id', 'payment', 'payment_order', 'amount', 'reason', 'status',
            'status_display', 'refund_id', 'created_at', 'processed_at'
        ]
        read_only_fields = ['id', 'created_at', 'processed_at']

class PaymentRequestSerializer(serializers.Serializer):
    """Serializer for payment request"""
    order_id = serializers.UUIDField()
    gateway = serializers.ChoiceField(choices=PaymentGateway.GATEWAY_CHOICES)
    callback_url = serializers.URLField()

class PaymentVerifySerializer(serializers.Serializer):
    """Serializer for payment verification"""
    payment_id = serializers.UUIDField()
    authority = serializers.CharField(max_length=100)
    status = serializers.CharField(max_length=20)
