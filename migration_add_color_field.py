# Add color field to ProductAttributeValue model
# This migration adds the missing color field to support the color picker component

from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('products', '0001_initial'),  # Replace with your latest migration
    ]

    operations = [
        migrations.AddField(
            model_name='productattributevalue',
            name='value_color',
            field=models.CharField(blank=True, max_length=7, null=True, verbose_name='مقدار رنگ (هکس)'),
        ),
        migrations.AddIndex(
            model_name='productattributevalue',
            index=models.Index(fields=['value_color'], name='products_productattributevalue_value_color_idx'),
        ),
    ]
