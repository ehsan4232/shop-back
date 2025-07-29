from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.conf import settings
import uuid
import json

class PaymentGateway(models.Model):
    """Payment gateway configurations for stores"""
    GATEWAY_TYPES = [
        ('zarinpal', 'زرین‌پال'),
        ('mellat', 'بانک ملت'),
        ('parsian', 'بانک پارسیان'),
        ('saman', 'بانک سامان'),
        ('pasargad', 'بانک پاسارگاد'),
        ('saderat', 'بانک صادرات'),
    ]
    
    store = models.ForeignKey('stores.Store', on_delete=models.CASCADE, related_name='payment_gateways')
    gateway_type = models.CharField(max_length=20, choices=GATEWAY_TYPES, verbose_name='نوع درگاه')
    
    # Gateway credentials
    merchant_id = models.CharField(max_length=100, verbose_name='شناسه پذیرنده')
    api_key = models.CharField(max_length=255, blank=True, verbose_name='کلید API')
    secret_key = models.CharField(max_length=255, blank=True, verbose_name='کلید مخفی')
    
    # Configuration
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    is_sandbox = models.BooleanField(default=True, verbose_name='حالت تست')
    display_name = models.CharField(max_length=100, verbose_name='نام نمایشی')
    display_order = models.PositiveIntegerField(default=0, verbose_name='ترتیب نمایش')
    
    # Additional settings
    min_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=0, 
        default=1000,
        verbose_name='حداقل مبلغ'
    )
    max_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=0, 
        default=50000000,
        verbose_name='حداکثر مبلغ'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['store', 'gateway_type']
        ordering = ['display_order', 'display_name']
        verbose_name = 'درگاه پرداخت'
        verbose_name_plural = 'درگاه‌های پرداخت'
    
    def __str__(self):
        return f"{self.store.name_fa} - {self.get_gateway_type_display()}"

class Transaction(models.Model):
    """Payment transactions"""
    STATUS_CHOICES = [
        ('pending', 'در انتظار'),
        ('processing', 'در حال پردازش'),
        ('paid', 'پرداخت شده'),
        ('failed', 'ناموفق'),
        ('cancelled', 'لغو شده'),
        ('refunded', 'بازگردانده شده'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey('orders.Order', on_delete=models.CASCADE, related_name='transactions')
    gateway = models.ForeignKey(PaymentGateway, on_delete=models.CASCADE, related_name='transactions')
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='وضعیت')
    amount = models.DecimalField(max_digits=12, decimal_places=0, verbose_name='مبلغ')
    reference_id = models.CharField(max_length=100, unique=True, verbose_name='شناسه مرجع')
    gateway_transaction_id = models.CharField(max_length=100, blank=True, verbose_name='شناسه تراکنش درگاه')
    
    request_data = models.JSONField(default=dict, verbose_name='داده‌های درخواست')
    response_data = models.JSONField(default=dict, verbose_name='داده‌های پاسخ')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='آخرین به‌روزرسانی')
    paid_at = models.DateTimeField(null=True, blank=True, verbose_name='تاریخ پرداخت')
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'تراکنش'
        verbose_name_plural = 'تراکنش‌ها'
        indexes = [
            models.Index(fields=['order', '-created_at']),
            models.Index(fields=['gateway', '-created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['reference_id']),
        ]
    
    def __str__(self):
        return f"تراکنش {self.reference_id} - {self.order.order_number}"
    
    def save(self, *args, **kwargs):
        if not self.reference_id:
            self.reference_id = self.generate_reference_id()
        super().save(*args, **kwargs)
    
    def generate_reference_id(self):
        """Generate unique reference ID"""
        import random
        import string
        
        timestamp = str(int(timezone.now().timestamp()))[-8:]
        random_part = ''.join(random.choices(string.digits, k=6))
        reference_id = f"TXN{timestamp}{random_part}"
        
        while Transaction.objects.filter(reference_id=reference_id).exists():
            random_part = ''.join(random.choices(string.digits, k=6))
            reference_id = f"TXN{timestamp}{random_part}"
        
        return reference_id
