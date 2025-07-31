from django.db import models
from django.utils import timezone
from django.db.models import Count, Sum, Avg, Q, F
from django.core.cache import cache
from apps.core.mixins import TimestampMixin, StoreOwnedMixin
import uuid
from datetime import datetime, timedelta
import json


class AnalyticsPeriod(models.TextChoices):
    """Time periods for analytics"""
    TODAY = 'today', 'امروز'
    YESTERDAY = 'yesterday', 'دیروز'
    LAST_7_DAYS = '7d', '7 روز گذشته'
    LAST_30_DAYS = '30d', '30 روز گذشته'
    THIS_MONTH = 'this_month', 'این ماه'
    LAST_MONTH = 'last_month', 'ماه گذشته'
    THIS_YEAR = 'this_year', 'امسال'
    LAST_YEAR = 'last_year', 'سال گذشته'
    CUSTOM = 'custom', 'سفارشی'


class StoreAnalytics(StoreOwnedMixin, TimestampMixin):
    """
    Store analytics dashboard data
    Product requirement: "dashboards of charts and info about their sales and website views and interactions"
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Date for this analytics record
    date = models.DateField(verbose_name='تاریخ')
    
    # Sales metrics
    total_sales = models.DecimalField(
        max_digits=15, 
        decimal_places=0, 
        default=0,
        verbose_name='فروش کل (تومان)'
    )
    orders_count = models.PositiveIntegerField(default=0, verbose_name='تعداد سفارشات')
    avg_order_value = models.DecimalField(
        max_digits=12, 
        decimal_places=0, 
        default=0,
        verbose_name='میانگین ارزش سفارش'
    )
    
    # Product metrics
    products_sold = models.PositiveIntegerField(default=0, verbose_name='تعداد محصولات فروخته شده')
    top_selling_product = models.JSONField(
        default=dict, 
        blank=True,
        verbose_name='پرفروش‌ترین محصول'
    )
    
    # Website metrics
    page_views = models.PositiveIntegerField(default=0, verbose_name='بازدید صفحات')
    unique_visitors = models.PositiveIntegerField(default=0, verbose_name='بازدیدکنندگان منحصربه‌فرد')
    session_duration_avg = models.PositiveIntegerField(default=0, verbose_name='میانگین مدت جلسه (ثانیه)')
    bounce_rate = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=0,
        verbose_name='نرخ خروج سریع (%)'
    )
    
    # Customer metrics
    new_customers = models.PositiveIntegerField(default=0, verbose_name='مشتریان جدید')
    returning_customers = models.PositiveIntegerField(default=0, verbose_name='مشتریان بازگشتی')
    customer_lifetime_value = models.DecimalField(
        max_digits=12, 
        decimal_places=0, 
        default=0,
        verbose_name='ارزش مادام‌العمر مشتری'
    )
    
    # Conversion metrics
    conversion_rate = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=0,
        verbose_name='نرخ تبدیل (%)'
    )
    cart_abandonment_rate = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=0,
        verbose_name='نرخ رها کردن سبد خرید (%)'
    )
    
    # Traffic sources
    traffic_sources = models.JSONField(
        default=dict, 
        blank=True,
        verbose_name='منابع ترافیک'
    )
    
    # Popular pages
    popular_pages = models.JSONField(
        default=list, 
        blank=True,
        verbose_name='صفحات محبوب'
    )
    
    # Device analytics
    device_breakdown = models.JSONField(
        default=dict, 
        blank=True,
        verbose_name='تفکیک دستگاه‌ها'
    )
    
    # Geographic data
    top_cities = models.JSONField(
        default=list, 
        blank=True,
        verbose_name='شهرهای برتر'
    )
    
    # Social media engagement
    social_media_metrics = models.JSONField(
        default=dict, 
        blank=True,
        verbose_name='متریک‌های شبکه‌های اجتماعی'
    )
    
    class Meta:
        verbose_name = 'آنالیتیک فروشگاه'
        verbose_name_plural = 'آنالیتیک‌های فروشگاه'
        unique_together = ['store', 'date']
        ordering = ['-date']
        indexes = [
            models.Index(fields=['store', '-date']),
            models.Index(fields=['date']),
        ]
    
    def __str__(self):
        return f"آنالیتیک {self.store.name_fa} - {self.date}"
    
    @classmethod
    def generate_daily_analytics(cls, store, date=None):
        """Generate analytics for a specific date"""
        if date is None:
            date = timezone.now().date()
        
        # Get or create analytics record
        analytics, created = cls.objects.get_or_create(
            store=store,
            date=date,
            defaults={}
        )
        
        # Calculate metrics for the date
        from apps.orders.models import Order
        from apps.products.models import Product
        
        # Sales metrics
        orders = Order.objects.filter(
            store=store,
            created_at__date=date,
            status__in=['completed', 'delivered']
        )
        
        analytics.total_sales = orders.aggregate(
            total=Sum('total_amount')
        )['total'] or 0
        
        analytics.orders_count = orders.count()
        
        if analytics.orders_count > 0:
            analytics.avg_order_value = analytics.total_sales / analytics.orders_count
        
        # Get most popular product
        top_product = orders.values(
            'items__product__name_fa'
        ).annotate(
            quantity=Sum('items__quantity')
        ).order_by('-quantity').first()
        
        if top_product:
            analytics.top_selling_product = {
                'name': top_product['items__product__name_fa'],
                'quantity': top_product['quantity']
            }
        
        # Customer metrics - simplified
        analytics.new_customers = store.customers.filter(
            created_at__date=date
        ).count()
        
        analytics.save()
        return analytics


class WebsiteAnalytics(StoreOwnedMixin, TimestampMixin):
    """
    Website interaction analytics
    Product requirement: "website views and interactions"
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Session info
    session_id = models.CharField(max_length=100, verbose_name='شناسه جلسه')
    ip_address = models.GenericIPAddressField(verbose_name='آدرس IP')
    user_agent = models.TextField(verbose_name='User Agent')
    
    # Visit details
    page_url = models.URLField(verbose_name='آدرес صفحه')
    page_title = models.CharField(max_length=200, blank=True, verbose_name='عنوان صفحه')
    referrer = models.URLField(blank=True, verbose_name='مرجع')
    
    # Timing
    session_start = models.DateTimeField(verbose_name='شروع جلسه')
    page_view_time = models.DateTimeField(verbose_name='زمان بازدید صفحه')
    time_on_page = models.PositiveIntegerField(default=0, verbose_name='مدت زمان در صفحه (ثانیه)')
    
    # Device and location
    device_type = models.CharField(
        max_length=20,
        choices=[
            ('desktop', 'دسکتاپ'),
            ('mobile', 'موبایل'),
            ('tablet', 'تبلت'),
        ],
        default='desktop',
        verbose_name='نوع دستگاه'
    )
    browser = models.CharField(max_length=50, blank=True, verbose_name='مرورگر')
    os = models.CharField(max_length=50, blank=True, verbose_name='سیستم عامل')
    city = models.CharField(max_length=100, blank=True, verbose_name='شهر')
    country = models.CharField(max_length=100, blank=True, verbose_name='کشور')
    
    # Interaction tracking
    clicks_count = models.PositiveIntegerField(default=0, verbose_name='تعداد کلیک')
    scroll_depth = models.PositiveIntegerField(default=0, verbose_name='عمق اسکرول (%)')
    is_bounce = models.BooleanField(default=False, verbose_name='خروج سریع')
    
    # Conversion tracking
    viewed_products = models.ManyToManyField(
        'products.Product',
        blank=True,
        verbose_name='محصولات مشاهده شده'
    )
    added_to_cart = models.ManyToManyField(
        'products.Product',
        blank=True,
        through='ProductCartInteraction',
        related_name='cart_additions',
        verbose_name='اضافه شده به سبد'
    )
    
    class Meta:
        verbose_name = 'آنالیتیک وبسایت'
        verbose_name_plural = 'آنالیتیک‌های وبسایت'
        ordering = ['-page_view_time']
        indexes = [
            models.Index(fields=['store', '-page_view_time']),
            models.Index(fields=['session_id']),
            models.Index(fields=['ip_address', '-page_view_time']),
            models.Index(fields=['device_type']),
        ]
    
    def __str__(self):
        return f"بازدید {self.page_url} - {self.page_view_time}"


