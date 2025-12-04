from django.urls import path
import orders.views as api_views

urlpatterns = [
    path('orders/', api_views.CreateOrderView.as_view(), name='create-order'),
    path('order-history/', api_views.ProviderOrderHistoryView.as_view(), name='order-history'),
    path('invoice/<int:order_id>/', api_views.InvoicePDFView.as_view(), name='order-invoice-pdf'),
    path('carekit/create/', api_views.create_carekit_order, name='create-carekit-order'),
    path('recent/', api_views.get_recent_orders, name='recent-orders'),
    path('<int:order_id>/reorder/', api_views.reorder_carekit, name='reorder-carekit'),

]