import mimetypes
from django_summernote.models import Attachment
from django.utils.translation import gettext_lazy as _
from common.utils.images import convert_image_to_webp


class CustomAttachment(Attachment):
    def save(self, *args, **kwargs):
        request = kwargs.pop('request', None)

        from blog.models import Media
        from django.core.files.storage import default_storage

        content_type = getattr(getattr(self.file, 'file', None), 'content_type', None)
        if content_type is None:
            guessed_type, _ = mimetypes.guess_type(self.file.name)
            content_type = guessed_type or 'application/octet-stream'

        is_image = 'image' in content_type
        file_to_save = self.file
        if is_image and not self.file.name.lower().endswith(".webp"):
            file_to_save = convert_image_to_webp(self.file)

        # Save the file to the default storage
        storage_key = default_storage.save(file_to_save.name, file_to_save)
        file_url = default_storage.url(storage_key)

        # Create a Media object
        uploader = None
        if request is not None:
            user = getattr(request, 'user', None)
            if getattr(user, 'is_authenticated', False):
                uploader = user

        media = Media(
            storage_key=storage_key,
            url=file_url,
            type='image' if is_image else 'video' if 'video' in content_type else 'file',
            mime='image/webp' if is_image else content_type,
            size_bytes=file_to_save.size,
            title=self.name,
            uploaded_by=uploader,
        )
        media.save()

        # Override the file url with the media url
        self.url = media.url

        super().save(*args, **kwargs)

    class Meta:
        proxy = True
        verbose_name = _('Attachment')
        verbose_name_plural = _('Attachments')
