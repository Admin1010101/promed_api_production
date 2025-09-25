from django.apps import AppConfig

class ProviderAuthConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'provider_auth'
    
    def ready(self):
        import provider_auth.signals
