# your_project/urls.py or sales_rep/urls.py
from django.urls import path
from .views import SalesRepDashboardView

urlpatterns = [
    # ... other paths
    path('sales-rep/dashboard/', SalesRepDashboardView.as_view(), name='sales-rep-dashboard'),
]