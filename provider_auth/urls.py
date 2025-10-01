#urls
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from provider_auth import views as api_views

#urls
urlpatterns = [
    path('provider/token/', api_views.MyTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('provider/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('provider/register/', api_views.RegisterUser.as_view(), name='register'),
    path('verify-code/', api_views.VerifyCodeView.as_view(), name='verify-code'),
    path('provider/profile/', api_views.ProviderProfileView.as_view(), name='provider-profile'),
    path('provider/contact-rep/', api_views.ContactRepView.as_view(), name='contact-rep'),
    path('contact-us/', api_views.PublicContactView.as_view(), name='public-contact-us'),
    path('provider/verify-email/<uuid:token>/', api_views.VerifyEmailView.as_view(), name='verify-email'),
    path('provider/reset-password/<uuid:token>/', api_views.ResetPasswordView.as_view(), name='reset-password'),
    path('provider/request-password-reset/', api_views.RequestPasswordResetView.as_view(), name='request-password-reset'), 
]