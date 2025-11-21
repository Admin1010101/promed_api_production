# sales_rep/urls.py
from django.urls import path
from .views import SalesRepDashboardView, sales_rep_dashboard_stats

urlpatterns = [
    path('sales-rep/dashboard/', SalesRepDashboardView.as_view(), name='sales-rep-dashboard'),
    path('sales-rep/dashboard-stats/', sales_rep_dashboard_stats, name='sales-rep-dashboard-stats'),
]