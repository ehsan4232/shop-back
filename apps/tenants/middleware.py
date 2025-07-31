# Enhanced tenant middleware for Mall platform
# Implements domain-based tenant routing with subdomain and custom domain support

from django.http import Http404, HttpResponse
from django.utils.deprecation import MiddlewareMixin
from django.shortcuts import redirect
from django.conf import settings
from django.db import connection
from django_tenants.middleware import TenantMainMiddleware
from django_tenants.utils import get_tenant_model, get_public_schema_name
from .models import Tenant, Domain
import logging

logger = logging.getLogger(__name__)

class MallTenantMiddleware(TenantMainMiddleware):
    """
    Enhanced tenant middleware for Mall platform
    Supports both subdomain and custom domain routing
    Handles tenant status validation and redirection
    """
    
    def process_request(self, request):
        # Get hostname from request
        hostname = request.get_host().split(':')[0].lower()
        
        # Handle development/admin domains
        if self.is_admin_domain(hostname):
            return self.handle_admin_domain(request)
        
        # Try to find tenant by domain
        try:
            domain = Domain.objects.select_related('tenant').get(
                domain=hostname,
                verification_status='verified'
            )
            tenant = domain.tenant
            
            # Validate tenant status
            if not self.is_tenant_accessible(tenant):
                return self.handle_inaccessible_tenant(request, tenant)
            
            # Set tenant in request
            request.tenant = tenant
            
            # Switch to tenant schema
            connection.set_tenant(tenant)
            
            # Add tenant info to request for use in views
            request.tenant_info = {
                'id': tenant.id,
                'store_name': tenant.store_name,
                'plan_type': tenant.plan_type,
                'is_trial': tenant.on_trial,
                'domain': domain.domain,
                'is_custom_domain': domain.is_custom
            }
            
            # Log successful tenant resolution
            logger.info(f"Tenant resolved: {tenant.store_name} for domain {hostname}")
            
        except Domain.DoesNotExist:
            return self.handle_domain_not_found(request, hostname)
        except Exception as e:
            logger.error(f"Error resolving tenant for {hostname}: {str(e)}")
            return self.handle_tenant_error(request)
    
    def is_admin_domain(self, hostname):
        """Check if this is an admin/platform domain"""
        admin_domains = getattr(settings, 'ADMIN_DOMAINS', [
            'localhost', '127.0.0.1', 'admin.mall.local', 'mall.local'
        ])
        return hostname in admin_domains
    
    def handle_admin_domain(self, request):
        """Handle admin domain requests"""
        # Set public schema for admin
        connection.set_schema_to_public()
        request.tenant = None
        return None
    
    def is_tenant_accessible(self, tenant):
        """Check if tenant is accessible based on subscription status"""
        if not tenant.is_active:
            return False
        
        # Allow access during trial period
        if tenant.on_trial and not tenant.is_trial_expired:
            return True
        
        # Allow access for active subscriptions
        if not tenant.on_trial and tenant.is_subscription_active:
            return True
        
        return False
    
    def handle_inaccessible_tenant(self, request, tenant):
        """Handle requests to inaccessible tenants"""
        if not tenant.is_active:
            return self.render_error_page(
                "فروشگاه غیرفعال",
                "این فروشگاه در حال حاضر غیرفعال است.",
                status=503
            )
        
        if tenant.on_trial and tenant.is_trial_expired:
            return self.render_error_page(
                "دوره آزمایشی پایان یافته",
                "دوره آزمایشی این فروشگاه به پایان رسیده است. لطفاً برای تمدید با مدیریت تماس بگیرید.",
                status=402
            )
        
        if not tenant.is_subscription_active:
            return self.render_error_page(
                "اشتراک منقضی شده",
                "اشتراک این فروشگاه منقضی شده است.",
                status=402
            )
        
        return self.render_error_page(
            "دسترسی غیرمجاز",
            "امکان دسترسی به این فروشگاه وجود ندارد.",
            status=403
        )
    
    def handle_domain_not_found(self, request, hostname):
        """Handle requests to non-existent domains"""
        # Check if it's a subdomain pattern
        if '.' in hostname and not hostname.startswith('www.'):
            subdomain = hostname.split('.')[0]
            
            # Check if there's a tenant with this subdomain as schema_name
            try:
                tenant = Tenant.objects.get(schema_name=subdomain)
                
                # Create a default domain entry if missing
                domain, created = Domain.objects.get_or_create(
                    domain=hostname,
                    defaults={
                        'tenant': tenant,
                        'is_primary': True,
                        'verification_status': 'verified'
                    }
                )
                
                if created:
                    logger.info(f"Auto-created domain {hostname} for tenant {tenant.store_name}")
                
                # Retry the request
                return self.process_request(request)
                
            except Tenant.DoesNotExist:
                pass
        
        # Domain not found - show appropriate error
        if getattr(settings, 'SHOW_PUBLIC_IF_NO_TENANT_FOUND', False):
            connection.set_schema_to_public()
            request.tenant = None
            return None
        else:
            return self.render_error_page(
                "فروشگاه یافت نشد",
                f"فروشگاهی با آدرس {hostname} یافت نشد.",
                status=404
            )
    
    def handle_tenant_error(self, request):
        """Handle general tenant resolution errors"""
        return self.render_error_page(
            "خطای سیستم",
            "خطایی در سیستم رخ داده است. لطفاً بعداً تلاش کنید.",
            status=500
        )
    
    def render_error_page(self, title, message, status=500):
        """Render a simple error page"""
        html_content = f"""
        <!DOCTYPE html>
        <html lang="fa" dir="rtl">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{title} - مال</title>
            <style>
                body {{
                    font-family: 'Tahoma', sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    margin: 0;
                    padding: 0;
                    min-height: 100vh;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }}
                .error-container {{
                    background: white;
                    border-radius: 10px;
                    padding: 40px;
                    text-align: center;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                    max-width: 500px;
                    margin: 20px;
                }}
                .error-icon {{
                    font-size: 64px;
                    color: #dc3545;
                    margin-bottom: 20px;
                }}
                .error-title {{
                    font-size: 28px;
                    color: #333;
                    margin-bottom: 15px;
                    font-weight: bold;
                }}
                .error-message {{
                    font-size: 16px;
                    color: #666;
                    line-height: 1.6;
                    margin-bottom: 30px;
                }}
                .mall-logo {{
                    font-size: 24px;
                    color: #667eea;
                    font-weight: bold;
                    margin-top: 20px;
                }}
            </style>
        </head>
        <body>
            <div class="error-container">
                <div class="error-icon">⚠️</div>
                <h1 class="error-title">{title}</h1>
                <p class="error-message">{message}</p>
                <div class="mall-logo">مال</div>
            </div>
        </body>
        </html>
        """
        
        return HttpResponse(html_content, status=status, content_type='text/html; charset=utf-8')

class TenantSecurityMiddleware(MiddlewareMixin):
    """
    Additional security middleware for tenant requests
    Ensures proper data isolation and access control
    """
    
    def process_request(self, request):
        # Skip for admin domains
        if hasattr(request, 'tenant') and request.tenant is None:
            return None
        
        # Ensure tenant is set for non-admin requests
        if not hasattr(request, 'tenant') or request.tenant is None:
            logger.warning(f"No tenant set for request to {request.get_host()}")
            return HttpResponse("Access Denied", status=403)
        
        # Add security headers for tenant requests
        return None
    
    def process_response(self, request, response):
        # Add security headers for tenant responses
        if hasattr(request, 'tenant') and request.tenant:
            response['X-Tenant-ID'] = str(request.tenant.id)
            response['X-Frame-Options'] = 'SAMEORIGIN'
            response['X-Content-Type-Options'] = 'nosniff'
        
        return response
