from django import forms
from django.core.exceptions import ValidationError
from apps.products.models import (
    Product, ProductClass, ProductCategory, Brand, Tag,
    ProductAttributeValue, ProductImage, ProductVariant
)
from apps.social_media.models import SocialMediaPost


class ColorWidget(forms.TextInput):
    """
    Custom color widget to replace external colorfield dependency
    Product requirement: "Color fields must be presented with colorpads"
    """
    template_name = 'widgets/color_input.html'
    
    def __init__(self, attrs=None):
        default_attrs = {
            'type': 'color',
            'class': 'color-picker-input'
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)


class ProductInstanceCreationForm(forms.ModelForm):
    """
    Enhanced product creation form with key features from product description:
    1. Checkbox for creating another instance with same info
    2. Color fields with color pads
    3. Social media import functionality
    4. Stock quantity validation for customer warnings
    """
    
    # CRITICAL: Checkbox for creating another instance (product requirement)
    create_another_instance = forms.BooleanField(
        required=False,
        label='ایجاد نمونه دیگری با همین اطلاعات',
        help_text='برای تسهیل در ایجاد محصولات مشابه'
    )
    
    # Enhanced color field with color pad (product requirement)
    primary_color = forms.CharField(
        required=False,
        widget=ColorWidget(attrs={'class': 'color-picker'}),
        label='رنگ اصلی محصول',
        help_text='انتخاب رنگ با استفاده از پالت رنگ'
    )
    
    # Social media import fields (product requirement)
    import_from_social = forms.BooleanField(
        required=False,
        label='وارد کردن از شبکه اجتماعی',
        help_text='استفاده از مطالب شبکه‌های اجتماعی'
    )
    
    social_media_platform = forms.ChoiceField(
        choices=[
            ('', 'انتخاب کنید'),
            ('telegram', 'تلگرام'),
            ('instagram', 'اینستاگرام'),
        ],
        required=False,
        label='پلتفرم شبکه اجتماعی'
    )
    
    class Meta:
        model = Product
        fields = [
            'name', 'name_fa', 'product_class', 'category', 'brand', 'tags',
            'description', 'short_description', 'product_type', 'base_price',
            'compare_price', 'stock_quantity', 'sku', 'weight', 'status',
            'is_featured', 'featured_image'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'short_description': forms.Textarea(attrs={'rows': 2}),
            'tags': forms.CheckboxSelectMultiple(),
        }
    
    def __init__(self, *args, **kwargs):
        self.store = kwargs.pop('store', None)
        super().__init__(*args, **kwargs)
        
        # Filter choices by store for multi-tenant isolation
        if self.store:
            self.fields['product_class'].queryset = ProductClass.objects.filter(
                store=self.store, is_leaf=True
            )
            self.fields['category'].queryset = ProductCategory.objects.filter(
                store=self.store, is_active=True
            )
            self.fields['brand'].queryset = Brand.objects.filter(
                store=self.store, is_active=True
            )
            self.fields['tags'].queryset = Tag.objects.filter(
                store=self.store
            )
    
    def clean_product_class(self):
        """Validate product class can create instances (product requirement)"""
        product_class = self.cleaned_data.get('product_class')
        if product_class:
            can_create, message = product_class.can_create_product_instances()
            if not can_create:
                raise ValidationError(f'امکان ایجاد محصول از این کلاس وجود ندارد: {message}')
        return product_class
    
    def clean_stock_quantity(self):
        """Validate stock quantity for customer warning system"""
        stock_quantity = self.cleaned_data.get('stock_quantity')
        if stock_quantity is not None and stock_quantity < 0:
            raise ValidationError('موجودی انبار نمی‌تواند منفی باشد')
        return stock_quantity
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Validate social media import
        import_from_social = cleaned_data.get('import_from_social')
        social_media_platform = cleaned_data.get('social_media_platform')
        
        if import_from_social and not social_media_platform:
            raise ValidationError({
                'social_media_platform': 'لطفاً پلتفرم شبکه اجتماعی را انتخاب کنید'
            })
        
        return cleaned_data
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Set store
        if self.store:
            instance.store = self.store
        
        # Handle social media import
        if self.cleaned_data.get('import_from_social'):
            instance.imported_from_social = True
            instance.social_media_source = self.cleaned_data.get('social_media_platform')
        
        if commit:
            instance.save()
            self.save_m2m()
            
            # Handle creating another instance with same info
            if self.cleaned_data.get('create_another_instance'):
                self._create_duplicate_instance(instance)
        
        return instance
    
    def _create_duplicate_instance(self, original_instance):
        """Create another instance with same information (product requirement)"""
        # Create duplicate with incremented name
        duplicate = Product.objects.create(
            store=original_instance.store,
            product_class=original_instance.product_class,
            category=original_instance.category,
            brand=original_instance.brand,
            name=f"{original_instance.name} - کپی",
            name_fa=f"{original_instance.name_fa} - کپی",
            description=original_instance.description,
            short_description=original_instance.short_description,
            product_type=original_instance.product_type,
            base_price=original_instance.base_price,
            compare_price=original_instance.compare_price,
            stock_quantity=original_instance.stock_quantity,
            weight=original_instance.weight,
            status='draft',  # Start as draft
            is_featured=False,
        )
        
        # Copy tags
        duplicate.tags.set(original_instance.tags.all())
        
        return duplicate


