from rest_framework import generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.db.models import Sum, Count, Avg
from django.utils import timezone
from datetime import timedelta
from apps.stores.models import Store
from apps.orders.models import Order
from apps.products.models import Product
from .models import StoreAnalytics, ProductAnalytics, WebsiteTraffic
import json


class StoreAnalyticsAPIView(generics.RetrieveAPIView):
    """
    Store analytics dashboard data
    Product requirement: "dashboards of charts and info about their sales and website views"
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, store_id=None):
        # Get store
        try:
            store = Store.objects.get(id=store_id, owner=request.user)
        except Store.DoesNotExist:
            return Response({'error': 'فروشگاه یافت نشد'}, status=404)
        
        # Get time range
        time_range = request.GET.get('time_range', '30d')
        days = {
            '7d': 7,
            '30d': 30,
            '90d': 90,
            '1y': 365
        }.get(time_range, 30)
        
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        # Calculate analytics
        orders = Order.objects.filter(
            store=store,
            created_at__gte=start_date
        )
        
        # Basic stats
        total_sales = orders.aggregate(total=Sum('total_amount'))['total'] or 0
        total_orders = orders.count()
        total_customers = orders.values('customer').distinct().count()
        
        # Get website views from analytics
        website_views = WebsiteTraffic.objects.filter(
            store=store,
            created_at__gte=start_date
        ).aggregate(total=Sum('page_views'))['total'] or 0
        
        # Conversion rate
        conversion_rate = (total_orders / max(website_views, 1)) * 100
        
        # Average order value
        average_order_value = total_sales / max(total_orders, 1)
        
        # Sales growth (compared to previous period)
        prev_start = start_date - timedelta(days=days)
        prev_orders = Order.objects.filter(
            store=store,
            created_at__gte=prev_start,
            created_at__lt=start_date
        )
        prev_sales = prev_orders.aggregate(total=Sum('total_amount'))['total'] or 0
        sales_growth = ((total_sales - prev_sales) / max(prev_sales, 1)) * 100
        
        # Popular products
        popular_products = []
        product_stats = orders.values(
            'items__product__name'
        ).annotate(
            sales_count=Sum('items__quantity'),
            revenue=Sum('items__total_price')
        ).order_by('-revenue')[:5]
        
        for stat in product_stats:
            if stat['items__product__name']:
                popular_products.append({
                    'name': stat['items__product__name'],
                    'sales_count': stat['sales_count'] or 0,
                    'revenue': float(stat['revenue'] or 0)
                })
        
        # Daily sales data
        daily_sales = []
        for i in range(days):
            day = start_date + timedelta(days=i)
            day_orders = orders.filter(
                created_at__date=day.date()
            )
            daily_sales.append({
                'date': day.isoformat(),
                'sales': float(day_orders.aggregate(total=Sum('total_amount'))['total'] or 0),
                'orders': day_orders.count()
            })
        
        # Traffic sources (mock data for now)
        traffic_sources = [
            {'source': 'جستجوی مستقیم', 'visitors': int(website_views * 0.4), 'percentage': 40.0},
            {'source': 'شبکه‌های اجتماعی', 'visitors': int(website_views * 0.3), 'percentage': 30.0},
            {'source': 'موتورهای جستجو', 'visitors': int(website_views * 0.2), 'percentage': 20.0},
            {'source': 'سایر', 'visitors': int(website_views * 0.1), 'percentage': 10.0},
        ]
        
        return Response({
            'total_sales': float(total_sales),
            'total_orders': total_orders,
            'total_customers': total_customers,
            'website_views': website_views,
            'conversion_rate': round(conversion_rate, 2),
            'average_order_value': float(average_order_value),
            'sales_growth': round(sales_growth, 1),
            'popular_products': popular_products,
            'sales_by_day': daily_sales,
            'traffic_sources': traffic_sources
        })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def sales_chart_data(request, store_id):
    """Sales chart data for analytics dashboard"""
    try:
        store = Store.objects.get(id=store_id, owner=request.user)
    except Store.DoesNotExist:
        return Response({'error': 'فروشگاه یافت نشد'}, status=404)
    
    # Get time range
    time_range = request.GET.get('range', '30d')
    days = {
        '7d': 7,
        '30d': 30,
        '90d': 90,
        '1y': 365
    }.get(time_range, 30)
    
    end_date = timezone.now()
    start_date = end_date - timedelta(days=days)
    
    # Get daily sales data
    chart_data = []
    for i in range(days):
        day = start_date + timedelta(days=i)
        orders = Order.objects.filter(
            store=store,
            created_at__date=day.date()
        )
        
        chart_data.append({
            'date': day.strftime('%Y-%m-%d'),
            'sales': float(orders.aggregate(total=Sum('total_amount'))['total'] or 0),
            'orders': orders.count(),
            'customers': orders.values('customer').distinct().count()
        })
    
    return Response({
        'chart_data': chart_data,
        'time_range': time_range
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def website_stats(request, store_id):
    """Website traffic statistics"""
    try:
        store = Store.objects.get(id=store_id, owner=request.user)
    except Store.DoesNotExist:
        return Response({'error': 'فروشگاه یافت نشد'}, status=404)
    
    # Get time range
    days = int(request.GET.get('days', 30))
    end_date = timezone.now()
    start_date = end_date - timedelta(days=days)
    
    # Get website traffic data
    traffic_data = WebsiteTraffic.objects.filter(
        store=store,
        created_at__gte=start_date
    )
    
    # Aggregate stats
    total_views = traffic_data.aggregate(total=Sum('page_views'))['total'] or 0
    unique_visitors = traffic_data.aggregate(total=Sum('unique_visitors'))['total'] or 0
    bounce_rate = traffic_data.aggregate(avg=Avg('bounce_rate'))['avg'] or 0
    avg_session_duration = traffic_data.aggregate(avg=Avg('avg_session_duration'))['avg'] or 0
    
    # Popular pages
    popular_pages = traffic_data.values('page_path').annotate(
        views=Sum('page_views')
    ).order_by('-views')[:10]
    
    return Response({
        'total_views': total_views,
        'unique_visitors': unique_visitors,
        'bounce_rate': round(bounce_rate, 2),
        'avg_session_duration': round(float(avg_session_duration or 0), 2),
        'popular_pages': list(popular_pages)
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def analytics_reports(request, store_id):
    """Generate analytics reports"""
    try:
        store = Store.objects.get(id=store_id, owner=request.user)
    except Store.DoesNotExist:
        return Response({'error': 'فروشگاه یافت نشد'}, status=404)
    
    report_type = request.GET.get('type', 'summary')
    
    if report_type == 'products':
        # Product performance report
        products = Product.objects.filter(store=store)
        product_data = []
        
        for product in products:
            orders = Order.objects.filter(
                store=store,
                items__product=product
            )
            
            total_sold = orders.aggregate(
                quantity=Sum('items__quantity'),
                revenue=Sum('items__total_price')
            )
            
            product_data.append({
                'name': product.name_fa,
                'sku': product.sku,
                'quantity_sold': total_sold['quantity'] or 0,
                'revenue': float(total_sold['revenue'] or 0),
                'current_stock': product.stock_quantity
            })
        
        return Response({
            'report_type': 'products',
            'products': product_data
        })
    
    elif report_type == 'customers':
        # Customer analytics report
        customers = Order.objects.filter(store=store).values('customer').distinct()
        customer_data = []
        
        for customer in customers:
            if customer['customer']:
                orders = Order.objects.filter(
                    store=store,
                    customer_id=customer['customer']
                )
                
                customer_stats = orders.aggregate(
                    total_orders=Count('id'),
                    total_spent=Sum('total_amount'),
                    avg_order=Avg('total_amount')
                )
                
                customer_data.append({
                    'customer_id': customer['customer'],
                    'total_orders': customer_stats['total_orders'],
                    'total_spent': float(customer_stats['total_spent'] or 0),
                    'average_order': float(customer_stats['avg_order'] or 0)
                })
        
        return Response({
            'report_type': 'customers',
            'customers': customer_data
        })
    
    else:
        # Summary report
        end_date = timezone.now()
        start_date = end_date - timedelta(days=30)
        
        orders = Order.objects.filter(
            store=store,
            created_at__gte=start_date
        )
        
        summary = {
            'period': '30 روز گذشته',
            'total_orders': orders.count(),
            'total_revenue': float(orders.aggregate(total=Sum('total_amount'))['total'] or 0),
            'unique_customers': orders.values('customer').distinct().count(),
            'top_selling_products': []
        }
        
        # Top selling products
        top_products = orders.values(
            'items__product__name_fa'
        ).annotate(
            quantity=Sum('items__quantity')
        ).order_by('-quantity')[:5]
        
        for product in top_products:
            if product['items__product__name_fa']:
                summary['top_selling_products'].append({
                    'name': product['items__product__name_fa'],
                    'quantity_sold': product['quantity']
                })
        
        return Response({
            'report_type': 'summary',
            'summary': summary
        })
