from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from .models import PaymentGateway, Payment, Refund
from .serializers import *
from apps.orders.models import Order
from apps.stores.models import Store

class PaymentGatewayListView(generics.ListCreateAPIView):
    """List and create payment gateways"""
    serializer_class = PaymentGatewaySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user_stores = Store.objects.filter(owner=self.request.user)
        return PaymentGateway.objects.filter(store__in=user_stores)
    
    def perform_create(self, serializer):
        store_id = self.request.data.get('store_id')
        store = get_object_or_404(Store, id=store_id, owner=self.request.user)
        serializer.save(store=store)

class PaymentGatewayDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, delete payment gateway"""
    serializer_class = PaymentGatewaySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user_stores = Store.objects.filter(owner=self.request.user)
        return PaymentGateway.objects.filter(store__in=user_stores)

class PaymentListView(generics.ListAPIView):
    """List payments"""
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user_stores = Store.objects.filter(owner=self.request.user)
        queryset = Payment.objects.filter(order__store__in=user_stores)
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by order
        order_id = self.request.query_params.get('order')
        if order_id:
            queryset = queryset.filter(order_id=order_id)
        
        return queryset.order_by('-created_at')

class PaymentDetailView(generics.RetrieveAPIView):
    """Get payment details"""
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user_stores = Store.objects.filter(owner=self.request.user)
        return Payment.objects.filter(order__store__in=user_stores)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_payment_request(request):
    """Create payment request"""
    serializer = PaymentRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    data = serializer.validated_data
    
    # Get order
    user_stores = Store.objects.filter(owner=request.user)
    order = get_object_or_404(
        Order,
        id=data['order_id'],
        store__in=user_stores
    )
    
    # Get gateway
    gateway = get_object_or_404(
        PaymentGateway,
        store=order.store,
        gateway=data['gateway'],
        is_active=True
    )
    
    # Create payment record
    payment = Payment.objects.create(
        order=order,
        gateway=gateway,
        amount=order.total_amount,
        status='pending'
    )
    
    # Here you would integrate with actual payment gateway
    # For now, return mock response
    response_data = {
        'payment_id': payment.id,
        'gateway_url': f'https://sandbox.zarinpal.com/pg/v4/payment/request',
        'authority': 'MOCK_AUTHORITY_123456',
        'amount': payment.amount
    }
    
    return Response(response_data)

@api_view(['POST'])
def verify_payment(request):
    """Verify payment (called by gateway callback)"""
    serializer = PaymentVerifySerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    data = serializer.validated_data
    
    try:
        payment = Payment.objects.get(id=data['payment_id'])
        
        # Update payment status based on gateway response
        if data['status'] == 'success':
            payment.status = 'success'
            payment.authority = data['authority']
            payment.paid_at = timezone.now()
            
            # Update order status
            payment.order.payment_status = 'paid'
            payment.order.save()
        else:
            payment.status = 'failed'
            payment.error_message = 'Payment verification failed'
        
        payment.save()
        
        return Response(PaymentSerializer(payment).data)
        
    except Payment.DoesNotExist:
        return Response(
            {'error': 'Payment not found'},
            status=status.HTTP_404_NOT_FOUND
        )

class RefundListCreateView(generics.ListCreateAPIView):
    """List and create refunds"""
    serializer_class = RefundSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user_stores = Store.objects.filter(owner=self.request.user)
        return Refund.objects.filter(payment__order__store__in=user_stores)
    
    def perform_create(self, serializer):
        payment_id = self.request.data.get('payment_id')
        user_stores = Store.objects.filter(owner=self.request.user)
        
        payment = get_object_or_404(
            Payment,
            id=payment_id,
            order__store__in=user_stores,
            status='success'
        )
        
        serializer.save(payment=payment)
