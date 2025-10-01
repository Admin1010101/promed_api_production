# onboarding_ops/urls.py
from django.urls import path
from onboarding_ops import views as api_views

urlpatterns = [
    # JOTFORM WEBHOOK
    path('jotform/webhook/', api_views.jotform_webhook, name='jotform-webhook'),

    # PROVIDER FORMS (CRUD & related)
    path('forms/', api_views.ProviderFormListCreate.as_view(), name='provider-form-list'),
    path('forms/<int:pk>/', api_views.ProviderFormDetail.as_view(), name='provider-form-detail'),
    path('forms/sas-url/', api_views.GenerateSASURLView.as_view(), name='generate-sas-url'),

    # PROVIDER DOCUMENTS (FOR EMAILING)
    path('documents/upload/', api_views.DocumentUploadView.as_view(), name='document-upload-email'),
    path('documents/', api_views.ProviderDocumentListCreate.as_view(), name='provider-document-list'),
    path('documents/<int:pk>/', api_views.ProviderDocumentDetail.as_view(), name='provider-document-detail'),

]