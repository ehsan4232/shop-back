from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import *
from .serializers import *

class PaymentGatewayListView(generics.ListAPIView):
    serializer_class = PaymentGatewaySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return PaymentGateway.objects.filter(
            store__owner=self.request.user,
            is_active=True
        )

class PaymentGatewayDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = PaymentGatewaySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return PaymentGateway.objects.filter(store__owner=self.request.user)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ProcessPaymentView(request):
    """Process payment through selected gateway"""
    order_id = request.data.get('order_id')
    gateway_id = request.data.get('gateway_id')
    
    try:
        order = Order.objects.get(id=order_id, store__owner=request.user)
        gateway = PaymentGateway.objects.get(id=gateway_id, store=order.store)
    except (Order.DoesNotExist, PaymentGateway.DoesNotExist):
        return Response({'error': 'Order or gateway not found'}, status=404)
    
    # Create payment record
    payment = Payment.objects.create(
        order=order,
        gateway=gateway,
        amount=order.total_amount,
        status='pending'
    )
    
    # Process payment based on gateway type
    if gateway.gateway == 'zarinpal':
        # ZarinPal integration logic
        payment_url = f"https://payment.zarinpal.com/pg/StartPay/{payment.authority}"
    else:
        payment_url = None
    
    return Response({
        'payment_id': payment.id,
        'payment_url': payment_url,
        'status': 'redirect_required'
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def VerifyPaymentView(request):
    """Verify payment after return from gateway"""
    payment_id = request.data.get('payment_id')
    authority = request.data.get('authority')
    
    try:
        payment = Payment.objects.get(id=payment_id)
    except Payment.DoesNotExist:
        return Response({'error': 'Payment not found'}, status=404)
    
    # Verify payment with gateway
    payment.status = 'success'
    payment.authority = authority
    payment.save()
    
    # Update order status
    payment.order.payment_status = 'paid'
    payment.order.save()
    
    return Response({'status': 'success', 'payment': PaymentSerializer(payment).data})

@api_view(['POST'])
def PaymentWebhookView(request):
    """Handle payment webhooks from gateways"""
    return Response({'status': 'received'})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def RefundPaymentView(request):
    """Process payment refund"""
    payment_id = request.data.get('payment_id')
    amount = request.data.get('amount')
    reason = request.data.get('reason')
    
    try:
        payment = Payment.objects.get(id=payment_id, order__store__owner=request.user)
    except Payment.DoesNotExist:
        return Response({'error': 'Payment not found'}, status=404)
    
    refund = Refund.objects.create(
        payment=payment,
        amount=amount or payment.amount,
        reason=reason,
        status='pending'
    )
    
    return Response({'refund_id': refund.id, 'status': 'processing'})
