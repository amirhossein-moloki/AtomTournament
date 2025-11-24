from django.db import models
from django.utils.translation import gettext_lazy as _
from blog.services import process_attachment


class CustomAttachment(models.Model):
    file = models.FileField(upload_to="attachments/")
    name = models.CharField(max_length=255, blank=True)
    url = models.URLField(blank=True)
    uploaded = models.DateTimeField(auto_now_add=True)

    def save(self, *args, request=None, **kwargs):
        # Let the service handle the heavy lifting
        process_attachment(self, request)
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = _("Attachment")
        verbose_name_plural = _("Attachments")

    def __str__(self):
        return self.name
