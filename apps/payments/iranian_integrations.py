from django.db import models
from django.core.exceptions import ValidationError
from apps.core.mixins import TimestampMixin, StoreOwnedMixin
from apps.orders.models import Order
import uuid
import requests
import json
from django.conf import settings


class IranianPaymentGateway(StoreOwnedMixin, TimestampMixin):
    """
    Iranian payment gateways integration
    Product requirement: "integrated with valid big logistics providers and payment gateways in iran"
    """
    
    GATEWAY_CHOICES = [
        ('zarinpal', 'زرین‌پال'),
        ('mellat', 'ملت'),
        ('parsian', 'پارسیان'),
        ('saderat', 'صادرات'),
        ('saman', 'سامان'),
        ('pasargad', 'پاسارگاد'),
        ('ayandeh', 'آینده'),
        ('tejarat', 'تجارت'),
        ('irankish', 'ایران کیش'),
        ('sep', 'سپ'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    name = models.CharField(max_length=100, verbose_name='نام درگاه')
    gateway_type = models.CharField(max_length=20, choices=GATEWAY_CHOICES, verbose_name='نوع درگاه')
    
    # Configuration
    merchant_id = models.CharField(max_length=100, verbose_name='شناسه پذیرنده')
    terminal_id = models.CharField(max_length=50, blank=True, verbose_name='شناسه ترمینال')
    username = models.CharField(max_length=100, blank=True, verbose_name='نام کاربری')
    password = models.CharField(max_length=100, blank=True, verbose_name='رمز عبور')
    
    # Settings
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    is_sandbox = models.BooleanField(default=True, verbose_name='حالت تست')
    callback_url = models.URLField(verbose_name='آدرس بازگشت')
    
    # Transaction settings
    min_amount = models.PositiveIntegerField(default=1000, verbose_name='حداقل مبلغ (تومان)')
    max_amount = models.PositiveIntegerField(default=50000000, verbose_name='حداکثر مبلغ (تومان)')
    fee_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name='درصد کارمزد')
    
    class Meta:
        verbose_name = 'درگاه پرداخت ایرانی'
        verbose_name_plural = 'درگاه‌های پرداخت ایرانی'
        unique_together = ['store', 'gateway_type']
    
    def __str__(self):
        return f"{self.store.name_fa} - {self.get_gateway_type_display()}"
    
    def create_payment_request(self, order, amount, description=""):
        """Create payment request based on gateway type"""
        if self.gateway_type == 'zarinpal':
            return self._zarinpal_request(order, amount, description)
        elif self.gateway_type == 'mellat':
            return self._mellat_request(order, amount, description)
        elif self.gateway_type == 'parsian':
            return self._parsian_request(order, amount, description)
        # Add other gateways...
        else:
            raise NotImplementedError(f"Gateway {self.gateway_type} not implemented")
    
    def _zarinpal_request(self, order, amount, description):
        """ZarinPal payment request"""
        url = "https://sandbox.zarinpal.com/pg/rest/WebGate/PaymentRequest.json" if self.is_sandbox else "https://zarinpal.com/pg/rest/WebGate/PaymentRequest.json"
        
        data = {
            "MerchantID": self.merchant_id,
            "Amount": amount,
            "Description": description or f"پرداخت سفارش {order.order_number}",
            "CallbackURL": self.callback_url,
            "Mobile": order.customer_phone,
            "Email": order.customer_email or ""
        }
        
        try:
            response = requests.post(url, json=data, timeout=10)
            result = response.json()
            
            if result['Status'] == 100:
                return {
                    'success': True,
                    'authority': result['Authority'],
                    'payment_url': f"https://sandbox.zarinpal.com/pg/StartPay/{result['Authority']}" if self.is_sandbox else f"https://zarinpal.com/pg/StartPay/{result['Authority']}"
                }
            else:
                return {
                    'success': False,
                    'error': f"ZarinPal Error: {result.get('Status', 'Unknown error')}"
                }
        except Exception as e:
            return {
                'success': False,
                'error': f"Connection error: {str(e)}"
            }
    
    def verify_payment(self, authority, amount):
        """Verify payment based on gateway type"""
        if self.gateway_type == 'zarinpal':
            return self._zarinpal_verify(authority, amount)
        elif self.gateway_type == 'mellat':
            return self._mellat_verify(authority, amount)
        # Add other verifications...
        else:
            raise NotImplementedError(f"Verification for {self.gateway_type} not implemented")
    
    def _zarinpal_verify(self, authority, amount):
        """ZarinPal payment verification"""
        url = "https://sandbox.zarinpal.com/pg/rest/WebGate/PaymentVerification.json" if self.is_sandbox else "https://zarinpal.com/pg/rest/WebGate/PaymentVerification.json"
        
        data = {
            "MerchantID": self.merchant_id,
            "Amount": amount,
            "Authority": authority
        }
        
        try:
            response = requests.post(url, json=data, timeout=10)
            result = response.json()
            
            if result['Status'] == 100:
                return {
                    'success': True,
                    'ref_id': result['RefID'],
                    'status': 'paid'
                }
            else:
                return {
                    'success': False,
                    'error': f"Verification failed: {result.get('Status', 'Unknown error')}"
                }
        except Exception as e:
            return {
                'success': False,
                'error': f"Verification error: {str(e)}"
            }


class IranianLogisticsProvider(StoreOwnedMixin, TimestampMixin):
    """
    Iranian logistics providers integration
    Product requirement: "integrated with valid big logistics providers"
    """
    
    PROVIDER_CHOICES = [
        ('post', 'اداره پست ایران'),
        ('tipax', 'تیپاکس'),
        ('chapar', 'چاپار'),
        ('alopeyk', 'علوپیک'),
        ('miare', 'میاره'),
        ('snapp_box', 'اسنپ باکس'),
        ('digikala_jet', 'دیجیکالا جت'),
        ('mahex', 'ماهکس'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    name = models.CharField(max_length=100, verbose_name='نام ارسال‌کننده')
    provider_type = models.CharField(max_length=20, choices=PROVIDER_CHOICES, verbose_name='نوع ارسال‌کننده')
    
    # API Configuration
    api_key = models.CharField(max_length=200, verbose_name='کلید API')
    api_secret = models.CharField(max_length=200, blank=True, verbose_name='کلید مخفی')
    base_url = models.URLField(verbose_name='آدرس پایه API')
    
    # Settings
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    is_cod_supported = models.BooleanField(default=True, verbose_name='پشتیبانی پرداخت در محل')
    
    # Coverage
    coverage_cities = models.JSONField(default=list, verbose_name='شهرهای تحت پوشش')
    coverage_provinces = models.JSONField(default=list, verbose_name='استان‌های تحت پوشش')
    
    # Pricing
    base_price = models.PositiveIntegerField(default=10000, verbose_name='قیمت پایه (تومان)')
    price_per_kg = models.PositiveIntegerField(default=5000, verbose_name='قیمت هر کیلوگرم (تومان)')
    free_shipping_threshold = models.PositiveIntegerField(default=500000, verbose_name='آستانه ارسال رایگان (تومان)')
    
    # Timing
    min_delivery_days = models.PositiveIntegerField(default=1, verbose_name='حداقل روز تحویل')
    max_delivery_days = models.PositiveIntegerField(default=7, verbose_name='حداکثر روز تحویل')
    
    class Meta:
        verbose_name = 'ارسال‌کننده ایرانی'
        verbose_name_plural = 'ارسال‌کنندگان ایرانی'
        unique_together = ['store', 'provider_type']
    
    def __str__(self):
        return f"{self.store.name_fa} - {self.get_provider_type_display()}"
    
    def calculate_shipping_cost(self, weight, destination_city, order_total=0):
        """Calculate shipping cost based on weight and destination"""
        if order_total >= self.free_shipping_threshold:
            return 0
        
        if destination_city.lower() not in [city.lower() for city in self.coverage_cities]:
            return None  # Not covered
        
        cost = self.base_price + (weight * self.price_per_kg)
        return cost
    
    def create_shipment(self, order, pickup_address, delivery_address):
        """Create shipment based on provider type"""
        if self.provider_type == 'post':
            return self._post_create_shipment(order, pickup_address, delivery_address)
        elif self.provider_type == 'tipax':
            return self._tipax_create_shipment(order, pickup_address, delivery_address)
        # Add other providers...
        else:
            return {
                'success': False,
                'error': f"Provider {self.provider_type} not implemented"
            }
    
    def track_shipment(self, tracking_number):
        """Track shipment status"""
        if self.provider_type == 'post':
            return self._post_track_shipment(tracking_number)
        elif self.provider_type == 'tipax':
            return self._tipax_track_shipment(tracking_number)
        # Add other providers...
        else:
            return {
                'success': False,
                'error': f"Tracking for {self.provider_type} not implemented"
            }


class PaymentTransaction(TimestampMixin):
    """Payment transaction records"""
    
    STATUS_CHOICES = [
        ('pending', 'در انتظار'),
        ('paid', 'پرداخت شده'),
        ('failed', 'ناموفق'),
        ('cancelled', 'لغو شده'),
        ('refunded', 'برگشت داده شده'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='payment_transaction')
    gateway = models.ForeignKey(IranianPaymentGateway, on_delete=models.CASCADE)
    
    # Transaction details
    amount = models.PositiveIntegerField(verbose_name='مبلغ (تومان)')
    authority = models.CharField(max_length=100, verbose_name='کد پیگیری درگاه')
    reference_id = models.CharField(max_length=100, blank=True, verbose_name='شماره مرجع')
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Gateway response
    gateway_response = models.JSONField(default=dict, verbose_name='پاسخ درگاه')
    error_message = models.TextField(blank=True, verbose_name='پیام خطا')
    
    # Timing
    paid_at = models.DateTimeField(null=True, blank=True, verbose_name='زمان پرداخت')
    
    class Meta:
        verbose_name = 'تراکنش پرداخت'
        verbose_name_plural = 'تراکنش‌های پرداخت'
        indexes = [
            models.Index(fields=['authority']),
            models.Index(fields=['reference_id']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"تراکنش {self.order.order_number} - {self.get_status_display()}"


class ShippingOrder(TimestampMixin):
    """Shipping order records"""
    
    STATUS_CHOICES = [
        ('pending', 'در انتظار'),
        ('picked_up', 'جمع‌آوری شده'),
        ('in_transit', 'در حال ارسال'),
        ('delivered', 'تحویل داده شده'),
        ('returned', 'برگشت داده شده'),
        ('cancelled', 'لغو شده'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='shipping_order')
    logistics_provider = models.ForeignKey(IranianLogisticsProvider, on_delete=models.CASCADE)
    
    # Shipment details
    tracking_number = models.CharField(max_length=100, unique=True, verbose_name='کد رهگیری')
    weight = models.DecimalField(max_digits=6, decimal_places=2, verbose_name='وزن (کیلوگرم)')
    shipping_cost = models.PositiveIntegerField(verbose_name='هزینه ارسال (تومان)')
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Addresses
    pickup_address = models.JSONField(verbose_name='آدرس مبدا')
    delivery_address = models.JSONField(verbose_name='آدرس مقصد')
    
    # Timing
    estimated_delivery = models.DateTimeField(null=True, blank=True, verbose_name='تخمین زمان تحویل')
    delivered_at = models.DateTimeField(null=True, blank=True, verbose_name='زمان تحویل')
    
    # Provider response
    provider_response = models.JSONField(default=dict, verbose_name='پاسخ ارسال‌کننده')
    
    class Meta:
        verbose_name = 'سفارش ارسال'
        verbose_name_plural = 'سفارش‌های ارسال'
        indexes = [
            models.Index(fields=['tracking_number']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"ارسال {self.order.order_number} - {self.tracking_number}"
