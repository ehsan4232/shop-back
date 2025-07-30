import uuid
import re
from typing import Dict, List, Optional, Tuple
from django.db import transaction
from django.core.cache import cache
from django.utils.text import slugify
from django.db import models
from .models import Product, ProductClass, ProductCategory, ProductImage

class ProductUtils:
    """Product-related utility functions"""
    
    @staticmethod
    def generate_unique_sku(product_class: ProductClass, store_id: str) -> str:
        """Generate unique SKU based on product class and store"""
        # Create base SKU from product class
        base = product_class.name.upper()[:3]
        if len(base) < 3:
            base = base.ljust(3, 'X')
        
        # Add store prefix (first 2 chars of store ID)
        store_prefix = str(store_id)[:2].upper()
        
        # Generate unique suffix
        counter = 1
        while True:
            sku = f"{store_prefix}{base}{counter:04d}"
            if not Product.objects.filter(sku=sku).exists():
                return sku
            counter += 1
            if counter > 9999:  # Prevent infinite loop
                # Fallback to UUID-based SKU
                return f"{store_prefix}{uuid.uuid4().hex[:6].upper()}"
    
    @staticmethod
    def generate_unique_slug(name: str, model_class, store_id: Optional[str] = None) -> str:
        """Generate unique slug for products/categories"""
        base_slug = slugify(name, allow_unicode=True)
        
        # Start with base slug
        slug = base_slug
        counter = 1
        
        while True:
            # Check if slug exists
            queryset = model_class.objects.filter(slug=slug)
            if store_id:
                queryset = queryset.filter(store_id=store_id)
            
            if not queryset.exists():
                return slug
            
            # Try with counter
            slug = f"{base_slug}-{counter}"
            counter += 1
            
            # Prevent infinite loop
            if counter > 1000:
                slug = f"{base_slug}-{uuid.uuid4().hex[:6]}"
                break
        
        return slug
    
    @staticmethod
    def extract_price_from_text(text: str) -> Optional[float]:
        """Extract price from Persian/English text"""
        if not text:
            return None
        
        # Persian to English number conversion
        persian_to_english = {
            '۰': '0', '۱': '1', '۲': '2', '۳': '3', '۴': '4',
            '۵': '5', '۶': '6', '۷': '7', '۸': '8', '۹': '9'
        }
        
        # Convert Persian numbers
        for persian, english in persian_to_english.items():
            text = text.replace(persian, english)
        
        # Price patterns
        patterns = [
            r'(\d{1,3}(?:[,،]\d{3})*)\s*(?:تومان|ریال|درهم)',
            r'قیمت[:\s]*(\d{1,3}(?:[,،]\d{3})*)',
            r'(\d{1,3}(?:[,،]\d{3})*)\s*(?:هزار\s*)?تومان',
            r'(\d+)\s*(?:T|تومان)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            if matches:
                try:
                    # Clean and convert to float
                    price_str = matches[0].replace(',', '').replace('،', '')
                    return float(price_str)
                except (ValueError, IndexError):
                    continue
        
        return None
    
    @staticmethod
    def bulk_update_product_counts():
        """Update product counts for all categories and classes"""
        with transaction.atomic():
            # Update category counts
            for category in ProductCategory.objects.all():
                category.update_product_count()
            
            # Update product class counts
            for product_class in ProductClass.objects.all():
                product_class.update_product_count()
    
    @staticmethod
    def optimize_product_images(product: Product) -> Dict:
        """Optimize product images (resize, compress, etc.)"""
        results = {
            'processed': 0,
            'errors': []
        }
        
        try:
            from PIL import Image
            import io
            from django.core.files.base import ContentFile
            
            for product_image in product.images.all():
                try:
                    # Open image
                    image = Image.open(product_image.image.path)
                    
                    # Resize if too large
                    max_size = (1200, 1200)
                    if image.size[0] > max_size[0] or image.size[1] > max_size[1]:
                        image.thumbnail(max_size, Image.Resampling.LANCZOS)
                    
                    # Convert to RGB if necessary
                    if image.mode in ('RGBA', 'P'):
                        image = image.convert('RGB')
                    
                    # Save optimized image
                    output = io.BytesIO()
                    image.save(output, format='JPEG', quality=85, optimize=True)
                    output.seek(0)
                    
                    # Update the image file
                    product_image.image.save(
                        product_image.image.name,
                        ContentFile(output.getvalue()),
                        save=True
                    )
                    
                    results['processed'] += 1
                    
                except Exception as e:
                    results['errors'].append(f"Error processing image {product_image.id}: {str(e)}")
            
        except ImportError:
            results['errors'].append("PIL not available for image optimization")
        
        return results
    
    @staticmethod
    def get_product_hierarchy_cache_key(store_id: str) -> str:
        """Get cache key for product hierarchy"""
        return f"product_hierarchy_{store_id}"
    
    @staticmethod
    def cache_product_hierarchy(store_id: str, data: Dict, timeout: int = 3600):
        """Cache product hierarchy data"""
        cache_key = ProductUtils.get_product_hierarchy_cache_key(store_id)
        cache.set(cache_key, data, timeout)
    
    @staticmethod
    def get_cached_product_hierarchy(store_id: str) -> Optional[Dict]:
        """Get cached product hierarchy"""
        cache_key = ProductUtils.get_product_hierarchy_cache_key(store_id)
        return cache.get(cache_key)
    
    @staticmethod
    def invalidate_product_hierarchy_cache(store_id: str):
        """Invalidate product hierarchy cache"""
        cache_key = ProductUtils.get_product_hierarchy_cache_key(store_id)
        cache.delete(cache_key)

class InventoryManager:
    """Inventory management utilities"""
    
    @staticmethod
    def check_low_stock_products(store) -> List[Product]:
        """Get products with low stock"""
        return Product.objects.filter(
            store=store,
            manage_stock=True,
            stock_quantity__lte=models.F('low_stock_threshold'),
            stock_quantity__gt=0,
            status='published'
        ).select_related('category', 'product_class')
    
    @staticmethod
    def update_stock_quantity(product: Product, quantity_change: int, 
                            reason: str = '', user=None) -> Dict:
        """Update stock quantity with logging"""
        try:
            with transaction.atomic():
                old_quantity = product.stock_quantity
                new_quantity = max(0, old_quantity + quantity_change)
                
                product.stock_quantity = new_quantity
                product.save(update_fields=['stock_quantity'])
                
                return {
                    'success': True,
                    'old_quantity': old_quantity,
                    'new_quantity': new_quantity,
                    'change': quantity_change
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def bulk_stock_update(updates: List[Dict]) -> Dict:
        """Bulk update stock quantities"""
        results = {
            'successful': 0,
            'failed': 0,
            'errors': []
        }
        
        try:
            with transaction.atomic():
                for update in updates:
                    try:
                        product = Product.objects.get(id=update['product_id'])
                        result = InventoryManager.update_stock_quantity(
                            product=product,
                            quantity_change=update['quantity_change'],
                            reason=update.get('reason', ''),
                            user=update.get('user')
                        )
                        
                        if result['success']:
                            results['successful'] += 1
                        else:
                            results['failed'] += 1
                            results['errors'].append(f"Product {update['product_id']}: {result['error']}")
                    
                    except Product.DoesNotExist:
                        results['failed'] += 1
                        results['errors'].append(f"Product {update['product_id']} not found")
                    except Exception as e:
                        results['failed'] += 1
                        results['errors'].append(f"Product {update['product_id']}: {str(e)}")
        
        except Exception as e:
            results['errors'].append(f"Transaction error: {str(e)}")
        
        return results

class SearchUtils:
    """Search and filtering utilities"""
    
    @staticmethod
    def build_search_query(search_term: str, store_id: str) -> Dict:
        """Build optimized search query"""
        from django.db.models import Q
        
        if not search_term:
            return {'query': Q(), 'highlighted_fields': []}
        
        # Split search term into words
        words = search_term.strip().split()
        
        # Build query for each word
        query = Q()
        highlighted_fields = []
        
        for word in words:
            word_query = (
                Q(name_fa__icontains=word) |
                Q(name__icontains=word) |
                Q(description__icontains=word) |
                Q(short_description__icontains=word) |
                Q(sku__icontains=word) |
                Q(brand__name_fa__icontains=word) |
                Q(category__name_fa__icontains=word) |
                Q(product_class__name_fa__icontains=word) |
                Q(tags__name_fa__icontains=word)
            )
            
            query |= word_query
        
        return {
            'query': query & Q(store_id=store_id, status='published'),
            'highlighted_fields': ['name_fa', 'description', 'sku']
        }

class ContentAnalyzer:
    """Analyze content for product information extraction"""
    
    @staticmethod
    def extract_product_info(text: str) -> Dict:
        """Extract product information from text"""
        if not text:
            return {'name': '', 'price': None, 'hashtags': [], 'description': text}
        
        # Extract hashtags
        hashtags = re.findall(r'#[\u0600-\u06FF\w]+', text)
        
        # Extract product name (first line, clean of hashtags)
        lines = text.split('\n')
        product_name = lines[0] if lines else ''
        
        # Clean product name
        product_name = re.sub(r'#\w+', '', product_name)
        product_name = re.sub(r'@\w+', '', product_name)
        product_name = product_name.strip()
        
        # Extract price using existing utility
        price = ProductUtils.extract_price_from_text(text)
        
        return {
            'name': product_name[:100] if product_name else 'محصول جدید',
            'price': price,
            'hashtags': hashtags,
            'description': text,
            'clean_name': product_name
        }
    
    @staticmethod
    def suggest_category(content: str, store) -> Optional:
        """Suggest category based on content analysis"""
        from .models import ProductCategory
        
        content_lower = content.lower()
        
        # Category keywords mapping
        category_keywords = {
            'fashion': ['لباس', 'پوشاک', 'کفش', 'کیف', 'جواهر', 'عینک'],
            'electronics': ['گوشی', 'لپ‌تاپ', 'کامپیوتر', 'هدفون', 'تلویزیون'],
            'home': ['خانه', 'آشپزخانه', 'دکوراسیون', 'مبل', 'فرش'],
            'beauty': ['آرایش', 'بهداشت', 'عطر', 'کرم', 'شامپو'],
            'sports': ['ورزش', 'فیتنس', 'دوچرخه', 'توپ'],
            'books': ['کتاب', 'مجله', 'نشریه'],
            'food': ['غذا', 'خوراکی', 'نوشیدنی', 'میوه']
        }
        
        for category_type, keywords in category_keywords.items():
            if any(keyword in content_lower for keyword in keywords):
                try:
                    return ProductCategory.objects.filter(
                        store=store,
                        name_fa__icontains=category_type
                    ).first()
                except:
                    continue
        
        # Return first available category as fallback
        return ProductCategory.objects.filter(store=store, is_active=True).first()
