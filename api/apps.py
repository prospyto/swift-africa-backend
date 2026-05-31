from django.apps import AppConfig

class ApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api'

    def ready(self):
        # L'import est maintenant bien à l'intérieur de la classe et ne se déclenchera
        # qu'une seule fois lorsque Django aura fini de charger tous les modèles.
        import api.signals