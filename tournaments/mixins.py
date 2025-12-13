from django.contrib import messages
from django.db import models
from django.utils.text import slugify


class AdminAlertsMixin:
    """
    A mixin for the Django admin that displays alerts based on model state.
    """

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        alerts = []
        for obj in self.get_queryset(request):
            obj_alerts = self.get_object_alerts(request, obj)
            if obj_alerts:
                alerts.extend(obj_alerts)

        for level, message in alerts:
            messages.add_message(request, getattr(messages, level.upper(), messages.INFO), message)

        return super().changelist_view(request, extra_context)

    def get_object_alerts(self, request, obj):
        """
        This method can be implemented in the ModelAdmin to return a list
        of alerts for a specific object. Each alert should be a tuple of
        (level, message).
        Example: [('warning', 'This tournament has no participants.')]
        """
        return []


class SlugMixin(models.Model):
    """
    A mixin that automatically generates a unique slug from the 'name' field
    before saving the model instance.
    """

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if hasattr(self, "slug") and hasattr(self, "name") and not self.slug:
            self.slug = slugify(self.name, allow_unicode=True)
            original_slug = self.slug
            queryset = self.__class__.objects.all()
            if self.pk:
                queryset = queryset.exclude(pk=self.pk)

            counter = 1
            while queryset.filter(slug=self.slug).exists():
                counter += 1
                self.slug = f"{original_slug}-{counter}"
        super().save(*args, **kwargs)
