# blog/services.py
import mimetypes
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from common.utils.images import convert_image_to_webp


class AttachmentService:
    def __init__(self, attachment_instance, request=None):
        self.attachment = attachment_instance
        self.request = request
        self.file_obj = self.attachment.file

    def get_uploader(self):
        if self.request:
            user = getattr(self.request, "user", None)
            if getattr(user, "is_authenticated", False):
                return user
        return None

    def get_content_type(self):
        content_type = getattr(getattr(self.file_obj, "file", None), "content_type", None)
        if content_type is None:
            guessed_type, _ = mimetypes.guess_type(getattr(self.file_obj, "name", ""))
            content_type = guessed_type or "application/octet-stream"
        return content_type

    def process_and_save_attachment(self):
        from blog.models import Media

        try:
            if not self.attachment.name:
                self.attachment.name = getattr(self.file_obj, "name", "") or "attachment"

            content_type = self.get_content_type()
            is_image = "image" in content_type
            file_to_save = self.file_obj

            if is_image and not self.file_obj.name.lower().endswith(".webp"):
                file_to_save = convert_image_to_webp(self.file_obj)
                content_type = "image/webp"

            # Use a temporary variable to avoid RecursionError
            temp_file = file_to_save
            self.attachment.file.save(temp_file.name, temp_file, save=False)

            storage_key = self.attachment.file.name
            file_url = self.attachment.file.storage.url(storage_key)

            uploader = self.get_uploader()

            media = Media(
                storage_key=storage_key,
                url=file_url,
                type="image" if is_image else "video" if "video" in content_type else "file",
                mime=content_type,
                size_bytes=self.attachment.file.size,
                title=self.attachment.name,
                uploaded_by=uploader,
            )
            media.save()

            self.attachment.url = self.attachment.file.url
            return self.attachment

        except Exception as e:
            raise ValidationError(
                _("امکان پردازش فایل آپلود شده وجود ندارد. لطفاً از فرمت معتبر استفاده کنید. خطا: %(error)s"),
                code='invalid_file',
                params={'error': str(e)},
            )

def process_attachment(attachment_instance, request=None):
    """Factory function to get and run the service."""
    service = AttachmentService(attachment_instance, request)
    return service.process_and_save_attachment()
