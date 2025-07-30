# Mall Platform - Migration Guide

## Overview
This guide helps you migrate to the new object-oriented product structure that was implemented to meet the product requirements.

## 🚨 IMPORTANT: Breaking Changes
The product models have been completely restructured to implement the required object-oriented hierarchy. This requires careful migration.

## Migration Steps

### Step 1: Backup Current Data
```bash
# Backup your database before migration
pg_dump your_database_name > backup_before_migration.sql

# Or using Django
python manage.py dumpdata > data_backup.json
```

### Step 2: Install New Requirements
```bash
pip install -r requirements.txt
```

### Step 3: Create and Run Migrations
```bash
# Make migrations for the new models
python manage.py makemigrations products
python manage.py makemigrations orders
python manage.py makemigrations accounts
python manage.py makemigrations stores

# Run migrations
python manage.py migrate
```

### Step 4: Create Initial Product Classes
```python
# management/commands/create_initial_product_classes.py
from django.core.management.base import BaseCommand
from apps.products.models import ProductClass, AttributeType
from apps.stores.models import Store

class Command(BaseCommand):
    help = 'Create initial product classes for existing stores'
    
    def handle(self, *args, **options):
        # Create basic attribute types
        color_attr, _ = AttributeType.objects.get_or_create(
            name='color',
            defaults={
                'name_fa': 'رنگ',
                'slug': 'color',
                'data_type': 'color',
                'is_filterable': True
            }
        )
        
        size_attr, _ = AttributeType.objects.get_or_create(
            name='size',
            defaults={
                'name_fa': 'سایز',
                'slug': 'size', 
                'data_type': 'choice',
                'is_filterable': True
            }
        )
        
        # Create basic product classes for each store
        for store in Store.objects.all():
            # Root class
            root_class, _ = ProductClass.objects.get_or_create(
                store=store,
                slug='products',
                defaults={
                    'name': 'Products',
                    'name_fa': 'محصولات',
                    'description': 'Root product class',
                    'is_active': True,
                    'is_leaf': True
                }
            )
        
        self.stdout.write(
            self.style.SUCCESS('Successfully created initial product classes')
        )
```

### Step 5: Run Management Commands
```bash
python manage.py create_initial_product_classes
```

### Step 6: Test the Migration
```bash
# Run tests to ensure everything works
python manage.py test

# Check admin interface
python manage.py runserver
# Visit /admin/ and verify all models are accessible
```

## New Features Available

### 1. Object-Oriented Product Hierarchy
```python
# Create hierarchical product classes
electronics = ProductClass.objects.create(
    store=my_store,
    name='Electronics',
    name_fa='الکترونیک',
    base_price=1000000,  # Base price for all electronics
    is_leaf=False
)

# Child class inherits price and attributes
smartphones = ProductClass.objects.create(
    store=my_store,
    parent=electronics,
    name='Smartphones', 
    name_fa='گوشی هوشمند',
    # Will inherit base_price from parent
    is_leaf=True  # Can have products
)
```

### 2. Attribute Inheritance
```python
# Add attributes to parent class
ProductClassAttribute.objects.create(
    product_class=electronics,
    attribute_type=color_attr,
    is_required=True,
    is_inherited=True
)

# Child classes automatically inherit this attribute
```

### 3. Creating Products with Classes
```python
# Products must be created from leaf classes only
product = Product.objects.create(
    store=my_store,
    product_class=smartphones,  # Must be leaf class
    category=phone_category,
    name='iPhone 15',
    name_fa='آیفون ۱۵',
    # base_price is optional - will use class price if not set
)

# Get effective price (with inheritance)
price = product.get_effective_price()  # Returns inherited or own price
```

## API Changes

### New Endpoints Added:
- `GET /api/products/attribute-types/` - Manage attribute types
- `GET /api/products/product-classes/` - Product class hierarchy
- `GET /api/products/product-class-hierarchy/` - Tree structure
- `GET /api/products/tags/` - Product tags

### Updated Endpoints:
- All product endpoints now include `product_class` information
- Filtering by product class hierarchy is supported
- Price inheritance is automatically handled

## Admin Interface Updates

### New Admin Sections:
1. **Attribute Types** - Define available attribute types
2. **Product Classes** - Manage hierarchical product structure
3. **Tags** - Product tagging system

### Enhanced Sections:
1. **Products** - Now shows product class and effective price
2. **Categories** - Enhanced with attribute management
3. **Brands** - Updated interface

## Breaking Changes

### 1. Product Model Changes
- Added required `product_class` field
- `base_price` is now optional (inherits from class)
- Added `get_effective_price()` method

### 2. API Response Changes
- Product serializers now include `product_class_name`
- Price fields include both `base_price` and `effective_price`
- Inheritance information is included in responses

### 3. Admin Interface
- Product creation now requires selecting a product class
- Only leaf classes can have products

## Troubleshooting

### Common Issues:

1. **Migration Errors**
   ```bash
   # If you get constraint errors, run:
   python manage.py migrate --fake-initial
   ```

2. **Missing Product Classes**
   ```bash
   # Create basic structure:
   python manage.py shell
   from apps.products.models import ProductClass
   from apps.stores.models import Store
   
   for store in Store.objects.all():
       ProductClass.objects.get_or_create(
           store=store,
           slug='general',
           defaults={'name': 'General', 'name_fa': 'عمومی', 'is_leaf': True}
       )
   ```

3. **Import Errors**
   - Ensure all new requirements are installed
   - Restart Django development server
   - Clear any cached bytecode: `find . -name "*.pyc" -delete`

## Testing the New Structure

### 1. Test Product Class Creation
```python
# In Django shell
from apps.products.models import ProductClass, AttributeType
from apps.stores.models import Store

store = Store.objects.first()

# Create hierarchy
root = ProductClass.objects.create(
    store=store,
    name='Products',
    name_fa='محصولات',
    slug='products',
    base_price=0,
    is_leaf=False
)

clothing = ProductClass.objects.create(
    store=store,
    parent=root,
    name='Clothing',
    name_fa='پوشاک', 
    slug='clothing',
    base_price=100000,
    is_leaf=True
)

# Test inheritance
print(clothing.get_effective_price())  # Should return 100000
print(clothing.get_inherited_attributes())  # Should show inherited attributes
```

### 2. Test Product Creation
```python
from apps.products.models import Product, ProductCategory

category = ProductCategory.objects.first()

product = Product.objects.create(
    store=store,
    product_class=clothing,  # Must be leaf class
    category=category,
    name='T-Shirt',
    name_fa='تی‌شرت',
    # base_price not required - will inherit
)

print(product.get_effective_price())  # Should return inherited price
```

## Support

If you encounter any issues during migration:

1. Check the GitHub issues for known problems
2. Ensure all requirements are properly installed  
3. Verify database permissions for schema changes
4. Contact the development team for assistance

## Rollback Plan

If migration fails and you need to rollback:

```bash
# Restore from backup
psql your_database_name < backup_before_migration.sql

# Or restore Django data
python manage.py loaddata data_backup.json

# Revert to previous Git commit
git checkout previous_commit_hash
```

Remember to test thoroughly in a development environment before applying to production!
