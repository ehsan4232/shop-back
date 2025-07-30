from django.db.models import Sum
from django.core.cache import cache
from decimal import Decimal
from typing import Dict, List, Optional, Any
from PIL import Image
import io
from django.core.files.uploadedfile import InMemoryUploadedFile


def optimize_product_image(image_file, max_width: int = 800, max_height: int = 600, quality: int = 85):
    """
    Optimize product image for web display
    """
    if not image_file:
        return None
    
    try:
        # Open image
        img = Image.open(image_file)
        
        # Convert to RGB if necessary
        if img.mode in ('RGBA', 'LA', 'P'):
            img = img.convert('RGB')
        
        # Calculate new dimensions
        width, height = img.size
        if width > max_width or height > max_height:
            img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
        
        # Save optimized image
        output = io.BytesIO()
        img.save(output, format='JPEG', quality=quality, optimize=True)
        output.seek(0)
        
        # Create new uploaded file
        optimized_file = InMemoryUploadedFile(
            output,
            'ImageField',
            f"{image_file.name.split('.')[0]}_optimized.jpg",
            'image/jpeg',
            output.getbuffer().nbytes,
            None
        )
        
        return optimized_file
    
    except Exception:
        # Return original if optimization fails
        return image_file


def calculate_shipping_cost(product, quantity: int = 1, destination: str = None) -> Decimal:
    """
    Calculate shipping cost for a product
    """
    base_cost = Decimal('50000')  # Base shipping cost in Tomans
    
    # Weight-based calculation
    if product.weight:
        weight_cost = product.weight * Decimal('1000')  # 1000 Tomans per gram
        base_cost += weight_cost
    
    # Quantity adjustment
    if quantity > 1:
        base_cost *= Decimal(str(quantity * 0.8))  # Volume discount
    
    # Destination-based adjustment (mock implementation)
    if destination:
        if destination in ['tehran', 'تهران']:
            base_cost *= Decimal('1.0')  # No extra cost
        elif destination in ['isfahan', 'اصفهان', 'mashhad', 'مشهد']:
            base_cost *= Decimal('1.2')  # 20% extra
        else:
            base_cost *= Decimal('1.5')  # 50% extra for other cities
    
    return base_cost


def generate_product_sku(product_class=None, category=None, store=None) -> str:
    """
    Generate a unique SKU for a product
    """
    import uuid
    import datetime
    
    parts = []
    
    # Store prefix
    if store:
        parts.append(store.name[:3].upper())
    
    # Category prefix
    if category:
        parts.append(category.name[:2].upper())
    
    # Product class prefix
    if product_class:
        parts.append(product_class.name[:2].upper())
    
    # Date component
    today = datetime.date.today()
    parts.append(f"{today.year}{today.month:02d}")
    
    # Random component
    parts.append(uuid.uuid4().hex[:4].upper())
    
    return '-'.join(parts)


def get_price_history(product, days: int = 30) -> List[Dict]:
    """
    Get price history for a product (mock implementation)
    """
    import datetime
    from decimal import Decimal
    
    # In real implementation, this would fetch from price history table
    current_price = product.get_effective_price()
    history = []
    
    for i in range(days):
        date = datetime.date.today() - datetime.timedelta(days=i)
        # Mock price variation
        variation = Decimal(str(1 + (i % 7) * 0.02))  # Small variations
        price = current_price * variation
        
        history.append({
            'date': date.isoformat(),
            'price': float(price),
            'currency': 'IRR'
        })
    
    return history[::-1]  # Reverse to chronological order


def calculate_discount_impact(product, new_price: Decimal) -> Dict[str, Any]:
    """
    Calculate the impact of a price change on product metrics
    """
    current_price = product.get_effective_price()
    
    if current_price == 0:
        return {'error': 'Current price is zero'}
    
    price_change_percent = ((new_price - current_price) / current_price) * 100
    
    # Estimated demand elasticity (mock calculation)
    elasticity = -1.5  # Assume price elastic product
    estimated_demand_change = elasticity * price_change_percent
    
    # Calculate revenue impact
    estimated_sales_change = estimated_demand_change / 100
    new_estimated_sales = product.sales_count * (1 + estimated_sales_change)
    
    current_revenue = current_price * product.sales_count
    new_revenue = new_price * new_estimated_sales
    revenue_change = new_revenue - current_revenue
    
    return {
        'current_price': float(current_price),
        'new_price': float(new_price),
        'price_change_percent': round(price_change_percent, 2),
        'estimated_demand_change_percent': round(estimated_demand_change, 2),
        'estimated_sales_change': round(estimated_sales_change, 2),
        'current_revenue': float(current_revenue),
        'estimated_new_revenue': float(new_revenue),
        'estimated_revenue_change': float(revenue_change),
        'revenue_change_percent': round((revenue_change / current_revenue) * 100, 2) if current_revenue > 0 else 0
    }


