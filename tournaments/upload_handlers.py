import magic
from django.core.exceptions import ValidationError
from django.core.files.uploadhandler import TemporaryFileUploadHandler


class SafeFileUploadHandler(TemporaryFileUploadHandler):
    """
    Custom file upload handler to validate file type and size.
    """

    def __init__(self, request=None):
        super().__init__(request)
        self.max_size = 1024 * 1024 * 5  # 5 MB
        self.allowed_content_types = ["image/jpeg", "image/png", "video/mp4"]
        self.file_size = 0

    def receive_data_chunk(self, raw_data, start):
        self.file_size += len(raw_data)
        if self.file_size > self.max_size:
            raise ValidationError(
                f"File size exceeds the limit of {self.max_size} bytes."
            )
        return super().receive_data_chunk(raw_data, start)

    def file_complete(self, file_size):
        self.file.seek(0)
        file_content = self.file.read(2048)  # Read first 2KB for MIME check
        self.file.seek(0)

        mime_type = magic.from_buffer(file_content, mime=True)

        if mime_type not in self.allowed_content_types:
            raise ValidationError(f"Invalid content type: {mime_type}")

        self.file.content_type = mime_type
        return super().file_complete(file_size)
