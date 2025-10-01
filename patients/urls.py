from django.urls import path
from patients import views as api_views
urlpatterns = [
    path('patients/', api_views.PatientListView.as_view(), name='patient-list'),
    path('patients/<int:pk>/', api_views.PatientDetailView.as_view(), name='patient-detail'),
]
