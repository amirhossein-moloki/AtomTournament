from django_summernote.models import Attachment
from django_summernote.utils import get_attachment_storage
from django.utils.translation import gettext_lazy as _
from common.utils.images import convert_image_to_webp


class CustomAttachment(Attachment):
    def save(self, *args, **kwargs):
        request = kwargs.pop('request', None)
        if request is None:
            raise ValueError("The request object is required to save a CustomAttachment.")

        from blog.models import Media
        from django.core.files.storage import default_storage

        is_image = 'image' in self.file.file.content_type
        file_to_save = self.file
        if is_image and not self.file.name.lower().endswith(".webp"):
            file_to_save = convert_image_to_webp(self.file)

        # Save the file to the default storage
        storage_key = default_storage.save(file_to_save.name, file_to_save)
        file_url = default_storage.url(storage_key)

        # Create a Media object
        media = Media(
            storage_key=storage_key,
            url=file_url,
            type='image' if is_image else 'video' if 'video' in self.file.file.content_type else 'file',
            mime='image/webp' if is_image else self.file.file.content_type,
            size_bytes=file_to_save.size,
            title=self.name,
            uploaded_by=request.user,
        )
        media.save()

        # Override the file url with the media url
        self.url = media.url

        super().save(*args, **kwargs)

    class Meta:
        proxy = True
        verbose_name = _('Attachment')
        verbose_name_plural = _('Attachments')
