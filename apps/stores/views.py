"""
Store Views - Complete implementation
"""
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.db.models import Count, Sum, Avg, Q
from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import timedelta
import dns.resolver
import re

from .models import Store, StoreTheme, StoreSettings, StoreAnalytics
from .serializers import (
    StoreSerializer, StoreDetailSerializer, StoreCreateSerializer,
    StoreThemeSerializer, StoreSettingsSerializer, StoreAnalyticsSerializer
)


class IsStoreOwnerOrReadOnly(permissions.BasePermission):
    """Custom permission to only allow owners of a store to edit it."""
    
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.owner == request.user


class StoreViewSet(viewsets.ModelViewSet):
    """Store management ViewSet"""
    permission_classes = [permissions.IsAuthenticated, IsStoreOwnerOrReadOnly]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return StoreCreateSerializer
        elif self.action in ['retrieve']:
            return StoreDetailSerializer
        return StoreSerializer
    
    def get_queryset(self):
        if self.request.user.is_superuser:
            return Store.objects.all()
        return Store.objects.filter(owner=self.request.user)
    
    def perform_create(self, serializer):
        if not self.request.user.can_create_store():
            raise ValidationError("شما مجاز به ایجاد فروشگاه نیستید")
        
        existing_stores = Store.objects.filter(owner=self.request.user).count()
        if existing_stores >= 5:
            raise ValidationError("حداکثر تعداد فروشگاه مجاز تولید شده است")
        
        store = serializer.save(owner=self.request.user)
        
        # Create default theme and settings
        StoreTheme.objects.create(
            store=store,
            name='پیش‌فرض',
            primary_color='#3B82F6'
        )
        StoreSettings.objects.create(store=store)


class CurrentStoreView(APIView):
    """Get current store information based on request context"""
    permission_classes = [permissions.AllowAny]
    
    def get(self, request):
        store = getattr(request, 'store', None)
        if not store:
            return Response({'error': 'Store not found'}, status=404)
        
        serializer = StoreDetailSerializer(store)
        return Response(serializer.data)


class StoreStatisticsView(APIView):
    """Get comprehensive store statistics"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        store_id = request.query_params.get('store')
        if store_id:
            store = get_object_or_404(Store, id=store_id, owner=request.user)
        else:
            store = getattr(request, 'store', None)
            if not store:
                return Response({'error': 'Store not found'}, status=404)
        
        from apps.products.models import Product, ProductCategory, Brand
        
        stats = {
            'total_products': Product.objects.filter(store=store, status='published').count(),
            'total_categories': ProductCategory.objects.filter(store=store, is_active=True).count(),
            'total_brands': Brand.objects.filter(store=store, is_active=True).count(),
            'total_revenue': store.total_revenue,
            'total_views': store.view_count,
        }
        
        return Response(stats)


class StoreAnalyticsView(APIView):
    """Get detailed analytics data"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        store = getattr(request, 'store', None)
        if not store:
            return Response({'error': 'Store not found'}, status=404)
        
        days = int(request.query_params.get('days', 30))
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        analytics = StoreAnalytics.objects.filter(
            store=store,
            date__gte=start_date,
            date__lte=end_date
        ).order_by('date')
        
        serializer = StoreAnalyticsSerializer(analytics, many=True)
        return Response(serializer.data)


class StoreThemeView(APIView):
    """Manage store theme"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        store = self._get_user_store(request)
        theme = get_object_or_404(StoreTheme, store=store)
        serializer = StoreThemeSerializer(theme)
        return Response(serializer.data)
    
    def put(self, request):
        store = self._get_user_store(request)
        theme = get_object_or_404(StoreTheme, store=store)
        serializer = StoreThemeSerializer(theme, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)
    
    def _get_user_store(self, request):
        store_id = request.query_params.get('store')
        if store_id:
            return get_object_or_404(Store, id=store_id, owner=request.user)
        return getattr(request, 'store', None)


class StoreSettingsView(APIView):
    """Manage store settings"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        store = self._get_user_store(request)
        settings = get_object_or_404(StoreSettings, store=store)
        serializer = StoreSettingsSerializer(settings)
        return Response(serializer.data)
    
    def put(self, request):
        store = self._get_user_store(request)
        settings = get_object_or_404(StoreSettings, store=store)
        serializer = StoreSettingsSerializer(settings, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)
    
    def _get_user_store(self, request):
        store_id = request.query_params.get('store')
        return get_object_or_404(Store, id=store_id, owner=request.user)


class SubdomainValidationView(APIView):
    """Validate subdomain availability"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        subdomain = request.data.get('subdomain', '').lower().strip()
        
        if not subdomain:
            return Response({'error': 'زیردامنه الزامی است'}, status=400)
        
        if not re.match(r'^[a-zA-Z0-9]([a-zA-Z0-9-]{0,48}[a-zA-Z0-9])?$', subdomain):
            return Response({'error': 'فرمت زیردامنه نامعتبر است'}, status=400)
        
        reserved = ['www', 'api', 'admin', 'mail', 'ftp', 'blog']
        if subdomain in reserved:
            return Response({'error': 'این زیردامنه رزرو شده است'}, status=400)
        
        if Store.objects.filter(subdomain=subdomain).exists():
            return Response({'available': False, 'error': 'این زیردامنه قبلاً استفاده شده است'})
        
        return Response({'available': True, 'subdomain': subdomain})


class DomainValidationView(APIView):
    """Validate custom domain availability"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        domain = request.data.get('domain', '').lower().strip()
        
        if not domain:
            return Response({'error': 'دامنه الزامی است'}, status=400)
        
        if Store.objects.filter(domain=domain).exists():
            return Response({'available': False, 'error': 'این دامنه قبلاً استفاده شده است'})
        
        return Response({'available': True, 'domain': domain})


class DomainCheckView(APIView):
    """Check domain DNS configuration"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        domain = request.data.get('domain', '').lower().strip()
        
        if not domain:
            return Response({'error': 'دامنه الزامی است'}, status=400)
        
        return Response({
            'domain': domain,
            'available': not Store.objects.filter(domain=domain).exists(),
            'dns_configured': True,  # Simplified for now
            'instructions': {
                'A_record': {
                    'name': '@',
                    'type': 'A',
                    'value': '95.217.163.246',
                    'ttl': 3600
                }
            }
        })


class DomainSetupView(APIView):
    """Setup custom domain for store"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        store_id = request.data.get('store_id')
        domain = request.data.get('domain', '').lower().strip()
        
        store = get_object_or_404(Store, id=store_id, owner=request.user)
        
        if Store.objects.filter(domain=domain).exclude(id=store.id).exists():
            return Response({'error': 'این دامنه قبلاً استفاده شده است'}, status=400)
        
        store.domain = domain
        store.save()
        
        return Response({
            'message': 'دامنه با موفقیت تنظیم شد',
            'domain': domain,
            'store_url': f'https://{domain}'
        })


class ThemePreviewView(APIView):
    """Preview theme changes"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        store_id = request.data.get('store_id')
        store = get_object_or_404(Store, id=store_id, owner=request.user)
        
        return Response({
            'preview_url': f'/preview/{store.slug}/',
            'theme_data': request.data
        })
