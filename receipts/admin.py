from django.contrib import admin
from .models import Receipt, ReceiptItem, ExpenseBudget


class ReceiptItemInline(admin.TabularInline):
    """Inline admin for receipt items."""
    model = ReceiptItem
    extra = 0
    readonly_fields = ['created_at']


@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    """Admin configuration for Receipt model."""
    
    list_display = [
        'merchant_name', 'user', 'receipt_date', 'total_amount',
        'category', 'is_tax_deductible', 'processing_status'
    ]
    
    list_filter = [
        'category', 'is_tax_deductible', 'processing_status',
        'receipt_date', 'tax_year'
    ]
    
    search_fields = [
        'merchant_name', 'receipt_number', 'notes', 'raw_ocr_text'
    ]
    
    readonly_fields = [
        'id', 'created_at', 'updated_at', 'raw_ocr_text'
    ]
    
    inlines = [ReceiptItemInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'user', 'image', 'processing_status')
        }),
        ('Merchant Details', {
            'fields': ('merchant_name', 'merchant_address', 'receipt_number')
        }),
        ('Date & Time', {
            'fields': ('receipt_date', 'receipt_time', 'tax_year')
        }),
        ('Financial Details', {
            'fields': ('subtotal', 'tax_amount', 'tip_amount', 'total_amount')
        }),
        ('Categorization', {
            'fields': ('category', 'is_tax_deductible')
        }),
        ('Additional Information', {
            'fields': ('notes', 'raw_ocr_text', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ReceiptItem)
class ReceiptItemAdmin(admin.ModelAdmin):
    """Admin configuration for ReceiptItem model."""
    
    list_display = ['description', 'receipt', 'quantity', 'unit_price', 'total_price']
    list_filter = ['category', 'created_at']
    search_fields = ['description', 'receipt__merchant_name']


@admin.register(ExpenseBudget)
class ExpenseBudgetAdmin(admin.ModelAdmin):
    """Admin configuration for ExpenseBudget model."""
    
    list_display = [
        'user', 'category', 'year', 'month', 
        'monthly_budget', 'spent_amount', 'remaining_budget'
    ]
    list_filter = ['category', 'year', 'month']
    search_fields = ['user__username']
