# CRITICAL FIXES REQUIRED - IMMEDIATE ACTION NEEDED

## 🚨 PRODUCTION BLOCKING ISSUES

This document outlines critical issues that must be fixed before the Mall platform can be considered production-ready.

## 1. MULTI-TENANCY IMPLEMENTATION (CRITICAL)

### Current Problem
- No tenant isolation
- Security vulnerability: stores can access each other's data
- Domain routing impossible

### Required Implementation

Add to `requirements.txt`:
```
django-tenant-schemas==1.14.0
```

Create `apps/tenants/models.py`:
```python
from django_tenants.models import TenantMixin, DomainMixin
from django.db import models

class Tenant(TenantMixin):
    name = models.CharField(max_length=100)
    paid_until = models.DateField()
    on_trial = models.BooleanField()
    created_on = models.DateField(auto_now_add=True)

class Domain(DomainMixin):
    pass
```

Update `mall/settings.py`:
```python
SHARED_APPS = [
    'django_tenants',
    'apps.tenants',
    # ... shared apps
]

TENANT_APPS = [
    'apps.stores',
    'apps.products',
    'apps.orders',
    # ... tenant-specific apps
]

INSTALLED_APPS = list(SHARED_APPS) + [app for app in TENANT_APPS if app not in SHARED_APPS]

DATABASE_ROUTERS = [
    'django_tenants.routers.TenantSyncRouter',
]

TENANT_MODEL = "tenants.Tenant"
TENANT_DOMAIN_MODEL = "tenants.Domain"
```

## 2. FIX PRODUCT CLASS HIERARCHY (CRITICAL)

### Current Problems
- Circular dependency validation is incomplete
- Performance issues with price inheritance
- Broken leaf node validation

### Required Fix in `apps/products/models.py`:

Replace the current `ProductClass.clean()` method:
```python
def clean(self):
    """Enhanced validation for product description requirements"""
    super().clean()
    
    if self.parent and self.pk:
        # Check direct self-reference
        if self.parent == self:
            raise ValidationError({'parent': 'کلاس نمی‌تواند والد خودش باشد'})
        
        # CRITICAL FIX: Check for circular dependency in the entire chain
        parent_chain = []
        current = self.parent
        while current:
            if current.pk == self.pk:
                raise ValidationError({
                    'parent': 'انتخاب این والد باعث ایجاد حلقه در ساختار درختی می‌شود'
                })
            if current.pk in parent_chain:
                raise ValidationError({
                    'parent': 'ساختار درختی دارای حلقه است'
                })
            parent_chain.append(current.pk)
            current = current.parent
            
            # Prevent infinite loops
            if len(parent_chain) > 50:
                raise ValidationError({
                    'parent': 'عمق درخت بیش از حد مجاز است'
                })
    
    # CRITICAL: Validate leaf node product creation
    if self.pk and not self.is_leaf:
        has_products = Product.objects.filter(product_class=self).exists()
        if has_products:
            raise ValidationError({
                'is_leaf': 'کلاس‌های غیربرگ نمی‌توانند محصول داشته باشند'
            })
```

Fix price inheritance performance:
```python
def get_effective_price(self):
    """Optimized price inheritance with proper caching"""
    cache_key = f"effective_price_class_{self.id}"
    cached_price = cache.get(cache_key)
    if cached_price is not None:
        return cached_price
    
    if self.base_price:
        price = self.base_price
    else:
        # Use optimized ancestor query with select_related
        ancestor_with_price = self.get_ancestors().select_related().filter(
            base_price__isnull=False
        ).order_by('-level').first()
        price = ancestor_with_price.base_price if ancestor_with_price else 0
    
    cache.set(cache_key, price, timeout=600)  # 10 minutes
    return price
```

## 3. IMPLEMENT OTP AUTHENTICATION (HIGH PRIORITY)

### Create `apps/authentication/` app

`apps/authentication/models.py`:
```python
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
import random

class User(AbstractUser):
    phone_regex = RegexValidator(
        regex=r'^09\d{9}$',
        message="شماره تلفن باید به فرمت 09xxxxxxxxx باشد"
    )
    phone_number = models.CharField(
        validators=[phone_regex], 
        max_length=11, 
        unique=True
    )
    is_store_owner = models.BooleanField(default=False)
    is_phone_verified = models.BooleanField(default=False)
    
    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = []

class OTPCode(models.Model):
    phone_number = models.CharField(max_length=11)
    code = models.CharField(max_length=6)
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    
    def save(self, *args, **kwargs):
        if not self.code:
            self.code = str(random.randint(100000, 999999))
        super().save(*args, **kwargs)
    
    @property
    def is_expired(self):
        from django.utils import timezone
        return timezone.now() > self.expires_at
```

## 4. ADD MISSING SOCIAL MEDIA INTEGRATION (HIGH PRIORITY)

### Create `apps/social_media/services.py`:
```python
import requests
from django.conf import settings

class TelegramService:
    def __init__(self):
        self.bot_token = settings.TELEGRAM_BOT_TOKEN
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
    
    def get_channel_posts(self, channel_username, limit=5):
        """Get last 5 posts from Telegram channel"""
        # Implementation for Telegram API
        pass

class InstagramService:
    def __init__(self):
        self.access_token = settings.INSTAGRAM_ACCESS_TOKEN
    
    def get_user_media(self, user_id, limit=5):
        """Get last 5 posts from Instagram using Basic Display API"""
        url = f"https://graph.instagram.com/{user_id}/media"
        params = {
            'fields': 'id,caption,media_type,media_url,thumbnail_url',
            'access_token': self.access_token,
            'limit': limit
        }
        response = requests.get(url, params=params)
        return response.json()

class SocialMediaImporter:
    def __init__(self):
        self.telegram = TelegramService()
        self.instagram = InstagramService()
    
    def import_from_platform(self, platform, source_id):
        """Import media and text from social media platforms"""
        if platform == 'telegram':
            return self.telegram.get_channel_posts(source_id)
        elif platform == 'instagram':
            return self.instagram.get_user_media(source_id)
        else:
            raise ValueError(f"Unsupported platform: {platform}")
```

