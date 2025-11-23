import mimetypes
from django.db import models
from django.utils.translation import gettext_lazy as _

from common.utils.images import convert_image_to_webp


class CustomAttachment(models.Model):
    file = models.FileField(upload_to="attachments/")
    name = models.CharField(max_length=255, blank=True)
    url = models.URLField(blank=True)
    uploaded = models.DateTimeField(auto_now_add=True)

    def save(self, *args, request=None, **kwargs):
        file_obj = self.file

        if not self.name:
            self.name = getattr(file_obj, "name", "") or "attachment"

        content_type = getattr(getattr(file_obj, "file", None), "content_type", None)
        if content_type is None:
            guessed_type, _ = mimetypes.guess_type(getattr(file_obj, "name", ""))
            content_type = guessed_type or "application/octet-stream"

        is_image = "image" in content_type
        file_to_save = file_obj
        if is_image and not file_obj.name.lower().endswith(".webp"):
            file_to_save = convert_image_to_webp(file_obj)
            content_type = "image/webp"

        self.file.save(file_to_save.name, file_to_save, save=False)
        storage_key = self.file.name
        file_url = self.file.storage.url(storage_key)

        from blog.models import Media

        uploader = None
        if request is not None:
            user = getattr(request, "user", None)
            if getattr(user, "is_authenticated", False):
                uploader = user

        media = Media(
            storage_key=storage_key,
            url=file_url,
            type="image" if is_image else "video" if "video" in content_type else "file",
            mime=content_type,
            size_bytes=self.file.size,
            title=self.name,
            uploaded_by=uploader,
        )
        media.save()

        self.url = self.file.url

        super().save(*args, **kwargs)

    class Meta:
        verbose_name = _("Attachment")
        verbose_name_plural = _("Attachments")

    def __str__(self):
        return self.name
