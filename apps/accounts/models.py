from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import RegexValidator
from django.utils import timezone
from datetime import timedelta
import random
import string
import uuid

class User(AbstractUser):
    """
    Simple user model focused on product requirements:
    - Phone-based OTP authentication only
    - Store owner or customer roles
    - Basic profile information
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Phone as username for OTP auth (product requirement)
    username = models.CharField(
        max_length=15, 
        unique=True, 
        validators=[
            RegexValidator(
                regex=r'^(\+98|0)?9\d{9}$',
                message='شماره تلفن معتبر وارد کنید (مثال: 09123456789)'
            )
        ],
        verbose_name='شماره تلفن'
    )
    
    # Basic info only
    first_name = models.CharField(max_length=150, blank=True, verbose_name='نام')
    last_name = models.CharField(max_length=150, blank=True, verbose_name='نام خانوادگی')
    email = models.EmailField(blank=True, verbose_name='ایمیل')
    
    # Simple roles (product requirement)
    is_store_owner = models.BooleanField(default=False, verbose_name='مالک فروشگاه')
    is_verified = models.BooleanField(default=False, verbose_name='تأیید شده')
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['first_name']
    
    class Meta:
        verbose_name = 'کاربر'
        verbose_name_plural = 'کاربران'
        indexes = [
            models.Index(fields=['username']),
            models.Index(fields=['is_store_owner']),
        ]
    
    def __str__(self):
        return self.username
    
    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'.strip() or self.username

class OTPVerification(models.Model):
    """
    Simple OTP for login only (product requirement: "All logins in the platform are with otp")
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    phone = models.CharField(max_length=15, verbose_name='شماره تلفن')
    otp_code = models.CharField(max_length=6, verbose_name='کد تأیید')
    is_used = models.BooleanField(default=False, verbose_name='استفاده شده')
    
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(verbose_name='انقضا')
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'تأیید OTP'
        verbose_name_plural = 'تأییدات OTP'
        indexes = [
            models.Index(fields=['phone', '-created_at']),
            models.Index(fields=['otp_code']),
        ]
    
    def save(self, *args, **kwargs):
        if not self.otp_code:
            self.otp_code = ''.join(random.choices(string.digits, k=4))
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(minutes=5)
        super().save(*args, **kwargs)
    
    def is_expired(self):
        return timezone.now() > self.expires_at
    
    def verify(self, entered_code):
        if self.is_expired() or self.is_used:
            return False, 'کد منقضی شده است'
        
        if self.otp_code == entered_code:
            self.is_used = True
            self.save()
            
            if self.user:
                self.user.is_verified = True
                self.user.save(update_fields=['is_verified'])
            
            return True, 'کد تأیید شد'
        else:
            return False, 'کد اشتباه است'
    
    def __str__(self):
        return f'{self.phone} - {self.otp_code}'