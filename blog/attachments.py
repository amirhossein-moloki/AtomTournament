from django_summernote.models import Attachment
from django_summernote.utils import get_attachment_storage
from django.utils.translation import gettext_lazy as _


class CustomAttachment(Attachment):
    def save(self, *args, **kwargs):
        request = kwargs.pop('request', None)
        if request is None:
            raise ValueError("The request object is required to save a CustomAttachment.")

        from blog.models import Media
        from django.core.files.storage import default_storage

        # Save the file to the default storage
        storage_key = default_storage.save(self.file.name, self.file)
        file_url = default_storage.url(storage_key)

        # Create a Media object
        media = Media(
            storage_key=storage_key,
            url=file_url,
            type='image',  # Assuming all attachments are images for now
            mime=self.file.file.content_type,
            size_bytes=self.file.size,
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
