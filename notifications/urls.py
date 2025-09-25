from django.urls import path
from .views import NotificationListCreateView, MarkNotificationReadView, UnreadNotificationCountView, NotificationDeleteView, BroadcastNotificationView

urlpatterns = [
    path('provider/notifications/', NotificationListCreateView.as_view(), name='notification-list-create'),
    path('provider/notifications/unread-count/', UnreadNotificationCountView.as_view(), name='notification-unread-count'),
    path('<int:pk>/provider/mark-read/', MarkNotificationReadView.as_view(), name='notification-mark-read'),
    path('<int:pk>/provider/delete-notification/', NotificationDeleteView.as_view(), name='notification-delete'),
    path('provider/notifications/broadcast/', BroadcastNotificationView.as_view(), name='notifications-broadcast'),
]



