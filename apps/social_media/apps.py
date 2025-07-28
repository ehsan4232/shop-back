from django.apps import AppConfig


class SocialMediaConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.social_media'
    verbose_name = 'شبکه‌های اجتماعی'
    
    def ready(self):
        """
        Import signal handlers when app is ready
        """
        import apps.social_media.models  # Import to register signals
