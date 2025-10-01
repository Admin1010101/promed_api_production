from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

schema_view = get_schema_view(
    openapi.Info(
      title="ProMed Health Plus Portal APIs",
      default_version='v1',
      description="This is the API documentation for ProMed Health Plus Portal project APIs",
      terms_of_service="https://www.google.com/policies/terms/",
      contact=openapi.Contact(email="william.d.chandler1@gmail.com"),
      license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    # Swagger / Redoc
    path('swagger<format>/', schema_view.with_ui(cache_timeout=0), name='schema-json'),
    path('', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    # Admin
    path('admin/', admin.site.urls),
    # App URLs
    path('api/v1/', include('provider_auth.urls')),
    path('api/v1/', include('notes.urls')),
    path('api/v1/', include('orders.urls')),
    path('api/v1/', include('product.urls')),
    path('api/v1/', include('notifications.urls')),
    path('api/v1/', include('sales_rep.urls')),
    path('api/v1/patient/', include('patients.urls')),
    path('api/v1/onboarding/', include('onboarding_ops.urls')),
    
]

# Serve media and static files in development
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)