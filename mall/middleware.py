# Custom middleware for Mall platform
# Implements the missing middleware components referenced in settings

from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse, HttpResponse
from django.core.cache import cache
from django.conf import settings
from django.utils import timezone
from django.contrib.auth import get_user_model
import json
import logging
import time

logger = logging.getLogger(__name__)
User = get_user_model()

class StoreContextMiddleware(MiddlewareMixin):
    """
    Add store context to requests for multi-tenant support
    Works with django-tenants to provide store-specific context
    """
    
    def process_request(self, request):
        # Add store context if tenant is available
        if hasattr(request, 'tenant') and request.tenant:
            request.store = request.tenant
            request.store_context = {
                'store_id': request.tenant.id,
                'store_name': request.tenant.name,
                'store_domain': request.get_host(),
                'is_trial': getattr(request.tenant, 'on_trial', False),
                'plan_type': getattr(request.tenant, 'business_type', 'other'),
            }
        else:
            request.store = None
            request.store_context = None
        
        return None
    
    def process_response(self, request, response):
        # Add store context headers for debugging
        if hasattr(request, 'store_context') and request.store_context:
            if settings.DEBUG:
                response['X-Store-ID'] = request.store_context['store_id']
                response['X-Store-Name'] = request.store_context['store_name']
        
        return response

class RateLimitMiddleware(MiddlewareMixin):
    """
    Simple rate limiting middleware for API endpoints
    Prevents abuse and ensures fair usage
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.rate_limits = {
            '/api/auth/': {'requests': 10, 'window': 300},  # 10 requests per 5 minutes
            '/api/otp/': {'requests': 5, 'window': 300},    # 5 OTP requests per 5 minutes
            '/api/': {'requests': 1000, 'window': 3600},    # 1000 API requests per hour
        }
    
    def __call__(self, request):
        # Check rate limits before processing request
        if self.is_rate_limited(request):
            return JsonResponse({
                'error': 'Rate limit exceeded',
                'message': 'درخواست‌های زیاد. لطفاً کمی صبر کنید.',
                'retry_after': 300
            }, status=429)
        
        response = self.get_response(request)
        return response
    
    def is_rate_limited(self, request):
        """Check if request should be rate limited"""
        client_ip = self.get_client_ip(request)
        user_id = getattr(request.user, 'id', None) if request.user.is_authenticated else None
        
        # Create rate limit key
        identifier = user_id if user_id else client_ip
        
        for path_prefix, limits in self.rate_limits.items():
            if request.path.startswith(path_prefix):
                cache_key = f"rate_limit:{path_prefix}:{identifier}"
                
                current_requests = cache.get(cache_key, 0)
                
                if current_requests >= limits['requests']:
                    return True
                
                # Increment counter
                cache.set(cache_key, current_requests + 1, limits['window'])
                break
        
        return False
    
    def get_client_ip(self, request):
        """Get client IP address from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

class SecurityMiddleware(MiddlewareMixin):
    """
    Enhanced security middleware for additional protection
    """
    
    def process_request(self, request):
        # Log suspicious activity
        if self.is_suspicious_request(request):
            logger.warning(f"Suspicious request from {self.get_client_ip(request)}: {request.path}")
        
        return None
    
    def process_response(self, request, response):
        # Add security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'  
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # Add CSP header for admin pages
        if request.path.startswith('/admin/'):
            response['Content-Security-Policy'] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self' https:;"
            )
        
        return response
    
    def is_suspicious_request(self, request):
        """Detect potentially suspicious requests"""
        suspicious_patterns = [
            'admin/admin',
            'wp-admin',
            'phpmyadmin',
            '.php',
            '.asp',
            '.jsp',
            'sql',
            'union select',
            'script>',
            'javascript:',
        ]
        
        path_lower = request.path.lower()
        query_lower = request.META.get('QUERY_STRING', '').lower()
        
        for pattern in suspicious_patterns:
            if pattern in path_lower or pattern in query_lower:
                return True
        
        return False
    
    def get_client_ip(self, request):
        """Get client IP address from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

class RequestLoggingMiddleware(MiddlewareMixin):
    """
    Log requests for analytics and debugging
    """
    
    def process_request(self, request):
        request.start_time = time.time()
        return None
    
    def process_response(self, request, response):
        # Calculate request duration
        duration = time.time() - getattr(request, 'start_time', time.time())
        
        # Log API requests
        if request.path.startswith('/api/'):
            log_data = {
                'method': request.method,
                'path': request.path,
                'status': response.status_code,
                'duration': round(duration * 1000, 2),  # milliseconds
                'user': str(request.user) if request.user.is_authenticated else 'Anonymous',
                'ip': self.get_client_ip(request),
                'user_agent': request.META.get('HTTP_USER_AGENT', '')[:200],
            }
            
            # Add store context if available
            if hasattr(request, 'store_context') and request.store_context:
                log_data['store_id'] = request.store_context['store_id']
                log_data['store_name'] = request.store_context['store_name']
            
            # Log slow requests as warnings
            if duration > 2.0:  # 2 seconds
                logger.warning(f"Slow request: {json.dumps(log_data)}")
            elif response.status_code >= 400:
                logger.error(f"Error request: {json.dumps(log_data)}")
            else:
                logger.info(f"API request: {json.dumps(log_data)}")
        
        return response
    
    def get_client_ip(self, request):
        """Get client IP address from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
