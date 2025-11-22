from django.apps import AppConfig


class TournamentsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "tournaments"
    label = "tournaments"

    def ready(self):
        import tournaments.signals
