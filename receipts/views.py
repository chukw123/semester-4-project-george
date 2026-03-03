import json
import base64
import io
from datetime import datetime, timedelta
from decimal import Decimal

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import UserCreationForm
from django.http import JsonResponse
from django.db.models import Sum, Count, Avg, Q
from django.utils import timezone
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST
from django.conf import settings

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.backends.backend_agg import FigureCanvasAgg

from .models import Receipt, ReceiptItem, ExpenseBudget
from .ocr_service import receipt_ocr


def home(request):
    """Home page view."""
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'receipts/home.html')


def signup(request):
    """User registration view."""
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('dashboard')
    else:
        form = UserCreationForm()
    return render(request, 'receipts/signup.html', {'form': form})


@login_required
def dashboard(request):
    """Main dashboard with expense overview."""
    # Get date range (default: current month)
    today = timezone.now().date()
    start_of_month = today.replace(day=1)
    
    # Get user's receipts for current month
    monthly_receipts = Receipt.objects.filter(
        user=request.user,
        receipt_date__gte=start_of_month,
        receipt_date__lte=today
    )
    
    # Calculate statistics
    total_spent = monthly_receipts.aggregate(
        total=Sum('total_amount')
    )['total'] or Decimal('0')
    
    receipt_count = monthly_receipts.count()
    
    avg_receipt = monthly_receipts.aggregate(
        avg=Avg('total_amount')
    )['avg'] or Decimal('0')
    
    # Category breakdown for current month
    category_spending = monthly_receipts.values('category').annotate(
        total=Sum('total_amount'),
        count=Count('id')
    ).order_by('-total')
    
    # Recent receipts
    recent_receipts = Receipt.objects.filter(
        user=request.user
    ).order_by('-created_at')[:5]
    
    # Tax deductible amount for current year
    tax_deductible_total = Receipt.objects.filter(
        user=request.user,
        is_tax_deductible=True,
        tax_year=today.year
    ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
    
    context = {
        'total_spent': total_spent,
        'receipt_count': receipt_count,
        'avg_receipt': avg_receipt,
        'category_spending': category_spending,
        'recent_receipts': recent_receipts,
        'tax_deductible_total': tax_deductible_total,
        'current_month': today.strftime('%B %Y'),
    }
    
    return render(request, 'receipts/dashboard.html', context)


@login_required
def upload_receipt(request):
    """Handle receipt upload and OCR processing."""
    if request.method == 'POST':
        # Handle file upload
        if 'receipt_image' in request.FILES:
            image = request.FILES['receipt_image']
            
            # Create receipt record
            receipt = Receipt.objects.create(
                user=request.user,
                image=image,
                processing_status='processing'
            )
            
            # Process with OCR
            try:
                result = receipt_ocr.process_receipt(receipt.image.path)
                
                if result['success']:
                    # Update receipt with extracted data
                    receipt.merchant_name = result['merchant_name']
                    receipt.receipt_date = result['receipt_date']
                    receipt.receipt_time = result['receipt_time']
                    receipt.receipt_number = result['receipt_number']
                    receipt.subtotal = result['subtotal']
                    receipt.tax_amount = result['tax_amount']
                    receipt.tip_amount = result['tip_amount']
                    receipt.total_amount = result['total_amount']
                    receipt.category = result['category']
                    receipt.raw_ocr_text = result['raw_text']
                    receipt.processing_status = 'completed'
                    receipt.save()
                    
                    # Create receipt items
                    for item_data in result['items']:
                        ReceiptItem.objects.create(
                            receipt=receipt,
                            description=item_data['description'],
                            quantity=item_data['quantity'],
                            unit_price=item_data['unit_price'],
                            total_price=item_data['total_price']
                        )
                    
                    return JsonResponse({
                        'success': True,
                        'receipt_id': str(receipt.id),
                        'data': {
                            'merchant_name': result['merchant_name'],
                            'receipt_date': result['receipt_date'].isoformat() if result['receipt_date'] else None,
                            'total_amount': str(result['total_amount']) if result['total_amount'] else None,
                            'category': result['category'],
                        }
                    })
                else:
                    receipt.processing_status = 'failed'
                    receipt.save()
                    return JsonResponse({
                        'success': False,
                        'error': result.get('error', 'OCR processing failed')
                    })
                    
            except Exception as e:
                receipt.processing_status = 'failed'
                receipt.save()
                return JsonResponse({
                    'success': False,
                    'error': str(e)
                })
        
        return JsonResponse({
            'success': False,
            'error': 'No image provided'
        })
    
    return render(request, 'receipts/upload.html')


@login_required
def receipt_list(request):
    """List all receipts with filtering and pagination."""
    # Get filter parameters
    category = request.GET.get('category', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    search = request.GET.get('search', '')
    
    # Base queryset
    receipts = Receipt.objects.filter(user=request.user)
    
    # Apply filters
    if category:
        receipts = receipts.filter(category=category)
    
    if date_from:
        receipts = receipts.filter(receipt_date__gte=date_from)
    
    if date_to:
        receipts = receipts.filter(receipt_date__lte=date_to)
    
    if search:
        receipts = receipts.filter(
            Q(merchant_name__icontains=search) |
            Q(receipt_number__icontains=search) |
            Q(notes__icontains=search)
        )
    
    # Order by date
    receipts = receipts.order_by('-receipt_date')
    
    # Pagination
    paginator = Paginator(receipts, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Calculate totals
    total_amount = receipts.aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
    
    context = {
        'page_obj': page_obj,
        'total_amount': total_amount,
        'categories': Receipt.RECEIPT_CATEGORIES,
        'filters': {
            'category': category,
            'date_from': date_from,
            'date_to': date_to,
            'search': search,
        }
    }
    
    return render(request, 'receipts/receipt_list.html', context)


@login_required
def receipt_detail(request, receipt_id):
    """View receipt details."""
    receipt = get_object_or_404(Receipt, id=receipt_id, user=request.user)
    
    if request.method == 'POST':
        # Update receipt details
        receipt.merchant_name = request.POST.get('merchant_name', receipt.merchant_name)
        receipt.category = request.POST.get('category', receipt.category)
        receipt.notes = request.POST.get('notes', receipt.notes)
        receipt.is_tax_deductible = request.POST.get('is_tax_deductible') == 'on'
        
        # Parse date
        date_str = request.POST.get('receipt_date')
        if date_str:
            try:
                receipt.receipt_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                pass
        
        # Parse amounts
        total_str = request.POST.get('total_amount')
        if total_str:
            try:
                receipt.total_amount = Decimal(total_str)
            except:
                pass
        
        receipt.save()
        return redirect('receipt_detail', receipt_id=receipt.id)
    
    context = {
        'receipt': receipt,
        'items': receipt.items.all(), # type: ignore
        'categories': Receipt.RECEIPT_CATEGORIES,
    }
    
    return render(request, 'receipts/receipt_detail.html', context)


@login_required
def delete_receipt(request, receipt_id):
    """Delete a receipt."""
    receipt = get_object_or_404(Receipt, id=receipt_id, user=request.user)
    
    if request.method == 'POST':
        receipt.delete()
        return redirect('receipt_list')
    
    return render(request, 'receipts/confirm_delete.html', {'receipt': receipt})


@login_required
def expense_summary(request):
    """Expense summary and analytics view."""
    # Get date range
    today = timezone.now().date()
    
    # Default to current year
    year = int(request.GET.get('year', today.year))
    month = request.GET.get('month', '')
    
    # Base filters
    filters = {'user': request.user, 'receipt_date__year': year}
    if month:
        filters['receipt_date__month'] = int(month)
    
    receipts = Receipt.objects.filter(**filters)
    
    # Monthly spending trend
    monthly_data = Receipt.objects.filter(
        user=request.user,
        receipt_date__year=year
    ).values('receipt_date__month').annotate(
        total=Sum('total_amount'),
        count=Count('id')
    ).order_by('receipt_date__month')
    
    # Category breakdown
    category_data = receipts.values('category').annotate(
        total=Sum('total_amount'),
        count=Count('id')
    ).order_by('-total')
    
    # Top merchants
    top_merchants = receipts.exclude(merchant_name__isnull=True).values('merchant_name').annotate(
        total=Sum('total_amount'),
        count=Count('id')
    ).order_by('-total')[:10]
    
    # Statistics
    total_spent = receipts.aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
    total_receipts = receipts.count()
    avg_receipt = receipts.aggregate(avg=Avg('total_amount'))['avg'] or Decimal('0')
    
    # Tax summary
    tax_data = Receipt.objects.filter(
        user=request.user,
        is_tax_deductible=True,
        receipt_date__year=year
    ).values('category').annotate(
        total=Sum('total_amount')
    ).order_by('-total')
    
    total_tax_deductible = Receipt.objects.filter(
        user=request.user,
        is_tax_deductible=True,
        receipt_date__year=year
    ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
    
    context = {
        'year': year,
        'month': month,
        'monthly_data': monthly_data,
        'category_data': category_data,
        'top_merchants': top_merchants,
        'total_spent': total_spent,
        'total_receipts': total_receipts,
        'avg_receipt': avg_receipt,
        'tax_data': tax_data,
        'total_tax_deductible': total_tax_deductible,
        'years': range(today.year - 4, today.year + 1),
        'months': [
            (1, 'January'), (2, 'February'), (3, 'March'), (4, 'April'),
            (5, 'May'), (6, 'June'), (7, 'July'), (8, 'August'),
            (9, 'September'), (10, 'October'), (11, 'November'), (12, 'December')
        ],
    }
    
    return render(request, 'receipts/expense_summary.html', context)


@login_required
def tax_summary(request):
    """Tax summary report view."""
    # Get tax year
    today = timezone.now().date()
    tax_year = int(request.GET.get('year', today.year))
    
    # Get tax-deductible receipts
    tax_receipts = Receipt.objects.filter(
        user=request.user,
        is_tax_deductible=True,
        tax_year=tax_year
    ).order_by('category', 'receipt_date')
    
    # Category breakdown for tax
    category_summary = tax_receipts.values('category').annotate(
        total=Sum('total_amount'),
        count=Count('id')
    ).order_by('-total')
    
    # Monthly breakdown
    monthly_summary = tax_receipts.values('receipt_date__month').annotate(
        total=Sum('total_amount'),
        count=Count('id')
    ).order_by('receipt_date__month')
    
    # Totals
    total_deductions = tax_receipts.aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
    total_receipts = tax_receipts.count()
    
    # Business vs Personal split (simplified)
    business_categories = ['office', 'travel', 'utilities']
    business_total = tax_receipts.filter(
        category__in=business_categories
    ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
    
    context = {
        'tax_year': tax_year,
        'tax_receipts': tax_receipts,
        'category_summary': category_summary,
        'monthly_summary': monthly_summary,
        'total_deductions': total_deductions,
        'total_receipts': total_receipts,
        'business_total': business_total,
        'personal_total': total_deductions - business_total,
        'years': range(today.year - 4, today.year + 1),
    }
    
    return render(request, 'receipts/tax_summary.html', context)


@login_required
def spending_chart(request):
    """Generate spending charts as base64 images."""
    chart_type = request.GET.get('type', 'category')
    year = int(request.GET.get('year', timezone.now().year))
    
    # Set style
    sns.set_style("whitegrid")
    plt.rcParams['figure.figsize'] = (10, 6)
    
    fig, ax = plt.subplots()
    
    if chart_type == 'category':
        # Category pie chart
        data = Receipt.objects.filter(
            user=request.user,
            receipt_date__year=year
        ).values('category').annotate(total=Sum('total_amount')).order_by('-total')
        
        if data:
            categories = [d['category'].title() for d in data]
            values = [float(d['total']) for d in data]
            
            colors = sns.color_palette("husl", len(categories))
            ax.pie(values, labels=categories, autopct='%1.1f%%', colors=colors)
            ax.set_title(f'Spending by Category - {year}')
        else:
            ax.text(0.5, 0.5, 'No data available', ha='center', va='center')
    
    elif chart_type == 'monthly':
        # Monthly bar chart
        data = Receipt.objects.filter(
            user=request.user,
            receipt_date__year=year
        ).values('receipt_date__month').annotate(total=Sum('total_amount')).order_by('receipt_date__month')
        
        if data:
            months = [d['receipt_date__month'] for d in data]
            values = [float(d['total']) for d in data]
            month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                          'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
            labels = [month_names[m-1] for m in months]
            
            ax.bar(labels, values, color=sns.color_palette("viridis", len(labels)))
            ax.set_xlabel('Month')
            ax.set_ylabel('Amount ($)')
            ax.set_title(f'Monthly Spending - {year}')
            plt.xticks(rotation=45)
        else:
            ax.text(0.5, 0.5, 'No data available', ha='center', va='center')
    
    plt.tight_layout()
    
    # Convert to base64
    buffer = io.BytesIO()
    canvas = FigureCanvasAgg(fig)
    canvas.print_png(buffer)
    buffer.seek(0)
    image_png = buffer.getvalue()
    buffer.close()
    
    graphic = base64.b64encode(image_png).decode('utf-8')
    
    return JsonResponse({'chart': graphic})


@login_required
def api_receipts(request):
    """API endpoint for receipt data."""
    receipts = Receipt.objects.filter(user=request.user).values(
        'id', 'merchant_name', 'receipt_date', 'total_amount', 
        'category', 'is_tax_deductible'
    ).order_by('-receipt_date')[:100]
    
    data = list(receipts)
    return JsonResponse({'receipts': data})


@login_required
def api_stats(request):
    """API endpoint for dashboard statistics."""
    today = timezone.now().date()
    start_of_month = today.replace(day=1)
    
    # Monthly stats
    monthly_receipts = Receipt.objects.filter(
        user=request.user,
        receipt_date__gte=start_of_month
    )
    
    total_spent = monthly_receipts.aggregate(total=Sum('total_amount'))['total'] or 0
    receipt_count = monthly_receipts.count()
    
    # Category breakdown
    categories = monthly_receipts.values('category').annotate(
        total=Sum('total_amount')
    ).order_by('-total')
    
    return JsonResponse({
        'total_spent': float(total_spent) if total_spent else 0,
        'receipt_count': receipt_count,
        'categories': list(categories),
    })
