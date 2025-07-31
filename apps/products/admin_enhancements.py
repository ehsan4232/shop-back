# Enhanced admin interface with color picker support
from django import forms
from django.contrib import admin
from django.utils.html import format_html
from .models import ProductAttributeValue, Product, AttributeType

class ColorWidget(forms.TextInput):
    """Custom color picker widget for admin interface"""
    input_type = 'color'
    template_name = 'admin/widgets/color_picker.html'
    
    class Media:
        css = {
            'screen': ('admin/css/color-picker.css',)
        }
        js = ('admin/js/color-picker.js',)
    
    def format_value(self, value):
        if value:
            return value
        return '#000000'

class ProductAttributeValueForm(forms.ModelForm):
    """Enhanced form for product attribute values with color support"""
    
    class Meta:
        model = ProductAttributeValue
        fields = '__all__'
        widgets = {
            'value_color': ColorWidget(attrs={
                'class': 'color-picker-input',
                'data-toggle': 'color-picker'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Dynamically show/hide fields based on attribute type
        if self.instance and self.instance.attribute:
            attr_type = self.instance.attribute.attribute_type.data_type
            
            # Hide irrelevant fields based on attribute type
            if attr_type != 'color':
                self.fields['value_color'].widget = forms.HiddenInput()
            if attr_type != 'number':
                self.fields['value_number'].widget = forms.HiddenInput()
            if attr_type != 'boolean':
                self.fields['value_boolean'].widget = forms.HiddenInput()
            if attr_type != 'date':
                self.fields['value_date'].widget = forms.HiddenInput()
            if attr_type in ['color', 'number', 'boolean', 'date']:
                self.fields['value_text'].widget = forms.HiddenInput()

class ProductAttributeValueInline(admin.TabularInline):
    """Enhanced inline for product attribute values"""
    model = ProductAttributeValue
    form = ProductAttributeValueForm
    extra = 0
    
    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(super().get_readonly_fields(request, obj))
        
        # Make attribute readonly after creation to prevent data corruption
        if obj and obj.pk:
            readonly_fields.append('attribute')
        
        return readonly_fields
    
    def color_preview(self, obj):
        """Display color preview in admin"""
        if obj.value_color:
            return format_html(
                '<div style="width: 20px; height: 20px; background-color: {}; border: 1px solid #ccc; display: inline-block; margin-right: 5px;"></div>{}',
                obj.value_color,
                obj.value_color
            )
        return '-'
    color_preview.short_description = 'پیش‌نمایش رنگ'
    
    def get_fields(self, request, obj=None):
        fields = ['attribute', 'value_text', 'value_number', 'value_boolean', 'value_date', 'value_color']
        return fields
    
    def get_list_display(self, request):
        return ['attribute', 'get_value', 'color_preview']

# Enhanced Product Admin with color support
class EnhancedProductAdmin(admin.ModelAdmin):
    """Enhanced product admin with better color field support"""
    
    inlines = [ProductAttributeValueInline]
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        
        # Add JavaScript for dynamic form behavior
        form.Media.js = form.Media.js + ('admin/js/product-form-enhancements.js',)
        
        return form
    
    class Media:
        css = {
            'screen': ('admin/css/enhanced-product-admin.css',)
        }
        js = (
            'admin/js/jquery.min.js',
            'admin/js/color-picker.js',
            'admin/js/product-form-enhancements.js',
        )

# Custom admin for AttributeType with color preview
class AttributeTypeAdmin(admin.ModelAdmin):
    list_display = ['name_fa', 'name', 'data_type', 'is_required', 'is_filterable']
    list_filter = ['data_type', 'is_required', 'is_filterable']
    search_fields = ['name', 'name_fa']
    
    def get_list_display(self, request):
        return ['name_fa', 'name', 'data_type', 'is_required', 'is_filterable', 'color_indicator']
    
    def color_indicator(self, obj):
        """Show color indicator for color attribute types"""
        if obj.data_type == 'color':
            return format_html(
                '<span style="background: linear-gradient(90deg, #ff0000, #00ff00, #0000ff); width: 30px; height: 15px; display: inline-block; border-radius: 3px;"></span>'
            )
        return '-'
    color_indicator.short_description = 'نوع رنگ'

# Register enhanced admin classes
# admin.site.register(AttributeType, AttributeTypeAdmin)
# admin.site.register(Product, EnhancedProductAdmin)
