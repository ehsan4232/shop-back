"""
Mall platform views for error handling and core functionality
"""
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import logging

logger = logging.getLogger('mall')


def handler404(request, exception=None):
    """Custom 404 handler for API and web requests"""
    if request.path.startswith('/api/'):
        return JsonResponse({
            'error': 'Not Found',
            'message': 'The requested endpoint was not found',
            'status_code': 404
        }, status=404)
    
    return render(request, '404.html', {
        'title': 'صفحه یافت نشد',
        'message': 'صفحه مورد نظر شما یافت نشد'
    }, status=404)


def handler500(request):
    """Custom 500 handler for API and web requests"""
    logger.error('500 Internal Server Error', exc_info=True, extra={
        'request': request,
        'user': getattr(request, 'user', None)
    })
    
    if request.path.startswith('/api/'):
        error_data = {
            'error': 'Internal Server Error',
            'message': 'An unexpected error occurred',
            'status_code': 500
        }
        
        # Include debug info if in debug mode
        if settings.DEBUG:
            import traceback
            error_data['debug'] = traceback.format_exc()
        
        return JsonResponse(error_data, status=500)
    
    return render(request, '500.html', {
        'title': 'خطای سرور',
        'message': 'خطای داخلی سرور رخ داده است'
    }, status=500)


@csrf_exempt
def health_check(request):
    """Health check endpoint for load balancer and monitoring"""
    try:
        # Basic health checks
        from django.db import connection
        from django.core.cache import cache
        
        # Check database
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        
        # Check cache
        cache.set('health_check', 'ok', 10)
        cache.get('health_check')
        
        return JsonResponse({
            'status': 'healthy',
            'database': 'ok',
            'cache': 'ok',
            'debug': settings.DEBUG
        })
        
    except Exception as e:
        logger.error(f'Health check failed: {e}')
        return JsonResponse({
            'status': 'unhealthy',
            'error': str(e)
        }, status=503)


def maintenance_mode(request):
    """Maintenance mode page"""
    return render(request, 'maintenance.html', {
        'title': 'حالت تعمیر',
        'message': 'سایت در حال تعمیر و به‌روزرسانی است'
    }, status=503)
