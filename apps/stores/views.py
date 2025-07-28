from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404
from django.db.models import Count, Sum, Avg
from django.utils import timezone
from datetime import timedelta
from .models import Store, StoreTheme, StoreSettings, StoreAnalytics
from .serializers import *
from apps.products.models import Product
from apps.orders.models import Order
from apps.accounts.models import User

class StoreListCreateView(generics.ListCreateAPIView):
    """List user's stores and create new store"""
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return StoreCreateUpdateSerializer
        return StoreListSerializer
    
    def get_queryset(self):
        return Store.objects.filter(owner=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

class StoreDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, delete store"""
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return StoreCreateUpdateSerializer
        return StoreDetailSerializer
    
    def get_queryset(self):
        return Store.objects.filter(owner=self.request.user)

class StoreThemeView(generics.RetrieveUpdateAPIView):
    """Get and update store theme"""
    serializer_class = StoreThemeSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        store = get_object_or_404(Store, pk=self.kwargs['store_pk'], owner=self.request.user)
        theme, created = StoreTheme.objects.get_or_create(store=store)
        return theme

class StoreSettingsView(generics.RetrieveUpdateAPIView):
    """Get and update store settings"""
    serializer_class = StoreSettingsSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        store = get_object_or_404(Store, pk=self.kwargs['store_pk'], owner=self.request.user)
        settings, created = StoreSettings.objects.get_or_create(store=store)
        return settings

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def store_statistics(request, store_pk):
    """Get comprehensive store statistics"""
    store = get_object_or_404(Store, pk=store_pk, owner=request.user)
    
    # Basic counts
    total_products = Product.objects.filter(store=store, status='published').count()
    total_orders = Order.objects.filter(store=store).count()
    total_revenue = Order.objects.filter(
        store=store, 
        payment_status='paid'
    ).aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    
    # Customer stats
    total_customers = Order.objects.filter(store=store).values('customer').distinct().count()
    
    # Monthly stats (last 30 days)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    monthly_orders = Order.objects.filter(
        store=store,
        created_at__gte=thirty_days_ago
    ).count()
    
    monthly_revenue = Order.objects.filter(
        store=store,
        created_at__gte=thirty_days_ago,
        payment_status='paid'
    ).aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    
    # Conversion rate (mock calculation - you'd need proper tracking)
    conversion_rate = 2.5  # This would be calculated from actual visitor data
    
    # Average order value
    avg_order_value = Order.objects.filter(
        store=store,
        payment_status='paid'
    ).aggregate(Avg('total_amount'))['total_amount__avg'] or 0
    
    stats = StoreStatsSerializer({
        'total_products': total_products,
        'total_orders': total_orders,
        'total_revenue': total_revenue,
        'total_customers': total_customers,
        'monthly_revenue': monthly_revenue,
        'monthly_orders': monthly_orders,
        'conversion_rate': conversion_rate,
        'average_order_value': avg_order_value,
    }).data
    
    return Response(stats)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def store_analytics_data(request, store_pk):
    """Get detailed analytics data for charts"""
    store = get_object_or_404(Store, pk=store_pk, owner=request.user)
    
    # Get date range from query params
    days = int(request.GET.get('days', 30))
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days)
    
    # Daily analytics
    analytics = StoreAnalytics.objects.filter(
        store=store,
        date__range=[start_date, end_date]
    ).order_by('date')
    
    analytics_data = StoreAnalyticsSerializer(analytics, many=True).data
    
    # Sales chart data
    orders_data = Order.objects.filter(
        store=store,
        created_at__date__range=[start_date, end_date]
    ).extra(select={'day': 'date(created_at)'}).values('day').annotate(
        orders_count=Count('id'),
        revenue=Sum('total_amount')
    ).order_by('day')
    
    # Top products
    top_products = Product.objects.filter(
        store=store,
        status='published'
    ).order_by('-sales_count')[:10]
    
    # Recent orders
    recent_orders = Order.objects.filter(store=store).order_by('-created_at')[:10]
    
    response_data = {
        'analytics': analytics_data,
        'sales_chart': list(orders_data),
        'top_products': [
            {
                'id': str(p.id),
                'name': p.name_fa,
                'sales_count': p.sales_count,
                'revenue': p.sales_count * p.base_price
            } for p in top_products
        ],
        'recent_orders': [
            {
                'id': str(o.id),
                'order_number': o.order_number,
                'customer_name': o.customer_name,
                'total_amount': o.total_amount,
                'status': o.status,
                'created_at': o.created_at
            } for o in recent_orders
        ]
    }
    
    return Response(response_data)

@api_view(['GET'])
@permission_classes([AllowAny])
def store_public_info(request, subdomain):
    """Get public store information for store website"""
    try:
        store = Store.objects.get(subdomain=subdomain, is_active=True)
        
        # Increment view count
        store.increment_view_count()
        
        # Get store data without sensitive information
        data = {
            'id': str(store.id),
            'name': store.name,
            'name_fa': store.name_fa,
            'description': store.description,
            'description_fa': store.description_fa,
            'logo': store.logo.url if store.logo else None,
            'banner': store.banner.url if store.banner else None,
            'phone': store.phone,
            'email': store.email,
            'address': store.address,
            'city': store.city,
            'state': store.state,
            'currency': store.currency,
            'instagram_username': store.instagram_username,
            'telegram_username': store.telegram_username,
        }
        
        # Get theme if exists
        try:
            theme = store.theme
            data['theme'] = StoreThemeSerializer(theme).data
        except StoreTheme.DoesNotExist:
            data['theme'] = None
        
        return Response(data)
        
    except Store.DoesNotExist:
        return Response({'error': 'فروشگاه یافت نشد'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def check_subdomain_availability(request):
    """Check if subdomain is available"""
    subdomain = request.data.get('subdomain', '').lower().strip()
    
    if not subdomain:
        return Response({'error': 'زیردامنه الزامی است'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Check if subdomain is already taken
    is_available = not Store.objects.filter(subdomain=subdomain).exists()
    
    return Response({
        'subdomain': subdomain,
        'available': is_available,
        'full_domain': f'{subdomain}.mall.ir' if is_available else None
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def check_domain_availability(request):
    """Check if custom domain is available"""
    domain = request.data.get('domain', '').lower().strip()
    
    if not domain:
        return Response({'error': 'دامنه الزامی است'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Check if domain is already taken
    is_available = not Store.objects.filter(domain=domain).exists()
    
    return Response({
        'domain': domain,
        'available': is_available
    })
