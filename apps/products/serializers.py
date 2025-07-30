    attributes = ProductClassAttributeSerializer(many=True, read_only=True)
    children = serializers.SerializerMethodField()
    parent_name = serializers.CharField(source='parent.name_fa', read_only=True)
    inherited_attributes = serializers.SerializerMethodField()
    inherited_media = serializers.SerializerMethodField()  # ADDED: For inherited media list
    effective_price = serializers.ReadOnlyField(source='get_effective_price')
    can_create_instances = serializers.SerializerMethodField()  # ADDED: Business rule validation
    
    class Meta:
        model = ProductClass
        fields = [
            'id', 'name', 'name_fa', 'slug', 'description', 'parent', 'parent_name',
            'base_price', 'media_list', 'icon', 'image', 'display_order', 'is_active', 'is_leaf',  # ADDED: media_list
            'product_count', 'attributes', 'children', 'inherited_attributes', 'inherited_media',  # ADDED: inherited_media
            'effective_price', 'can_create_instances', 'created_at', 'updated_at'  # ADDED: can_create_instances
        ]
        read_only_fields = ['is_leaf', 'product_count']
    
    def get_children(self, obj):
        """Get immediate children classes"""
        children = obj.get_children().filter(is_active=True)
        return ProductClassSerializer(children, many=True, context=self.context).data
    
    def get_inherited_attributes(self, obj):
        """Get all inherited attributes from ancestors"""
        return ProductClassAttributeSerializer(obj.get_inherited_attributes(), many=True).data
    
    def get_inherited_media(self, obj):
        """Get inherited media list from ancestors"""
        return obj.get_inherited_media()
    
    def get_can_create_instances(self, obj):
        """Check if this class can create product instances"""
        can_create, message = obj.can_create_product_instances()
        return {'can_create': can_create, 'message': message}