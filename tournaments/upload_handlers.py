from django.core.exceptions import ValidationError
from django.core.files.uploadhandler import TemporaryFileUploadHandler
from django.http import JsonResponse
from django.utils.translation import gettext as _


class SafeFileUploadHandler(TemporaryFileUploadHandler):
    """
    Custom file upload handler to validate file type and size.
    """

    def __init__(self, request=None):
        super().__init__(request)
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
            raise ValidationError(_("File size exceeds the 20 MB limit."))
        return super().receive_data_chunk(raw_data, start)

    def file_complete(self, file_size):
        self.file.content_type = self.content_type
        if self.content_type not in self.allowed_content_types:
            raise ValidationError(_("Invalid file type."))
        return super().file_complete(file_size)

    def handle_raw_input(self, *args, **kwargs):
        try:
            return super().handle_raw_input(*args, **kwargs)
        except ValidationError as e:
            error_message = {"error": {"message": e.message}}
            return JsonResponse(error_message, status=400)
