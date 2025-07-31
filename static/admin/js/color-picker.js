// Enhanced Color Picker JavaScript for Django Admin
// Provides enhanced functionality for color fields in product attributes

(function() {
    'use strict';
    
    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initColorPickers);
    } else {
        initColorPickers();
    }
    
    function initColorPickers() {
        // Initialize all color picker inputs
        const colorInputs = document.querySelectorAll('input[type="color"], .color-picker-input');
        colorInputs.forEach(initColorPicker);
        
        // Handle dynamic inline forms (for tabular inlines)
        initInlineColorPickers();
        
        // Handle attribute type changes
        initAttributeTypeHandling();
    }
    
    function initColorPicker(input) {
        if (input.dataset.colorPickerInitialized) {
            return;
        }
        
        input.dataset.colorPickerInitialized = 'true';
        
        // Ensure input type is color
        if (input.classList.contains('color-picker-input')) {
            input.type = 'color';
        }
        
        // Add event listeners
        input.addEventListener('change', handleColorChange);
        input.addEventListener('input', handleColorInput);
        
        // Create preview element if it doesn't exist
        createColorPreview(input);
        
        // Set initial value if empty
        if (!input.value || input.value === '') {
            input.value = '#000000';
        }
        
        // Update preview on initialization
        updateColorPreview(input);
    }
    
    function createColorPreview(input) {
        // Check if preview already exists
        if (input.parentElement.querySelector('.color-preview')) {
            return;
        }
        
        const preview = document.createElement('div');
        preview.className = 'admin-color-preview color-preview';
        preview.style.backgroundColor = input.value || '#000000';
        preview.title = input.value || '#000000';
        
        // Insert preview after the input
        input.parentElement.insertBefore(preview, input.nextSibling);
        
        // Add click handler to preview to open color picker
        preview.addEventListener('click', function() {
            input.click();
        });
    }
    
    function updateColorPreview(input) {
        const preview = input.parentElement.querySelector('.color-preview');
        if (preview) {
            preview.style.backgroundColor = input.value;
            preview.title = input.value;
        }
        
        // Update any related display elements
        updateRelatedDisplays(input);
    }
    
    function updateRelatedDisplays(input) {
        // Update hex value display if exists
        const hexDisplay = input.parentElement.querySelector('.color-hex-display');
        if (hexDisplay) {
            hexDisplay.textContent = input.value;
        }
        
        // Update color name if we have a mapping
        const colorName = getColorName(input.value);
        const nameDisplay = input.parentElement.querySelector('.color-name-display');
        if (nameDisplay && colorName) {
            nameDisplay.textContent = colorName;
        }
    }
    
    function handleColorChange(event) {
        const input = event.target;
        updateColorPreview(input);
        
        // Validate hex color format
        if (!isValidHexColor(input.value)) {
            input.classList.add('color-picker-error');
            showColorError(input, 'فرمت رنگ نامعتبر است');
        } else {
            input.classList.remove('color-picker-error');
            hideColorError(input);
        }
        
        // Trigger change event for Django admin
        input.dispatchEvent(new Event('input', { bubbles: true }));
    }
    
    function handleColorInput(event) {
        const input = event.target;
        updateColorPreview(input);
    }
    
    function isValidHexColor(color) {
        return /^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$/.test(color);
    }
    
    function showColorError(input, message) {
        // Remove existing error message
        hideColorError(input);
        
        const errorDiv = document.createElement('div');
        errorDiv.className = 'color-picker-error-message';
        errorDiv.style.cssText = 'color: #dc3545; font-size: 11px; margin-top: 2px;';
        errorDiv.textContent = message;
        
        input.parentElement.appendChild(errorDiv);
    }
    
    function hideColorError(input) {
        const errorMsg = input.parentElement.querySelector('.color-picker-error-message');
        if (errorMsg) {
            errorMsg.remove();
        }
    }
    
    function initInlineColorPickers() {
        // Handle dynamically added inline forms
        const inlineGroups = document.querySelectorAll('.tabular.inline-group, .stacked.inline-group');
        
        inlineGroups.forEach(function(group) {
            // Watch for new rows being added
            const observer = new MutationObserver(function(mutations) {
                mutations.forEach(function(mutation) {
                    mutation.addedNodes.forEach(function(node) {
                        if (node.nodeType === 1) { // Element node
                            const colorInputs = node.querySelectorAll('input[type="color"], .color-picker-input');
                            colorInputs.forEach(initColorPicker);
                        }
                    });
                });
            });
            
            observer.observe(group, {
                childList: true,
                subtree: true
            });
        });
        
        // Handle existing add row buttons
        const addButtons = document.querySelectorAll('.add-row a, .addlink');
        addButtons.forEach(function(button) {
            button.addEventListener('click', function() {
                // Small delay to allow DOM to update
                setTimeout(function() {
                    const newInputs = document.querySelectorAll('input[type="color"]:not([data-color-picker-initialized]), .color-picker-input:not([data-color-picker-initialized])');
                    newInputs.forEach(initColorPicker);
                }, 100);
            });
        });
    }
    
    function initAttributeTypeHandling() {
        // Handle attribute type changes to show/hide appropriate fields
        const attributeSelects = document.querySelectorAll('select[name*="attribute"]');
        
        attributeSelects.forEach(function(select) {
            select.addEventListener('change', function() {
                handleAttributeTypeChange(this);
            });
            
            // Initialize on page load
            handleAttributeTypeChange(select);
        });
    }
    
    function handleAttributeTypeChange(select) {
        const selectedOption = select.options[select.selectedIndex];
        if (!selectedOption || !selectedOption.value) return;
        
        // Get the row containing this select
        const row = select.closest('tr, .form-row');
        if (!row) return;
        
        // This would need to make an AJAX call to get attribute type info
        // For now, we'll just ensure color inputs are properly initialized
        const colorInputs = row.querySelectorAll('input[type="color"], .color-picker-input');
        colorInputs.forEach(initColorPicker);
    }
    
    function getColorName(hexColor) {
        // Basic color name mapping for Persian
        const colorNames = {
            '#FF0000': 'قرمز',
            '#00FF00': 'سبز',
            '#0000FF': 'آبی',
            '#FFFF00': 'زرد',
            '#FF00FF': 'بنفش',
            '#00FFFF': 'فیروزه‌ای',
            '#FFA500': 'نارنجی',
            '#800080': 'ارغوانی',
            '#FFC0CB': 'صورتی',
            '#A52A2A': 'قهوه‌ای',
            '#808080': 'خاکستری',
            '#000000': 'مشکی',
            '#FFFFFF': 'سفید'
        };
        
        return colorNames[hexColor.toUpperCase()] || null;
    }
    
    // Public API for external use
    window.ColorPickerAdmin = {
        init: initColorPickers,
        initSingle: initColorPicker,
        updatePreview: updateColorPreview,
        isValidColor: isValidHexColor
    };
    
})();

// Initialize on page load and when Django admin adds new inline forms
document.addEventListener('DOMContentLoaded', function() {
    // Re-initialize when Django admin adds new inline forms
    if (typeof django !== 'undefined' && django.jQuery) {
        django.jQuery(document).on('formset:added', function(event, row) {
            // Small delay to ensure DOM is ready
            setTimeout(function() {
                const colorInputs = row.find('input[type="color"], .color-picker-input');
                colorInputs.each(function() {
                    window.ColorPickerAdmin.initSingle(this);
                });
            }, 50);
        });
    }
});