def get_competitor_prices(product, category=None) -> List[Dict]:
    """
    Get competitor prices for similar products (mock implementation)
    """
    # In real implementation, this would integrate with competitor analysis APIs
    current_price = product.get_effective_price()
    
    competitors = [
        {
            'competitor_name': 'فروشگاه رقیب ۱',
            'price': float(current_price * Decimal('0.95')),
            'url': 'https://competitor1.com/product',
            'availability': 'in_stock',
            'last_updated': '2025-07-30T20:00:00Z'
        },
        {
            'competitor_name': 'فروشگاه رقیب ۲',
            'price': float(current_price * Decimal('1.05')),
            'url': 'https://competitor2.com/product',
            'availability': 'in_stock',
            'last_updated': '2025-07-30T19:30:00Z'
        },
        {
            'competitor_name': 'فروشگاه رقیب ۳',
            'price': float(current_price * Decimal('0.98')),
            'url': 'https://competitor3.com/product',
            'availability': 'limited_stock',
            'last_updated': '2025-07-30T19:45:00Z'
        }
    ]
    
    return competitors


def validate_inventory_levels(store) -> Dict[str, Any]:
    """
    Validate inventory levels and identify issues
    """
    from apps.products.models import Product
    
    products = Product.objects.filter(store=store, status='published')
    
    issues = {
        'out_of_stock': [],
        'low_stock': [],
        'overstocked': [],
        'no_stock_tracking': []
    }
    
    for product in products:
        if not product.manage_stock:
            issues['no_stock_tracking'].append({
                'id': str(product.id),
                'name': product.name_fa,
                'sku': product.sku
            })
        elif product.stock_quantity == 0:
            issues['out_of_stock'].append({
                'id': str(product.id),
                'name': product.name_fa,
                'sku': product.sku,
                'stock': product.stock_quantity
            })
        elif product.stock_quantity <= product.low_stock_threshold:
            issues['low_stock'].append({
                'id': str(product.id),
                'name': product.name_fa,
                'sku': product.sku,
                'stock': product.stock_quantity,
                'threshold': product.low_stock_threshold
            })
        elif product.stock_quantity > 1000:  # Arbitrary "overstocked" threshold
            issues['overstocked'].append({
                'id': str(product.id),
                'name': product.name_fa,
                'sku': product.sku,
                'stock': product.stock_quantity
            })
    
    summary = {
        'total_products': products.count(),
        'total_issues': sum(len(issue_list) for issue_list in issues.values()),
        'issues': issues
    }
    
    return summary


def bulk_update_prices(products, price_change_percent: float, apply_to: str = 'all'):
    """
    Bulk update product prices
    """
    from apps.products.models import Product
    from django.db import transaction
    
    updated_count = 0
    errors = []
    
    with transaction.atomic():
        for product in products:
            try:
                current_price = product.get_effective_price()
                if current_price > 0:
                    new_price = current_price * (1 + price_change_percent / 100)
                    
                    if apply_to == 'base_price' or not product.base_price:
                        product.base_price = new_price
                        product.save(update_fields=['base_price', 'updated_at'])
                        updated_count += 1
                    
                    # Update variants if they exist
                    if apply_to in ['all', 'variants']:
                        for variant in product.variants.all():
                            variant.price = variant.price * (1 + price_change_percent / 100)
                            variant.save(update_fields=['price', 'updated_at'])
                
            except Exception as e:
                errors.append({
                    'product_id': str(product.id),
                    'product_name': product.name_fa,
                    'error': str(e)
                })
    
    return {
        'updated_count': updated_count,
        'total_products': len(products),
        'errors': errors,
        'success_rate': (updated_count / len(products)) * 100 if products else 0
    }


def generate_product_report(store, report_type: str = 'summary') -> Dict[str, Any]:
    """
    Generate various product reports
    """
    from apps.products.models import Product, ProductClass, ProductCategory, Brand
    
    cache_key = f"product_report_{store.id}_{report_type}"
    cached_report = cache.get(cache_key)
    if cached_report:
        return cached_report
    
    products = Product.objects.filter(store=store)
    
    if report_type == 'summary':
        report = {
            'total_products': products.count(),
            'published_products': products.filter(status='published').count(),
            'draft_products': products.filter(status='draft').count(),
            'total_value': float(products.aggregate(
                total=Sum('base_price')
            )['total'] or 0),
            'categories': ProductCategory.objects.filter(store=store, is_active=True).count(),
            'product_classes': ProductClass.objects.filter(store=store, is_active=True).count(),
            'brands': Brand.objects.filter(store=store, is_active=True).count(),
            'featured_products': products.filter(is_featured=True).count(),
        }
    
    elif report_type == 'performance':
        report = {
            'top_viewed': list(products.filter(status='published')
                             .order_by('-view_count')[:10]
                             .values('name_fa', 'view_count', 'sku')),
            'top_selling': list(products.filter(status='published')
                              .order_by('-sales_count')[:10]
                              .values('name_fa', 'sales_count', 'sku')),
            'low_performers': list(products.filter(status='published', view_count__lt=10)
                                 .order_by('view_count')[:10]
                                 .values('name_fa', 'view_count', 'sku')),
        }
    
    elif report_type == 'inventory':
        report = validate_inventory_levels(store)
    
    else:
        report = {'error': f'Unknown report type: {report_type}'}
    
    # Cache for 10 minutes
    cache.set(cache_key, report, timeout=600)
    return report
