from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from .models import Order, Cart, CartItem
from .serializers import OrderSerializer, CartSerializer, CartItemSerializer

class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Order.objects.filter(customer=self.request.user)

class CartViewSet(viewsets.ModelViewSet):
    serializer_class = CartSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Cart.objects.filter(customer=self.request.user)
    
    @action(detail=True, methods=['post'])
    def add_item(self, request, pk=None):
        cart = self.get_object()
        product_instance_id = request.data.get('product_instance_id')
        quantity = request.data.get('quantity', 1)
        
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product_instance_id=product_instance_id,
            defaults={'quantity': quantity}
        )
        
        if not created:
            cart_item.quantity += quantity
            cart_item.save()
        
        return Response(CartItemSerializer(cart_item).data)
    
    @action(detail=True, methods=['delete'])
    def clear(self, request, pk=None):
        cart = self.get_object()
        cart.items.all().delete()
        return Response({'message': 'سبد خرید خالی شد'})

class CheckoutView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        # Implementation for checkout process
        return Response({'message': 'پردازش سفارش'})