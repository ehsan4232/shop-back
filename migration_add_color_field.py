# CRITICAL FIX: Update ProductAttributeValue to add missing color_hex field
# This addresses product description requirement: "Color fields must be presented with colorpads"

from django.db import migrations, models

class Migration(migrations.Migration):
    
    dependencies = [
        ('products', '0001_initial'),  # Replace with your latest migration
    ]

    operations = [
        migrations.AddField(
            model_name='productattributevalue',
            name='color_hex',
            field=models.CharField(
                max_length=7, 
                null=True, 
                blank=True, 
                verbose_name='کد رنگ',
                help_text='کد رنگ hex برای ویژگی‌های رنگ (مثال: #FF0000)'
            ),
        ),
        
        # Add index for color_hex field for better performance
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS products_productattributevalue_color_hex_idx ON products_productattributevalue(color_hex);",
            reverse_sql="DROP INDEX IF EXISTS products_productattributevalue_color_hex_idx;"
        ),
    ]