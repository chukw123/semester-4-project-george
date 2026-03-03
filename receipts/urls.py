from django.urls import path
from . import views

urlpatterns = [
    # Home and auth
    path('', views.home, name='home'),
    path('signup/', views.signup, name='signup'),
    
    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Receipt management
    path('upload/', views.upload_receipt, name='upload_receipt'),
    path('receipts/', views.receipt_list, name='receipt_list'),
    path('receipts/<uuid:receipt_id>/', views.receipt_detail, name='receipt_detail'),
    path('receipts/<uuid:receipt_id>/delete/', views.delete_receipt, name='delete_receipt'),
    
    # Reports and summaries
    path('expenses/', views.expense_summary, name='expense_summary'),
    path('tax-summary/', views.tax_summary, name='tax_summary'),
    
    # Charts and API
    path('api/chart/', views.spending_chart, name='spending_chart'),
    path('api/receipts/', views.api_receipts, name='api_receipts'),
    path('api/stats/', views.api_stats, name='api_stats'),
]
