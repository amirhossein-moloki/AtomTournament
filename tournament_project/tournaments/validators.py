from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


class FileValidator:
    def __init__(self, max_size, content_types):
        self.max_size = max_size
        self.content_types = content_types

    def __call__(self, value):
        if value.size > self.max_size:
            raise ValidationError(_(f"File size cannot exceed {self.max_size} bytes."))
        if value.content_type not in self.content_types:
            raise ValidationError(
                _(
                    f'Invalid file type. Allowed types are: {", ".join(self.content_types)}'
                )
            )
