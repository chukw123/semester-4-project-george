from django.db import models
from django.contrib.auth.models import User
import uuid
from decimal import Decimal


class Receipt(models.Model):
    """Model for storing receipt data with OCR-extracted information."""
    
    RECEIPT_CATEGORIES = [
        ('food', 'Food & Dining'),
        ('transport', 'Transportation'),
        ('office', 'Office Supplies'),
        ('utilities', 'Utilities'),
        ('travel', 'Travel'),
        ('healthcare', 'Healthcare'),
        ('entertainment', 'Entertainment'),
        ('shopping', 'Shopping'),
        ('other', 'Other'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='receipts')
    
    # Image file
    image = models.ImageField(upload_to='receipts/%Y/%m/')
    
    # OCR Extracted Data
    merchant_name = models.CharField(max_length=255, blank=True, null=True)
    merchant_address = models.TextField(blank=True, null=True)
    receipt_date = models.DateField(blank=True, null=True)
    receipt_time = models.TimeField(blank=True, null=True)
    receipt_number = models.CharField(max_length=100, blank=True, null=True)
    
    # Financial Data
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    tip_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    
    # Categorization
    category = models.CharField(max_length=20, choices=RECEIPT_CATEGORIES, default='other')
    
    # Tax-related fields
    is_tax_deductible = models.BooleanField(default=False)
    tax_year = models.IntegerField(blank=True, null=True)
    
    # Raw OCR text for reference
    raw_ocr_text = models.TextField(blank=True, null=True)
    
    # Processing status
    processing_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('processing', 'Processing'),
            ('completed', 'Completed'),
            ('failed', 'Failed'),
        ],
        default='pending'
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['-receipt_date', '-created_at']
        indexes = [
            models.Index(fields=['user', 'receipt_date']),
            models.Index(fields=['user', 'category']),
            models.Index(fields=['user', 'tax_year']),
        ]
    
    def __str__(self):
        return f"{self.merchant_name or 'Unknown'} - ${self.total_amount or 0} ({self.receipt_date or 'No date'})"
    
    def save(self, *args, **kwargs):
        # Auto-set tax year from receipt date
        if self.receipt_date and not self.tax_year:
            self.tax_year = self.receipt_date.year
        super().save(*args, **kwargs)


class ReceiptItem(models.Model):
    """Individual line items from a receipt."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    receipt = models.ForeignKey(Receipt, on_delete=models.CASCADE, related_name='items')
    
    description = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=10, decimal_places=3, default=Decimal('1'))
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Optional category override for individual items
    category = models.CharField(max_length=20, choices=Receipt.RECEIPT_CATEGORIES, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-total_price']
    
    def __str__(self):
        return f"{self.description} - ${self.total_price}"


class ExpenseBudget(models.Model):
    """Budget tracking for different categories."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='budgets')
    
    category = models.CharField(max_length=20, choices=Receipt.RECEIPT_CATEGORIES)
    monthly_budget = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Budget period
    year = models.IntegerField()
    month = models.IntegerField()
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'category', 'year', 'month']
        ordering = ['-year', '-month', 'category']
    
    def __str__(self):
        return f"{self.get_category_display()} - {self.month}/{self.year}: ${self.monthly_budget}" # type: ignore
    
    @property
    def spent_amount(self):
        """Calculate total spent in this category for the budget period."""
        from django.db.models import Sum
        total = Receipt.objects.filter(
            user=self.user,
            category=self.category,
            receipt_date__year=self.year,
            receipt_date__month=self.month
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        return total
    
    @property
    def remaining_budget(self):
        return self.monthly_budget - self.spent_amount
    
    @property
    def budget_percentage_used(self):
        if self.monthly_budget > 0:
            return (self.spent_amount / self.monthly_budget) * 100
        return 0
