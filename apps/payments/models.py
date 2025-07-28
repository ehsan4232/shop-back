from django.db import models
from django.conf import settings
import uuid

class PaymentGateway(models.Model):
    """
    Payment gateway configuration for Iranian providers
    """
    GATEWAY_CHOICES = [
        ('zarinpal', 'زرین‌پال'),
        ('parsian', 'پارسیان'),
        ('mellat', 'ملت'),
        ('saman', 'سامان'),
        ('pasargad', 'پاسارگاد'),
    ]
    
    store = models.ForeignKey('stores.Store', on_delete=models.CASCADE, related_name='payment_gateways')
    gateway = models.CharField(max_length=20, choices=GATEWAY_CHOICES, verbose_name='درگاه')
    merchant_id = models.CharField(max_length=100, verbose_name='شناسه پذیرنده')
    api_key = models.CharField(max_length=200, blank=True, verbose_name='کلید API')
    terminal_id = models.CharField(max_length=100, blank=True, verbose_name='شناسه ترمینال')
    username = models.CharField(max_length=100, blank=True, verbose_name='نام کاربری')
    password = models.CharField(max_length=100, blank=True, verbose_name='رمز عبور')
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    is_sandbox = models.BooleanField(default=True, verbose_name='حالت آزمایشی')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['store', 'gateway']
        verbose_name = 'درگاه پرداخت'
        verbose_name_plural = 'درگاه‌های پرداخت'
    
    def __str__(self):
        return f'{self.store.name_fa} - {self.get_gateway_display()}'

class Payment(models.Model):
    """
    Payment transactions
    """
    STATUS_CHOICES = [
        ('pending', 'در انتظار'),
        ('processing', 'در حال پردازش'),
        ('success', 'موفق'),
        ('failed', 'ناموفق'),
        ('cancelled', 'لغو شده'),
        ('refunded', 'بازپرداخت'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey('orders.Order', on_delete=models.CASCADE, related_name='payments')
    gateway = models.ForeignKey(PaymentGateway, on_delete=models.CASCADE)
    
    amount = models.DecimalField(max_digits=12, decimal_places=0, verbose_name='مبلغ (تومان)')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='وضعیت')
    
    # Gateway specific fields
    transaction_id = models.CharField(max_length=100, blank=True, verbose_name='شناسه تراکنش')
    authority = models.CharField(max_length=100, blank=True, verbose_name='کد مجوز')
    reference_id = models.CharField(max_length=100, blank=True, verbose_name='شناسه پیگیری')
    tracking_code = models.CharField(max_length=100, blank=True, verbose_name='کد پیگیری')
    
    # Gateway response
    gateway_response = models.JSONField(default=dict, blank=True, verbose_name='پاسخ درگاه')
    error_message = models.TextField(blank=True, verbose_name='پیام خطا')
    
    # Timing
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True, verbose_name='زمان پرداخت')
    verified_at = models.DateTimeField(null=True, blank=True, verbose_name='زمان تایید')
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'پرداخت'
        verbose_name_plural = 'پرداخت‌ها'
    
    def __str__(self):
        return f'پرداخت {self.order.order_number} - {self.amount:,} تومان'

class Refund(models.Model):
    """
    Payment refunds
    """
    STATUS_CHOICES = [
        ('pending', 'در انتظار'),
        ('processing', 'در حال پردازش'),
        ('completed', 'تکمیل شده'),
        ('failed', 'ناموفق'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='refunds')
    amount = models.DecimalField(max_digits=12, decimal_places=0, verbose_name='مبلغ بازپرداخت')
    reason = models.TextField(verbose_name='دلیل بازپرداخت')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='وضعیت')
    
    # Gateway fields
    refund_id = models.CharField(max_length=100, blank=True, verbose_name='شناسه بازپرداخت')
    gateway_response = models.JSONField(default=dict, blank=True, verbose_name='پاسخ درگاه')
    
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True, verbose_name='زمان پردازش')
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'بازپرداخت'
        verbose_name_plural = 'بازپرداخت‌ها'
    
    def __str__(self):
        return f'بازپرداخت {self.payment.order.order_number} - {self.amount:,} تومان'
