from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from datetime import timedelta
import random
import string

class User(AbstractUser):
    phone_number = models.CharField(max_length=15, unique=True)
    is_store_owner = models.BooleanField(default=False)
    is_customer = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = ['username']
    
    def __str__(self):
        return self.phone_number

class OTPVerification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    phone_number = models.CharField(max_length=15)
    otp_code = models.CharField(max_length=6)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    
    class Meta:
        ordering = ['-created_at']
    
    def save(self, *args, **kwargs):
        if not self.otp_code:
            self.otp_code = self.generate_otp()
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(minutes=5)
        super().save(*args, **kwargs)
    
    def generate_otp(self):
        return ''.join(random.choices(string.digits, k=6))
    
    def is_expired(self):
        return timezone.now() > self.expires_at
    
    def __str__(self):
        return f'{self.phone_number} - {self.otp_code}'