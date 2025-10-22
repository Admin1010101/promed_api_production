from django.urls import path
from patients import views as api_views

urlpatterns = [
    path('patients/', api_views.PatientListView.as_view(), name='patient-list'),
    path('patients/<int:pk>/', api_views.PatientDetailView.as_view(), name='patient-detail'),
    path('forms/save-vr/', api_views.save_patient_vr_form, name='save-patient-vr-form'),
    path('patients/<int:patient_id>/ivr-forms/', api_views.get_patient_ivr_forms, name='patient-ivr-forms'),  # ← FIXED: Added 'patients/' prefix
]