class ProductCartInteraction(TimestampMixin):
    """Track when products are added to cart"""
    
    website_analytics = models.ForeignKey(WebsiteAnalytics, on_delete=models.CASCADE)
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    
    class Meta:
        verbose_name = 'تعامل سبد خرید'
        verbose_name_plural = 'تعاملات سبد خرید'


class DashboardWidget(StoreOwnedMixin, TimestampMixin):
    """
    Customizable dashboard widgets for store owners
    """
    
    WIDGET_TYPES = [
        ('sales_chart', 'نمودار فروش'),
        ('orders_count', 'تعداد سفارشات'),
        ('revenue_metric', 'متریک درآمد'),
        ('top_products', 'محصولات برتر'),
        ('customer_growth', 'رشد مشتریان'),
        ('traffic_sources', 'منابع ترافیک'),
        ('conversion_funnel', 'قیف تبدیل'),
        ('geographic_map', 'نقشه جغرافیایی'),
        ('recent_orders', 'سفارشات اخیر'),
        ('low_stock_alert', 'هشدار موجودی کم'),
    ]
    
    CHART_TYPES = [
        ('line', 'خطی'),
        ('bar', 'میله‌ای'),
        ('pie', 'دایره‌ای'),
        ('area', 'ناحیه‌ای'),
        ('donut', 'حلقه‌ای'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Widget configuration
    title = models.CharField(max_length=200, verbose_name='عنوان ویجت')
    widget_type = models.CharField(max_length=30, choices=WIDGET_TYPES, verbose_name='نوع ویجت')
    chart_type = models.CharField(
        max_length=20, 
        choices=CHART_TYPES, 
        blank=True,
        verbose_name='نوع نمودار'
    )
    
    # Layout
    position_x = models.PositiveIntegerField(default=0, verbose_name='موقعیت X')
    position_y = models.PositiveIntegerField(default=0, verbose_name='موقعیت Y')
    width = models.PositiveIntegerField(default=4, verbose_name='عرض')
    height = models.PositiveIntegerField(default=3, verbose_name='ارتفاع')
    
    # Data configuration
    data_period = models.CharField(
        max_length=20, 
        choices=AnalyticsPeriod.choices,
        default=AnalyticsPeriod.LAST_7_DAYS,
        verbose_name='دوره زمانی داده'
    )
    
    filters = models.JSONField(default=dict, blank=True, verbose_name='فیلترها')
    settings = models.JSONField(default=dict, blank=True, verbose_name='تنظیمات')
    
    # Status
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    refresh_interval = models.PositiveIntegerField(default=300, verbose_name='فاصله بروزرسانی (ثانیه)')
    
    class Meta:
        verbose_name = 'ویجت داشبورد'
        verbose_name_plural = 'ویجت‌های داشبورد'
        ordering = ['position_y', 'position_x']
        indexes = [
            models.Index(fields=['store', 'is_active']),
            models.Index(fields=['widget_type']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.get_widget_type_display()}"
    
    def get_widget_data(self):
        """Get data for this widget based on its configuration"""
        # This would be implemented based on widget type
        # Each widget type would have its own data generation logic
        cache_key = f"widget_data_{self.id}_{self.data_period}"
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return cached_data
        
        # Generate data based on widget type
        data = self._generate_widget_data()
        
        # Cache for refresh interval
        cache.set(cache_key, data, timeout=self.refresh_interval)
        return data
    
    def _generate_widget_data(self):
        """Generate data based on widget type"""
        if self.widget_type == 'sales_chart':
            return self._get_sales_chart_data()
        elif self.widget_type == 'orders_count':
            return self._get_orders_count_data()
        elif self.widget_type == 'top_products':
            return self._get_top_products_data()
        # Add more widget types as needed
        
        return {}
    
    def _get_sales_chart_data(self):
        """Get sales data for chart"""
        # Get date range based on period
        end_date = timezone.now().date()
        if self.data_period == AnalyticsPeriod.LAST_7_DAYS:
            start_date = end_date - timedelta(days=7)
        elif self.data_period == AnalyticsPeriod.LAST_30_DAYS:
            start_date = end_date - timedelta(days=30)
        else:
            start_date = end_date - timedelta(days=7)  # Default
        
        # Get analytics data
        analytics_data = StoreAnalytics.objects.filter(
            store=self.store,
            date__range=[start_date, end_date]
        ).values('date', 'total_sales').order_by('date')
        
        return {
            'labels': [item['date'].strftime('%Y-%m-%d') for item in analytics_data],
            'values': [float(item['total_sales']) for item in analytics_data],
            'type': 'line',
            'title': 'فروش روزانه'
        }
    
    def _get_orders_count_data(self):
        """Get orders count data"""
        from apps.orders.models import Order
        
        # Calculate for the selected period
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=30)  # Default to 30 days
        
        total_orders = Order.objects.filter(
            store=self.store,
            created_at__date__range=[start_date, end_date]
        ).count()
        
        return {
            'value': total_orders,
            'title': 'تعداد سفارشات',
            'period': '30 روز گذشته'
        }
    
    def _get_top_products_data(self):
        """Get top products data"""
        from apps.orders.models import OrderItem
        
        # Get top 5 products by quantity sold
        top_products = OrderItem.objects.filter(
            order__store=self.store,
            order__created_at__gte=timezone.now() - timedelta(days=30)
        ).values(
            'product__name_fa'
        ).annotate(
            total_quantity=Sum('quantity')
        ).order_by('-total_quantity')[:5]
        
        return {
            'products': list(top_products),
            'title': 'محصولات پرفروش'
        }


class ReportTemplate(StoreOwnedMixin, TimestampMixin):
    """
    Custom report templates for stores
    """
    
    REPORT_TYPES = [
        ('sales', 'گزارش فروش'),
        ('inventory', 'گزارش موجودی'),
        ('customers', 'گزارش مشتریان'),
        ('traffic', 'گزارش ترافیک'),
        ('financial', 'گزارش مالی'),
        ('custom', 'گزارش سفارشی'),
    ]
    
    OUTPUT_FORMATS = [
        ('pdf', 'PDF'),
        ('excel', 'Excel'),
        ('csv', 'CSV'),
        ('json', 'JSON'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Template info
    name = models.CharField(max_length=200, verbose_name='نام گزارش')
    description = models.TextField(blank=True, verbose_name='توضیحات')
    report_type = models.CharField(max_length=20, choices=REPORT_TYPES, verbose_name='نوع گزارش')
    
    # Configuration
    fields = models.JSONField(default=list, verbose_name='فیلدهای گزارش')
    filters = models.JSONField(default=dict, verbose_name='فیلترهای پیش‌فرض')
    sorting = models.JSONField(default=dict, verbose_name='ترتیب')
    
    # Scheduling
    is_scheduled = models.BooleanField(default=False, verbose_name='زمان‌بندی شده')
    schedule_frequency = models.CharField(
        max_length=20,
        choices=[
            ('daily', 'روزانه'),
            ('weekly', 'هفتگی'),
            ('monthly', 'ماهانه'),
        ],
        blank=True,
        verbose_name='فرکانس ارسال'
    )
    
    # Output
    output_format = models.CharField(
        max_length=10, 
        choices=OUTPUT_FORMATS, 
        default='pdf',
        verbose_name='فرمت خروجی'
    )
    
    email_recipients = models.JSONField(
        default=list, 
        blank=True,
        verbose_name='گیرندگان ایمیل'
    )
    
    # Status
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    last_generated = models.DateTimeField(null=True, blank=True, verbose_name='آخرین تولید')
    
    class Meta:
        verbose_name = 'قالب گزارش'
        verbose_name_plural = 'قالب‌های گزارش'
        ordering = ['name']
        indexes = [
            models.Index(fields=['store', 'report_type']),
            models.Index(fields=['is_scheduled', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.get_report_type_display()}"


# Signal handlers for real-time analytics updates
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

@receiver([post_save], sender='orders.Order')
def update_analytics_on_order_change(sender, instance, created, **kwargs):
    """Update analytics when order changes"""
    if created:
        # Update today's analytics
        analytics, _ = StoreAnalytics.objects.get_or_create(
            store=instance.store,
            date=timezone.now().date()
        )
        
        if instance.status in ['completed', 'delivered']:
            analytics.total_sales = F('total_sales') + instance.total_amount
            analytics.orders_count = F('orders_count') + 1
            analytics.save()

@receiver([post_save], sender='stores.Customer')
def update_customer_analytics(sender, instance, created, **kwargs):
    """Update customer analytics"""
    if created:
        analytics, _ = StoreAnalytics.objects.get_or_create(
            store=instance.store,
            date=timezone.now().date()
        )
        analytics.new_customers = F('new_customers') + 1
        analytics.save()
