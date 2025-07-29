"""
Enhanced multi-tenant middleware for proper tenant and store detection
Integrates with the Tenant model for domain-based routing
"""
from django.http import Http404, HttpResponseRedirect
from django.conf import settings
from django.core.cache import cache
from django.utils.deprecation import MiddlewareMixin
from django.db import connection
from django.utils.cache import patch_cache_control
import logging

logger = logging.getLogger(__name__)

class TenantMiddleware(MiddlewareMixin):
    """
    Multi-tenant middleware for domain-based tenant resolution
    Supports both subdomain (shop.mall.ir) and custom domain (shop.com) routing
    """
    
    def process_request(self, request):
        """
        Extract tenant information from request hostname
        Set tenant context for the entire request lifecycle
        """
        hostname = self.get_hostname(request)
        
        # Skip tenant resolution for admin, API docs, and static files
        if self.should_skip_tenant_resolution(request):
            request.tenant = None
            request.store = None
            return None
        
        # Get tenant from hostname
        tenant = self.get_tenant_from_hostname(hostname)
        
        if not tenant:
            # If no tenant found and this looks like a store request, return 404
            if self.is_store_request(hostname):
                raise Http404("فروشگاه یافت نشد")
            
            # For main platform requests, continue without tenant
            request.tenant = None
            request.store = None
            return None
        
        # Check if tenant is active
        if not tenant.is_active:
            raise Http404("فروشگاه غیرفعال است")
        
        # Set tenant and store in request
        request.tenant = tenant
        request.store = getattr(tenant, 'store', None)
        
        # Validate store exists and is active
        if not request.store or not request.store.is_active:
            raise Http404("فروشگاه یافت نشد")
        
        return None
    
    def process_response(self, request, response):
        """Add tenant-specific headers and caching"""
        if hasattr(request, 'tenant') and request.tenant:
            response['X-Tenant-ID'] = str(request.tenant.id)
            if hasattr(request, 'store') and request.store:
                response['X-Store-ID'] = str(request.store.id)
                # Add store-specific cache control
                patch_cache_control(response, public=True, max_age=300)
        
        return response
    
    def get_hostname(self, request):
        """Extract clean hostname from request"""
        hostname = request.get_host()
        
        # Remove port if present
        if ':' in hostname:
            hostname = hostname.split(':')[0]
        
        return hostname.lower().strip()
    
    def should_skip_tenant_resolution(self, request):
        """
        Determine if tenant resolution should be skipped
        Skip for admin, API documentation, static files, etc.
        """
        path = request.path.lower()
        
        skip_paths = [
            '/admin/',
            '/api/docs/',
            '/api/schema/',
            '/static/',
            '/media/',
            '/health/',
            '/favicon.ico',
        ]
        
        # Skip if path starts with any skip_paths
        for skip_path in skip_paths:
            if path.startswith(skip_path):
                return True
        
        # Skip for main platform domain
        hostname = self.get_hostname(request)
        platform_domain = getattr(settings, 'PLATFORM_DOMAIN', 'mall.ir')
        
        if hostname == platform_domain or hostname == f"www.{platform_domain}":
            return True
        
        return False
    
    def is_store_request(self, hostname):
        """
        Determine if hostname indicates a store request
        """
        platform_domain = getattr(settings, 'PLATFORM_DOMAIN', 'mall.ir')
        
        # Check if it's a subdomain of platform
        if hostname.endswith(f".{platform_domain}"):
            return True
        
        # Check if it's a custom domain (not the main platform)
        if hostname != platform_domain and hostname != f"www.{platform_domain}":
            return True
        
        return False
    
    def get_tenant_from_hostname(self, hostname):
        """
        Get tenant object from hostname with caching
        """
        # Use cache to avoid database hits on every request
        cache_key = f"tenant:{hostname}"
        tenant = cache.get(cache_key)
        
        if tenant is not None:
            return tenant if tenant != 'NOT_FOUND' else None
        
        try:
            from apps.stores.models import Tenant
            
            # Try exact domain match first
            tenant = Tenant.objects.select_related('store').get(
                domain_url=hostname,
                is_active=True
            )
            
            # Cache for 5 minutes
            cache.set(cache_key, tenant, 300)
            return tenant
            
        except Tenant.DoesNotExist:
            # Cache negative result for 1 minute
            cache.set(cache_key, 'NOT_FOUND', 60)
            return None
        except Exception as e:
            logger.error(f"Error getting tenant for hostname {hostname}: {e}")
            return None