class SocialMediaImportForm(forms.Form):
    """
    Form for importing content from social media platforms
    Product requirement: "Get from social media" button functionality
    """
    
    platform = forms.ChoiceField(
        choices=[
            ('telegram', 'تلگرام'),
            ('instagram', 'اینستاگرام'),
        ],
        label='پلتفرم'
    )
    
    account_username = forms.CharField(
        max_length=100,
        label='نام کاربری',
        help_text='نام کاربری اکانت برای دریافت پست‌ها'
    )
    
    max_posts = forms.IntegerField(
        initial=5,
        min_value=1,
        max_value=10,
        label='حداکثر تعداد پست',
        help_text='حداکثر 5 پست آخر دریافت می‌شود (طبق نیاز پروژه)'
    )
    
    def clean_account_username(self):
        username = self.cleaned_data.get('account_username')
        if username:
            # Remove @ if present
            username = username.lstrip('@')
        return username


class ProductColorAttributeForm(forms.Form):
    """
    Special form for color attributes with color pad support
    Product requirement: "Color fields must be presented with colorpads"
    """
    
    color_value = forms.CharField(
        widget=ColorWidget(attrs={
            'class': 'color-picker-input',
            'data-color-format': 'hex'
        }),
        label='انتخاب رنگ'
    )
    
    color_name = forms.CharField(
        max_length=50,
        label='نام رنگ',
        help_text='نام توصیفی رنگ (مثال: قرمز آتشین)'
    )
    
    color_code = forms.CharField(
        max_length=20,
        required=False,
        label='کد رنگ',
        help_text='کد تولیدی یا استاندارد رنگ'
    )


class ProductVariantForm(forms.ModelForm):
    """Form for creating product variants with color support"""
    
    class Meta:
        model = ProductVariant
        fields = ['sku', 'price', 'compare_price', 'stock_quantity', 'image', 'is_default']
    
    def __init__(self, *args, **kwargs):
        self.product = kwargs.pop('product', None)
        super().__init__(*args, **kwargs)
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.product:
            instance.product = self.product
        if commit:
            instance.save()
        return instance


class BulkProductImportForm(forms.Form):
    """Form for bulk importing products from social media"""
    
    csv_file = forms.FileField(
        label='فایل CSV',
        help_text='فایل CSV حاوی اطلاعات محصولات'
    )
    
    default_product_class = forms.ModelChoiceField(
        queryset=ProductClass.objects.none(),
        label='کلاس پیش‌فرض محصول'
    )
    
    default_category = forms.ModelChoiceField(
        queryset=ProductCategory.objects.none(),
        label='دسته‌بندی پیش‌فرض'
    )
    
    def __init__(self, *args, **kwargs):
        store = kwargs.pop('store', None)
        super().__init__(*args, **kwargs)
        
        if store:
            self.fields['default_product_class'].queryset = ProductClass.objects.filter(
                store=store, is_leaf=True
            )
            self.fields['default_category'].queryset = ProductCategory.objects.filter(
                store=store, is_active=True
            )


# Widget for color picker functionality
class ColorPadWidget(forms.TextInput):
    """
    Custom widget for color selection with color pad
    Product requirement: "Color fields must be presented with colorpads"
    """
    
    template_name = 'widgets/color_pad.html'
    
    def __init__(self, attrs=None):
        default_attrs = {
            'class': 'color-pad-input',
            'data-color-picker': 'true'
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)
    
    class Media:
        css = {
            'all': ('css/color-picker.css',)
        }
        js = ('js/color-picker.js',)
