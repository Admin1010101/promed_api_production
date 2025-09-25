# onboarding_ops/urls.py
from django.urls import path
from onboarding_ops import views as api_views

urlpatterns = [
    # JOTFORM WEBHOOK
    path('jotform/webhook/', api_views.jotform_webhook, name='jotform-webhook'),

    # PROVIDER FORMS (CRUD & related)
    path('forms/', api_views.ProviderFormListCreate.as_view(), name='provider-form-list'),
    path('forms/<int:pk>/', api_views.ProviderFormDetail.as_view(), name='provider-form-detail'),

    # PROVIDER DOCUMENTS (FOR EMAILING)
    path('documents/upload/', api_views.DocumentUploadView.as_view(), name='document-upload-email'),
    path('documents/', api_views.ProviderDocumentListCreate.as_view(), name='provider-document-list'),
    path('documents/<int:pk>/', api_views.ProviderDocumentDetail.as_view(), name='provider-document-detail'),

    # AZURE UTILITIES (for serving files from blob storage)
    path('forms/sas-url/<str:container_name>/<path:blob_name>/', api_views.GenerateSASURLView.as_view(), name='generate-sas-url'),
    path('forms/serve/<str:blob_name>/', api_views.ServePDFFromAzure.as_view(), name='serve-pdf'), 
    path('forms/check-blob/<str:container_name>/<path:blob_name>/', api_views.CheckBlobExistsView.as_view(), name='check-blob-exists'),
]