class StoreContextMiddleware(MiddlewareMixin):
    """
    Add store context to requests and responses
    """
    
    def process_request(self, request):
        """Add store context data to request"""
        if hasattr(request, 'store') and request.store:
            # Cache store settings for this request
            request.store_settings = self.get_store_settings(request.store)
        return None
    
    def process_response(self, request, response):
        """Add store context to API responses"""
        # Add store context to API responses
        if (hasattr(request, 'store') and request.store and 
            hasattr(response, 'data') and isinstance(response.data, dict)):
            
            # Add store info to API responses if not already present
            if 'store_info' not in response.data:
                response.data['store_info'] = {
                    'id': str(request.store.id),
                    'name': request.store.name_fa,
                    'slug': request.store.slug,
                    'domain': request.store.domain_url,
                    'currency': request.store.currency,
                    'theme': request.store.theme,
                    'layout': request.store.layout,
                    'colors': {
                        'primary': request.store.primary_color,
                        'secondary': request.store.secondary_color,
                    }
                }
        
        return response
    
    def get_store_settings(self, store):
        """Get cached store settings"""
        cache_key = f"store_settings:{store.id}"
        settings = cache.get(cache_key)
        
        if settings is None:
            # Get store settings from database
            store_settings = {}
            for setting in store.settings.all():
                store_settings[setting.key] = setting.get_typed_value()
            
            cache.set(cache_key, store_settings, 300)  # Cache for 5 minutes
            return store_settings
        
        return settings


class RateLimitMiddleware(MiddlewareMixin):
    """
    Rate limiting middleware for API endpoints
    """
    
    def process_request(self, request):
        """Apply rate limiting based on IP and user"""
        if not self.should_rate_limit(request):
            return None
        
        # Get client identifier
        client_id = self.get_client_identifier(request)
        
        # Check rate limit
        if self.is_rate_limited(client_id, request):
            from django.http import JsonResponse
            return JsonResponse(
                {'error': 'درخواست‌های شما بیش از حد مجاز است. لطفاً کمی صبر کنید.'},
                status=429
            )
        
        return None
    
    def should_rate_limit(self, request):
        """Determine if request should be rate limited"""
        path = request.path
        
        # Rate limit API endpoints
        rate_limit_paths = [
            '/api/',
            '/auth/',
        ]
        
        return any(path.startswith(limit_path) for limit_path in rate_limit_paths)
    
    def get_client_identifier(self, request):
        """Get client identifier for rate limiting"""
        # Use user ID if authenticated, otherwise IP address
        if hasattr(request, 'user') and request.user.is_authenticated:
            return f"user:{request.user.id}"
        else:
            return f"ip:{self.get_client_ip(request)}"
    
    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '')
    
    def is_rate_limited(self, client_id, request):
        """Check if client is rate limited"""
        # Different limits for different endpoints
        limits = {
            'default': 100,  # 100 requests per minute
            'auth': 10,      # 10 auth requests per minute
            'api_write': 30, # 30 write requests per minute
        }
        
        # Determine limit type
        if '/auth/' in request.path:
            limit_type = 'auth'
        elif request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
            limit_type = 'api_write'
        else:
            limit_type = 'default'
        
        limit = limits[limit_type]
        cache_key = f"rate_limit:{limit_type}:{client_id}"
        
        # Get current count
        current_count = cache.get(cache_key, 0)
        
        if current_count >= limit:
            return True
        
        # Increment counter
        cache.set(cache_key, current_count + 1, 60)  # 1 minute window
        return False


class SecurityMiddleware(MiddlewareMixin):
    """
    Security middleware for production environments
    """
    
    def process_response(self, request, response):
        """Add security headers"""
        # Add security headers
        if not settings.DEBUG:
            response['X-Content-Type-Options'] = 'nosniff'
            response['X-Frame-Options'] = 'SAMEORIGIN'  # Allow same origin for iframes
            response['X-XSS-Protection'] = '1; mode=block'
            response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
            
            # Content Security Policy
            csp = self.get_content_security_policy(request)
            response['Content-Security-Policy'] = csp
            
            # HSTS for HTTPS
            if request.is_secure():
                response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
        
        return response
    
    def get_content_security_policy(self, request):
        """Get Content Security Policy based on store"""
        base_csp = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdnjs.cloudflare.com",
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
            "font-src 'self' https://fonts.gstatic.com",
            "img-src 'self' data: https:",
            "connect-src 'self'",
        ]
        
        # Add store-specific domains if available
        if hasattr(request, 'store') and request.store:
            if request.store.custom_domain:
                base_csp.append(f"frame-ancestors 'self' https://{request.store.custom_domain}")
        
        return "; ".join(base_csp)


