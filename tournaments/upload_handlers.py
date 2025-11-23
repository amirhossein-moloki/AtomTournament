from django.core.exceptions import ValidationError
from django.core.files.uploadhandler import TemporaryFileUploadHandler


class SafeFileUploadHandler(TemporaryFileUploadHandler):
    """
    Custom file upload handler to validate file type and size.
    """

    def __init__(self, request=None):
        super().__init__(request)
        # Allow larger and more common media types for post content uploads.
        # Most modern phone photos exceed 5 MB and many browsers use WebP by
        # default, so we raise the limit to 20 MB and permit WebP/GIF images in
        # addition to the existing formats.
        self.max_size = 1024 * 1024 * 20  # 20 MB
        self.allowed_content_types = [
            "image/jpeg",
            "image/png",
            "image/webp",
            "image/gif",
            "video/mp4",
        ]
        self.file_size = 0

    def receive_data_chunk(self, raw_data, start):
        self.file_size += len(raw_data)
        if self.file_size > self.max_size:
            raise ValidationError(
                f"File size exceeds the limit of {self.max_size} bytes."
            )
        return super().receive_data_chunk(raw_data, start)

    def file_complete(self, file_size):
        self.file.content_type = self.content_type
        if self.content_type not in self.allowed_content_types:
            raise ValidationError(f"Invalid content type: {self.content_type}")
        return super().file_complete(file_size)
