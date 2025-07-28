"""
Multi-tenant middleware for Store detection based on subdomain/domain
"""
from django.http import Http404
from django.utils.cache import patch_cache_control
from django.conf import settings
import re


class TenantMiddleware:
    """
    Middleware to detect the current store based on subdomain or custom domain
    Sets request.store for use in views and other middleware
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Skip tenant detection for admin and API endpoints
        if self.is_admin_or_api_request(request):
            request.store = None
        else:
            request.store = self.get_store_from_request(request)
        
        response = self.get_response(request)
        
        # Add store-specific cache headers
        if hasattr(request, 'store') and request.store:
            patch_cache_control(response, public=True, max_age=300)
            response['X-Store-ID'] = str(request.store.id)
        
        return response
    
    def is_admin_or_api_request(self, request):
        """Check if request is for admin or API endpoints"""
        path = request.path
        return (
            path.startswith('/admin/') or 
            path.startswith('/api/') or
            path.startswith('/static/') or
            path.startswith('/media/')
        )
    
    def get_store_from_request(self, request):
        """Extract store from subdomain or custom domain"""
        from apps.stores.models import Store
        
        host = request.get_host().lower()
        
        # Remove port if present
        if ':' in host:
            host = host.split(':')[0]
        
        # Try custom domain first
        try:
            store = Store.objects.select_related('theme', 'settings').get(
                domain=host,
                is_active=True
            )
            return store
        except Store.DoesNotExist:
            pass
        
        # Try subdomain
        if host.endswith('.mall.ir'):
            subdomain = host.replace('.mall.ir', '')
            
            # Skip www subdomain
            if subdomain == 'www':
                return None
                
            try:
                store = Store.objects.select_related('theme', 'settings').get(
                    subdomain=subdomain,
                    is_active=True
                )
                return store
            except Store.DoesNotExist:
                pass
        
        return None


class StoreRequiredMiddleware:
    """
    Middleware to ensure store is required for store-specific views
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Check if store is required for this path
        if self.store_required(request) and not getattr(request, 'store', None):
            raise Http404("Store not found")
        
        return self.get_response(request)
    
    def store_required(self, request):
        """Check if store is required for this path"""
        path = request.path
        
        # Store is required for all paths except admin, API, and static files
        return not (
            path.startswith('/admin/') or 
            path.startswith('/api/') or
            path.startswith('/static/') or
            path.startswith('/media/') or
            path == '/' or  # Landing page
            path.startswith('/auth/')
        )


class StoreContextMiddleware:
    """
    Add store context to templates and API responses
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # Add store context to API responses
        if (hasattr(request, 'store') and request.store and 
            hasattr(response, 'data') and isinstance(response.data, dict)):
            
            # Add store info to API responses if not already present
            if 'store' not in response.data:
                response.data['store'] = {
                    'id': str(request.store.id),
                    'name': request.store.name_fa,
                    'slug': request.store.slug,
                    'domain': request.store.full_domain,
                    'currency': getattr(request.store.settings, 'currency', 'تومان') if hasattr(request.store, 'settings') else 'تومان'
                }
        
        return response


class CorsMiddleware:
    """
    Custom CORS middleware for multi-tenant architecture
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # Get allowed origins based on store
        allowed_origins = self.get_allowed_origins(request)
        
        origin = request.META.get('HTTP_ORIGIN')
        if origin in allowed_origins:
            response['Access-Control-Allow-Origin'] = origin
            response['Access-Control-Allow-Credentials'] = 'true'
            response['Access-Control-Allow-Methods'] = 'GET, POST, PUT, PATCH, DELETE, OPTIONS'
            response['Access-Control-Allow-Headers'] = (
                'Accept, Accept-Language, Content-Language, Content-Type, '
                'Authorization, X-Store-ID, X-Requested-With'
            )
        
        return response
    
    def get_allowed_origins(self, request):
        """Get allowed CORS origins for the current store"""
        origins = [
            'http://localhost:3000',
            'http://127.0.0.1:3000',
            'https://mall.ir',
            'https://www.mall.ir'
        ]
        
        # Add store-specific origins
        if hasattr(request, 'store') and request.store:
            origins.extend([
                f'https://{request.store.subdomain}.mall.ir',
                f'http://{request.store.subdomain}.mall.ir'  # For development
            ])
            
            if request.store.domain:
                origins.extend([
                    f'https://{request.store.domain}',
                    f'http://{request.store.domain}'  # For development
                ])
        
        return origins


class SecurityMiddleware:
    """
    Security middleware for production environments
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # Add security headers
        if not settings.DEBUG:
            response['X-Content-Type-Options'] = 'nosniff'
            response['X-Frame-Options'] = 'DENY'
            response['X-XSS-Protection'] = '1; mode=block'
            response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
            
            # HSTS for HTTPS
            if request.is_secure():
                response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
        
        return response


class RequestLoggingMiddleware:
    """
    Middleware to log requests for analytics
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Log request for analytics (implement as needed)
        if hasattr(request, 'store') and request.store:
            # You can implement analytics logging here
            # Example: track page views, user agents, etc.
            pass
        
        return self.get_response(request)
