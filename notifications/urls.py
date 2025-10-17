from django.urls import path
from .views import NotificationListCreateView, MarkNotificationReadView, UnreadNotificationCountView, NotificationDeleteView, BroadcastNotificationView

urlpatterns = [
    path('notifications/', NotificationListCreateView.as_view(), name='notification-list-create'),
    path('notifications/unread-count/', UnreadNotificationCountView.as_view(), name='notification-unread-count'),
    path('<int:pk>/mark-read/', MarkNotificationReadView.as_view(), name='notification-mark-read'),
    path('<int:pk>/delete-notification/', NotificationDeleteView.as_view(), name='notification-delete'),
    path('notifications/broadcast/', BroadcastNotificationView.as_view(), name='notifications-broadcast'),
]



