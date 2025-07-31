    def get_value(self):
        """Get the appropriate value based on attribute type"""
        if self.attribute.attribute_type.data_type == 'number':
            return self.value_number
        elif self.attribute.attribute_type.data_type == 'boolean':
            return self.value_boolean
        elif self.attribute.attribute_type.data_type == 'date':
            return self.value_date
        elif self.attribute.attribute_type.data_type == 'color':  # ADDED: Support for color attributes
            return self.value_color
        else:
            return self.value_text
    
    def set_value(self, value):
        """Set the appropriate value based on attribute type"""
        if self.attribute.attribute_type.data_type == 'number':
            self.value_number = value
        elif self.attribute.attribute_type.data_type == 'boolean':
            self.value_boolean = value
        elif self.attribute.attribute_type.data_type == 'date':
            self.value_date = value
        elif self.attribute.attribute_type.data_type == 'color':  # ADDED: Support for color attributes
            self.value_color = value
        else:
            self.value_text = str(value)