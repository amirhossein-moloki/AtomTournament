from django_summernote.models import Attachment
from django_summernote.utils import get_attachment_storage
from django.utils.translation import gettext_lazy as _
from blog.models import Media

class CustomAttachment(Attachment):
    def save(self, *args, **kwargs):
        # Do not save the attachment to the default summernote table
        # Instead, save it to the Media model

        media = Media(
            storage_key=self.file.name,
            url=self.file.url,
            type='image',  # Assuming all attachments are images for now
            mime=self.file.file.content_type,
            size_bytes=self.file.size,
            title=self.name,
            uploaded_by=self.uploaded_by,
        )
        media.save()

        # Override the file url with the media url
        self.url = media.url

        # Do not call super().save() as we don't want to use the default table
        pass

    class Meta:
        proxy = True
        verbose_name = _('Attachment')
        verbose_name_plural = _('Attachments')
