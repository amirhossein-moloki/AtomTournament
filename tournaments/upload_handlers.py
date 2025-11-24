# To enable the custom error handling for file uploads, add the following middleware
# to your MIDDLEWARE setting in settings.py:
# 'tournaments.upload_handlers.UploadErrorHandlerMiddleware'

from django.core.exceptions import ValidationError
from django.core.files.uploadhandler import (StopUpload, TemporaryFileUploadHandler)
from django.http import JsonResponse
from django.utils.translation import gettext as _


class UploadErrorHandlerMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            return self.get_response(request)
        except StopUpload:
            if hasattr(request, "upload_error"):
                return request.upload_error
            return JsonResponse(
                {"error": {"message": _("File upload stopped.")}}, status=400
            )


class SafeFileUploadHandler(TemporaryFileUploadHandler):
    """
    Custom file upload handler to validate file type and size, returning JSON errors.
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

    def new_file(self, *args, **kwargs):
        super().new_file(*args, **kwargs)
        if self.content_type not in self.allowed_content_types:
            error_message = {"error": {"message": _("Invalid file type.")}}
            self.request.upload_error = JsonResponse(error_message, status=400)
            raise StopUpload(connection_reset=True)

    def receive_data_chunk(self, raw_data, start):
        self.file_size += len(raw_data)
        if self.file_size > self.max_size:
            error_message = {
                "error": {"message": _("File size exceeds the 20 MB limit.")}
            }
            self.request.upload_error = JsonResponse(error_message, status=400)
            raise StopUpload(connection_reset=True)
        return super().receive_data_chunk(raw_data, start)

    def file_complete(self, file_size):
        # The content_type is already validated in new_file.
        # We still assign it here for compatibility.
        self.file.content_type = self.content_type
        return super().file_complete(file_size)