## 5. IMPLEMENT STOCK WARNING SYSTEM (MEDIUM PRIORITY)

### Backend Enhancement in `apps/products/models.py`:
```python
class Product(models.Model):
    # ... existing fields ...
    
    def get_stock_warning_data(self):
        """Get comprehensive stock warning data for frontend"""
        if self.product_type == 'simple':
            return {
                'needs_warning': self.stock_quantity <= 3,
                'stock_count': self.stock_quantity,
                'message': self.get_stock_warning_message(),
                'level': 'critical' if self.stock_quantity == 0 else 'warning'
            }
        elif self.product_type == 'variable':
            variants = self.variants.filter(is_active=True)
            low_stock_variants = variants.filter(stock_quantity__lte=3)
            
            return {
                'needs_warning': low_stock_variants.exists(),
                'variant_warnings': [
                    {
                        'variant_id': v.id,
                        'stock_count': v.stock_quantity,
                        'message': v.get_stock_warning_message(),
                        'attributes': v.get_attribute_display()
                    }
                    for v in low_stock_variants
                ],
                'level': 'critical' if variants.filter(stock_quantity=0).exists() else 'warning'
            }
        
        return {'needs_warning': False}
```

### Frontend Component (React):
```typescript
// components/StockWarning.tsx
interface StockWarningProps {
  stockData: {
    needs_warning: boolean;
    stock_count?: number;
    message?: string;
    level?: 'warning' | 'critical';
  };
}

export const StockWarning: React.FC<StockWarningProps> = ({ stockData }) => {
  if (!stockData.needs_warning) return null;
  
  const bgColor = stockData.level === 'critical' ? 'bg-red-100' : 'bg-yellow-100';
  const textColor = stockData.level === 'critical' ? 'text-red-800' : 'text-yellow-800';
  
  return (
    <div className={`p-2 rounded-md ${bgColor} ${textColor} text-sm`}>
      <span className="font-medium">⚠️ {stockData.message}</span>
    </div>
  );
};
```

## 6. DATABASE PERFORMANCE OPTIMIZATION (IMMEDIATE)

### Add Missing Indexes to `apps/products/models.py`:
```python
class Product(models.Model):
    class Meta:
        indexes = [
            # CRITICAL: Add compound indexes for common queries
            models.Index(fields=['store', 'status', '-created_at']),
            models.Index(fields=['store', 'category', 'status']),
            models.Index(fields=['store', 'brand', 'status']),
            models.Index(fields=['product_class', 'status']),
            
            # Performance indexes for filtering
            models.Index(fields=['base_price', 'status']),
            models.Index(fields=['stock_quantity', 'status']),
            models.Index(fields=['-view_count']),
            models.Index(fields=['-sales_count']),
            models.Index(fields=['-rating_average']),
            
            # Social media indexes
            models.Index(fields=['imported_from_social', 'social_media_source']),
            models.Index(fields=['last_social_import']),
        ]
```

## 7. SECURITY ENHANCEMENTS (IMMEDIATE)

### Add Rate Limiting in `mall/settings.py`:
```python
INSTALLED_APPS += ['django_ratelimit']

# Rate limiting configuration
RATELIMIT_ENABLE = True
RATELIMIT_USE_CACHE = 'default'
RATELIMIT_VIEW = 'apps.core.views.ratelimited'
```

### Create `apps/core/decorators.py`:
```python
from django_ratelimit.decorators import ratelimit
from django.http import JsonResponse

def api_ratelimit(group=None, key=None, rate=None, method='POST', block=True):
    """Custom rate limiting decorator for API endpoints"""
    def decorator(view_func):
        @ratelimit(group=group, key=key, rate=rate, method=method, block=block)
        def wrapper(request, *args, **kwargs):
            if getattr(request, 'limited', False):
                return JsonResponse({
                    'error': 'درخواست‌های زیاد. لطفا بعدا تلاش کنید.',
                    'detail': 'Rate limit exceeded'
                }, status=429)
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
```

## IMPLEMENTATION TIMELINE

### Week 1 (CRITICAL):
- [ ] Implement multi-tenancy
- [ ] Fix product class hierarchy
- [ ] Add database indexes

### Week 2 (HIGH PRIORITY):
- [ ] Implement OTP authentication
- [ ] Add social media integration base
- [ ] Implement stock warning system

### Week 3 (MEDIUM PRIORITY):
- [ ] Complete social media features
- [ ] Add comprehensive testing
- [ ] Performance optimization

## TESTING REQUIREMENTS

Each fix must include:
1. Unit tests
2. Integration tests
3. Performance tests
4. Security validation

## DEPLOYMENT NOTES

⚠️ **WARNING**: These changes require database migrations and may cause downtime. Plan accordingly.

1. Backup database before implementing
2. Test in staging environment first
3. Plan for data migration (multi-tenancy)
4. Update deployment scripts

## MONITORING

After implementing fixes, monitor:
- Database query performance
- Memory usage
- API response times
- Error rates
- Security logs

---

**Status**: 🔴 CRITICAL - Implementation required before production deployment
**Priority**: P0 - Blocking
**Estimated Effort**: 3-4 weeks full-time development
