from django.urls import path
from patients import views as api_views

# patients/urls.py
urlpatterns = [
    # Patient CRUD
    path('patients/', api_views.PatientListView.as_view(), name='patient-list'),
    path('patients/<int:pk>/', api_views.PatientDetailView.as_view(), name='patient-detail'),
    
    # === IVR Forms Management ===
    
    # 1. LIST IVR forms FOR A SPECIFIC PATIENT (The URL that was causing trouble)
    #    Uses the PatientIVRFormsView, which is a DRF ListAPIView.
    # patients/urls.py
    # CRITICAL: This line MUST point to the Class-Based View (PatientIVRFormsView)
    path('patients/<int:patient_id>/ivr-forms/', api_views.PatientIVRFormsView.as_view(), name='patient-ivr-forms'),
    # 2. SUBMISSION (Function-based view remains, but needs a model update)
    path('forms/save-vr/', api_views.save_patient_vr_form, name='save-patient-vr-form'),
    
    # 3. Provider IVR endpoints (for listing/creating/managing all IVRForm objects)
    path('ivr-forms/', api_views.IVRFormListCreateView.as_view(), name='ivr-form-list-create'),
    path('ivr-forms/<int:pk>/', api_views.IVRFormDetailView.as_view(), name='ivr-form-detail'),
    path('ivr-forms/<int:pk>/withdraw/', api_views.IVRFormWithdrawView.as_view(), name='ivr-form-withdraw'),
    # ADMIN IVR MANAGEMENT (Keep these as is)
    path('admin/ivr-forms/', api_views.AdminIVRFormListView.as_view(), name='admin-ivr-form-list'),
    path('admin/ivr-forms/<int:pk>/', api_views.AdminIVRFormDetailView.as_view(), name='admin-ivr-form-detail'),
    path('admin/ivr-forms/stats/', api_views.AdminIVRStatsView.as_view(), name='admin-ivr-stats'),
]
