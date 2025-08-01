from django.apps import AppConfig


class ThemesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.themes'
    verbose_name = 'قالب‌ها'
    
    def ready(self):
        import apps.themes.signals
