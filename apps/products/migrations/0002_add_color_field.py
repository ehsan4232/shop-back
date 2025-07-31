# Generated migration for adding color field support
# This migration adds the missing color field to ProductAttributeValue model

from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('products', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='productattributevalue',
            name='value_color',
            field=models.CharField(
                blank=True, 
                max_length=7, 
                null=True, 
                verbose_name='مقدار رنگ (هکس)',
                help_text='رنگ در فرمت هکس مانند #FF0000'
            ),
        ),
        migrations.AddIndex(
            model_name='productattributevalue',
            index=models.Index(
                fields=['value_color'], 
                name='products_productattributevalue_value_color_idx'
            ),
        ),
        # Add index for color filtering performance
        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_color_filtering ON products_productattributevalue (product_id, attribute_id) WHERE value_color IS NOT NULL;",
            reverse_sql="DROP INDEX IF EXISTS idx_color_filtering;"
        ),
    ]
