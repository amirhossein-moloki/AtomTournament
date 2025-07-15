from django.core.exceptions import ValidationError
from django.core.files.uploadhandler import TemporaryFileUploadHandler


class SafeFileUploadHandler(TemporaryFileUploadHandler):
    """
    Custom file upload handler to validate file type and size.
    """

    def __init__(self, request=None):
        super().__init__(request)
        self.max_size = 1024 * 1024 * 5  # 5 MB
        self.allowed_content_types = ["image/jpeg", "image/png"]

    def receive_data_chunk(self, raw_data, start):
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
