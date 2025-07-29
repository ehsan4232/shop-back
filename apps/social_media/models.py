from django.db import models
from django.utils import timezone
from django.core.files.base import ContentFile
import uuid
import requests
import json

class SocialMediaAccount(models.Model):
    """Social media account connections for stores"""
    PLATFORM_CHOICES = [
        ('telegram', 'تلگرام'),
        ('instagram', 'اینستاگرام'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'فعال'),
        ('inactive', 'غیرفعال'),
        ('error', 'خطا'),
        ('expired', 'منقضی شده'),
    ]
    
    store = models.ForeignKey('stores.Store', on_delete=models.CASCADE, related_name='social_accounts')
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES, verbose_name='پلتفرم')
    
    # Account information
    username = models.CharField(max_length=100, verbose_name='نام کاربری')
    display_name = models.CharField(max_length=200, blank=True, verbose_name='نام نمایشی')
    account_id = models.CharField(max_length=100, blank=True, verbose_name='شناسه اکانت')
    
    # Authentication
    access_token = models.TextField(blank=True, verbose_name='توکن دسترسی')
    refresh_token = models.TextField(blank=True, verbose_name='توکن تازه‌سازی')
    token_expires_at = models.DateTimeField(null=True, blank=True, verbose_name='انقضای توکن')
    
    # Status and settings
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active', verbose_name='وضعیت')
    is_auto_import = models.BooleanField(default=False, verbose_name='وارد کردن خودکار')
    last_import = models.DateTimeField(null=True, blank=True, verbose_name='آخرین واردات')
    
    # Configuration
    import_settings = models.JSONField(
        default=dict,
        verbose_name='تنظیمات واردات',
        help_text='تنظیمات مربوط به واردات محتوا'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['store', 'platform', 'username']
        verbose_name = 'اکانت شبکه اجتماعی'
        verbose_name_plural = 'اکانت‌های شبکه‌های اجتماعی'
        indexes = [
            models.Index(fields=['store', 'platform']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.store.name_fa} - {self.get_platform_display()} (@{self.username})"
    
    def is_token_valid(self):
        """Check if access token is still valid"""
        if not self.access_token:
            return False
        
        if self.token_expires_at and timezone.now() > self.token_expires_at:
            return False
        
        return True
    
    def refresh_access_token(self):
        """Refresh access token if possible"""
        if self.platform == 'instagram' and self.refresh_token:
            # Implement Instagram token refresh
            return self.refresh_instagram_token()
        
        return False
    
    def refresh_instagram_token(self):
        """Refresh Instagram access token"""
        try:
            url = 'https://graph.instagram.com/refresh_access_token'
            params = {
                'grant_type': 'ig_refresh_token',
                'access_token': self.access_token
            }
            
            response = requests.get(url, params=params)
            data = response.json()
            
            if 'access_token' in data:
                self.access_token = data['access_token']
                if 'expires_in' in data:
                    self.token_expires_at = timezone.now() + timezone.timedelta(seconds=data['expires_in'])
                self.status = 'active'
                self.save()
                return True
        
        except Exception as e:
            self.status = 'error'
            self.save()
        
        return False
    
    def import_recent_posts(self, limit=5):
        """Import recent posts from social media"""
        if self.platform == 'telegram':
            return self.import_telegram_posts(limit)
        elif self.platform == 'instagram':
            return self.import_instagram_posts(limit)
        
        return []
    
    def import_telegram_posts(self, limit=5):
        """Import posts from Telegram channel"""
        # This would require Telegram Bot API integration
        # For now, return empty list
        return []
    
    def import_instagram_posts(self, limit=5):
        """Import posts from Instagram"""
        if not self.is_token_valid():
            if not self.refresh_access_token():
                return []
        
        try:
            url = f'https://graph.instagram.com/{self.account_id}/media'
            params = {
                'fields': 'id,caption,media_type,media_url,thumbnail_url,timestamp,permalink',
                'limit': limit,
                'access_token': self.access_token
            }
            
            response = requests.get(url, params=params)
            data = response.json()
            
            posts = []
            if 'data' in data:
                for post_data in data['data']:
                    post = self.create_social_post_from_instagram(post_data)
                    if post:
                        posts.append(post)
            
            self.last_import = timezone.now()
            self.save()
            
            return posts
        
        except Exception as e:
            self.status = 'error'
            self.save()
            return []
    
    def create_social_post_from_instagram(self, post_data):
        """Create SocialMediaPost from Instagram data"""
        try:
            post = SocialMediaPost.objects.create(
                account=self,
                platform_post_id=post_data['id'],
                content=post_data.get('caption', ''),
                media_url=post_data.get('media_url', ''),
                thumbnail_url=post_data.get('thumbnail_url', ''),
                post_type=post_data.get('media_type', '').lower(),
                permalink=post_data.get('permalink', ''),
                posted_at=timezone.datetime.fromisoformat(post_data['timestamp'].replace('Z', '+00:00')),
                raw_data=post_data
            )
            
            # Download and save media
            if post_data.get('media_url'):
                post.download_media()
            
            return post
        
        except Exception:
            return None

class SocialMediaPost(models.Model):
    """Imported social media posts"""
    POST_TYPES = [
        ('image', 'تصویر'),
        ('video', 'ویدیو'),
        ('carousel_album', 'آلبوم'),
        ('text', 'متن'),
    ]
    
    IMPORT_STATUS = [
        ('imported', 'وارد شده'),
        ('processed', 'پردازش شده'),
        ('converted', 'تبدیل شده به محصول'),
        ('ignored', 'نادیده گرفته شده'),
    ]
    
    account = models.ForeignKey(SocialMediaAccount, on_delete=models.CASCADE, related_name='posts')
    
    # Post information
    platform_post_id = models.CharField(max_length=100, verbose_name='شناسه پست')
    content = models.TextField(blank=True, verbose_name='محتوا')
    post_type = models.CharField(max_length=20, choices=POST_TYPES, default='text', verbose_name='نوع پست')
    
    # Media
    media_url = models.URLField(blank=True, verbose_name='لینک رسانه')
    thumbnail_url = models.URLField(blank=True, verbose_name='لینک تصویر کوچک')
    local_media = models.FileField(upload_to='social_media/', null=True, blank=True, verbose_name='رسانه محلی')
    
    # Metadata
    permalink = models.URLField(blank=True, verbose_name='لینک پست')
    posted_at = models.DateTimeField(verbose_name='تاریخ انتشار')
    
    # Import information
    status = models.CharField(max_length=20, choices=IMPORT_STATUS, default='imported', verbose_name='وضعیت واردات')
    created_product = models.ForeignKey(
        'products.Product',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='source_posts',
        verbose_name='محصول ایجاد شده'
    )
    
    # Raw data from API
    raw_data = models.JSONField(default=dict, verbose_name='داده‌های خام')
    
    # Processing results
    extracted_text = models.TextField(blank=True, verbose_name='متن استخراج شده')
    detected_products = models.JSONField(default=list, verbose_name='محصولات تشخیص داده شده')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['account', 'platform_post_id']
        ordering = ['-posted_at']
        verbose_name = 'پست شبکه اجتماعی'
        verbose_name_plural = 'پست‌های شبکه‌های اجتماعی'
        indexes = [
            models.Index(fields=['account', '-posted_at']),
            models.Index(fields=['status']),
            models.Index(fields=['post_type']),
        ]
    
    def __str__(self):
        content_preview = self.content[:50] + '...' if len(self.content) > 50 else self.content
        return f"{self.account.username} - {content_preview}"
    
    def download_media(self):
        """Download and save media file locally"""
        if not self.media_url:
            return False
        
        try:
            response = requests.get(self.media_url, timeout=30)
            if response.status_code == 200:
                # Generate filename
                file_extension = self.media_url.split('.')[-1].split('?')[0]
                if not file_extension or len(file_extension) > 4:
                    file_extension = 'jpg' if self.post_type == 'image' else 'mp4'
                
                filename = f"{self.account.platform}_{self.platform_post_id}.{file_extension}"
                
                # Save file
                self.local_media.save(
                    filename,
                    ContentFile(response.content),
                    save=True
                )
                
                return True
        
        except Exception:
            pass
        
        return False
    
    def extract_product_info(self):
        """Extract product information from post content"""
        # Simple product detection based on keywords
        content = self.content.lower()
        
        # Look for price patterns
        import re
        price_patterns = [
            r'(\d+(?:,\d{3})*)\s*(?:تومان|ریال|درهم)',
            r'قیمت[:\s]*(\d+(?:,\d{3})*)',
            r'(\d+(?:,\d{3})*)\s*تومان',
        ]
        
        prices = []
        for pattern in price_patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                try:
                    price = int(match.replace(',', ''))
                    prices.append(price)
                except:
                    pass
        
        # Look for size/color information
        size_keywords = ['سایز', 'اندازه', 'small', 'medium', 'large', 'xl', 'xxl']
        color_keywords = ['رنگ', 'آبی', 'قرمز', 'سفید', 'مشکی', 'زرد', 'سبز']
        
        detected_info = {
            'prices': prices,
            'has_size_info': any(keyword in content for keyword in size_keywords),
            'has_color_info': any(keyword in content for keyword in color_keywords),
            'text_length': len(self.content),
            'has_media': bool(self.media_url or self.local_media),
        }
        
        self.detected_products = [detected_info]
        self.extracted_text = self.content
        self.save()
        
        return detected_info
    
    def convert_to_product(self, category, additional_data=None):
        """Convert social media post to product"""
        if self.created_product:
            return self.created_product
        
        # Extract product info if not done
        if not self.detected_products:
            self.extract_product_info()
        
        # Create product
        from apps.products.models import Product
        
        product_data = {
            'store': self.account.store,
            'category': category,
            'name': self.content[:100] if self.content else f"محصول از {self.account.username}",
            'name_fa': self.content[:100] if self.content else f"محصول از {self.account.username}",
            'description': self.content,
            'imported_from_social': True,
            'social_media_source': self.account.platform,
            'social_media_post_id': self.platform_post_id,
        }
        
        # Set price if detected
        if self.detected_products and self.detected_products[0].get('prices'):
            product_data['base_price'] = self.detected_products[0]['prices'][0]
        else:
            product_data['base_price'] = 0  # Will need manual pricing
        
        # Add additional data
        if additional_data:
            product_data.update(additional_data)
        
        product = Product.objects.create(**product_data)
        
        # Add media if available
        if self.local_media:
            from apps.products.models import ProductImage
            ProductImage.objects.create(
                product=product,
                image=self.local_media,
                is_featured=True,
                imported_from_social=True,
                social_media_url=self.permalink
            )
        
        # Update status
        self.created_product = product
        self.status = 'converted'
        self.save()
        
        return product

class SocialMediaImportJob(models.Model):
    """Background jobs for importing social media content"""
    JOB_TYPES = [
        ('manual', 'دستی'),
        ('scheduled', 'زمان‌بندی شده'),
        ('auto', 'خودکار'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'در انتظار'),
        ('running', 'در حال اجرا'),
        ('completed', 'تکمیل شده'),
        ('failed', 'ناموفق'),
        ('cancelled', 'لغو شده'),
    ]
    
    account = models.ForeignKey(SocialMediaAccount, on_delete=models.CASCADE, related_name='import_jobs')
    job_type = models.CharField(max_length=20, choices=JOB_TYPES, default='manual', verbose_name='نوع کار')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='وضعیت')
    
    # Job parameters
    limit = models.PositiveIntegerField(default=10, verbose_name='تعداد پست')
    filters = models.JSONField(default=dict, verbose_name='فیلترها')
    
    # Results
    total_posts = models.PositiveIntegerField(default=0, verbose_name='کل پست‌ها')
    imported_posts = models.PositiveIntegerField(default=0, verbose_name='پست‌های وارد شده')
    error_message = models.TextField(blank=True, verbose_name='پیام خطا')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'کار واردات شبکه اجتماعی'
        verbose_name_plural = 'کارهای واردات شبکه‌های اجتماعی'
    
    def __str__(self):
        return f"واردات {self.account.username} - {self.get_status_display()}"
    
    def execute(self):
        """Execute the import job"""
        self.status = 'running'
        self.started_at = timezone.now()
        self.save()
        
        try:
            posts = self.account.import_recent_posts(self.limit)
            self.imported_posts = len(posts)
            self.total_posts = len(posts)
            self.status = 'completed'
            
        except Exception as e:
            self.status = 'failed'
            self.error_message = str(e)
        
        self.completed_at = timezone.now()
        self.save()

# Celery tasks for background processing
try:
    from celery import shared_task
    
    @shared_task
    def import_social_media_posts(account_id, limit=10):
        """Celery task to import social media posts"""
        try:
            account = SocialMediaAccount.objects.get(id=account_id)
            posts = account.import_recent_posts(limit)
            return {
                'success': True,
                'imported_count': len(posts),
                'account': account.username
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    @shared_task
    def auto_import_all_accounts():
        """Auto import from all accounts with auto_import enabled"""
        accounts = SocialMediaAccount.objects.filter(
            is_auto_import=True,
            status='active'
        )
        
        results = []
        for account in accounts:
            try:
                posts = account.import_recent_posts(5)  # Import 5 recent posts
                results.append({
                    'account': account.username,
                    'imported': len(posts),
                    'success': True
                })
            except Exception as e:
                results.append({
                    'account': account.username,
                    'error': str(e),
                    'success': False
                })
        
        return results

except ImportError:
    # Celery not available
    pass