class CorsMiddleware(MiddlewareMixin):
    """
    Enhanced CORS middleware for multi-tenant architecture
    """
    
    def process_response(self, request, response):
        """Add CORS headers based on tenant configuration"""
        # Get allowed origins based on store
        allowed_origins = self.get_allowed_origins(request)
        
        origin = request.META.get('HTTP_ORIGIN')
        if origin in allowed_origins:
            response['Access-Control-Allow-Origin'] = origin
            response['Access-Control-Allow-Credentials'] = 'true'
            response['Access-Control-Allow-Methods'] = 'GET, POST, PUT, PATCH, DELETE, OPTIONS'
            response['Access-Control-Allow-Headers'] = (
                'Accept, Accept-Language, Content-Language, Content-Type, '
                'Authorization, X-Store-ID, X-Tenant-ID, X-Requested-With'
            )
            response['Access-Control-Max-Age'] = '86400'  # 24 hours
        
        return response
    
    def get_allowed_origins(self, request):
        """Get allowed CORS origins for the current store"""
        origins = [
            'http://localhost:3000',
            'http://127.0.0.1:3000',
        ]
        
        # Add platform domains
        platform_domain = getattr(settings, 'PLATFORM_DOMAIN', 'mall.ir')
        origins.extend([
            f'https://{platform_domain}',
            f'https://www.{platform_domain}',
        ])
        
        if settings.DEBUG:
            origins.extend([
                f'http://{platform_domain}',
                f'http://www.{platform_domain}',
            ])
        
        # Add store-specific origins
        if hasattr(request, 'store') and request.store:
            store_domain = request.store.domain_url
            if store_domain:
                origins.append(f'https://{store_domain}')
                if settings.DEBUG:
                    origins.append(f'http://{store_domain}')
        
        return origins


class RequestLoggingMiddleware(MiddlewareMixin):
    """
    Middleware to log requests for analytics and monitoring
    """
    
    def process_request(self, request):
        """Log request for analytics"""
        if self.should_log_request(request):
            # Implement analytics logging here
            # You can use Celery tasks for async logging
            self.log_request_async(request)
        
        return None
    
    def should_log_request(self, request):
        """Determine if request should be logged"""
        # Don't log admin, static files, or health checks
        skip_paths = ['/admin/', '/static/', '/media/', '/health/', '/favicon.ico']
        
        for skip_path in skip_paths:
            if request.path.startswith(skip_path):
                return False
        
        return True
    
    def log_request_async(self, request):
        """Log request asynchronously using Celery"""
        try:
            from apps.analytics.tasks import log_page_view
            
            # Prepare log data
            log_data = {
                'path': request.path,
                'method': request.method,
                'ip_address': self.get_client_ip(request),
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                'referer': request.META.get('HTTP_REFERER', ''),
                'store_id': str(request.store.id) if hasattr(request, 'store') and request.store else None,
                'user_id': str(request.user.id) if hasattr(request, 'user') and request.user.is_authenticated else None,
            }
            
            # Send to Celery task
            log_page_view.delay(log_data)
            
        except ImportError:
            # Analytics app not available, skip logging
            pass
        except Exception as e:
            logger.error(f"Error logging request: {e}")
    
    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '')


class MaintenanceMiddleware(MiddlewareMixin):
    """
    Maintenance mode middleware
    """
    
    def process_request(self, request):
        """Check if site is in maintenance mode"""
        # Check global maintenance mode
        if getattr(settings, 'MAINTENANCE_MODE', False):
            # Allow admin access during maintenance
            if not request.path.startswith('/admin/'):
                from django.http import HttpResponse
                return HttpResponse(
                    '<h1>سایت در حال تعمیر است</h1><p>لطفاً بعداً مراجعه کنید.</p>',
                    status=503,
                    content_type='text/html; charset=utf-8'
                )
        
        # Check store-specific maintenance mode
        if hasattr(request, 'store') and request.store:
            store_maintenance = cache.get(f"maintenance:{request.store.id}")
            if store_maintenance:
                from django.http import HttpResponse
                return HttpResponse(
                    f'<h1>فروشگاه {request.store.name_fa} در حال تعمیر است</h1><p>لطفاً بعداً مراجعه کنید.</p>',
                    status=503,
                    content_type='text/html; charset=utf-8'
                )
        
        return None
