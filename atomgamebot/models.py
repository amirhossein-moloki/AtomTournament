from django.db import models
from django.conf import settings
from .tasks import create_bot_article

class BotSettings(models.Model):
    """
    Settings for the AtomGameBot.
    This model is intended to hold a single instance of settings.
    """
    name = models.CharField(max_length=100, default="AtomGameBot", unique=True)
    is_active = models.BooleanField(
        default=False,
        help_text="Activate the bot to start its tasks. Deactivate to stop."
    )
    author = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="The user account that will be the author of posts created by the bot."
    )

    def __str__(self):
        return f"{self.name} Settings"

    def save(self, *args, **kwargs):
        """
        Overrides the save method to trigger the bot's task on activation.
        Handles both creation of an active bot and updating a bot to be active.
        """
        is_new = self.pk is None

        # For updates, check if the status changed from False to True
        if not is_new:
            original = BotSettings.objects.get(pk=self.pk)
            if not original.is_active and self.is_active:
                create_bot_article.delay()

        super().save(*args, **kwargs)

        # For new instances, trigger if created as active
        if is_new and self.is_active:
            create_bot_article.delay()

    class Meta:
        verbose_name = "AtomGameBot Settings"
        verbose_name_plural = "AtomGameBot Settings"
