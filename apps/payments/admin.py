from django.contrib import admin
from .models import PaymentGateway, Payment, Refund

@admin.register(PaymentGateway)
class PaymentGatewayAdmin(admin.ModelAdmin):
    list_display = ['store', 'gateway', 'is_active', 'is_sandbox', 'created_at']
    list_filter = ['gateway', 'is_active', 'is_sandbox']
    search_fields = ['store__name_fa', 'merchant_id']
    readonly_fields = ['created_at', 'updated_at']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(store__owner=request.user)

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['order', 'gateway', 'amount', 'status', 'created_at', 'paid_at']
    list_filter = ['status', 'gateway__gateway', 'created_at']
    search_fields = ['order__order_number', 'transaction_id', 'reference_id']
    readonly_fields = ['created_at', 'paid_at', 'verified_at']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(order__store__owner=request.user)

@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    list_display = ['payment', 'amount', 'status', 'reason', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['payment__order__order_number', 'refund_id']
    readonly_fields = ['created_at', 'processed_at']
