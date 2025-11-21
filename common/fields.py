from django.db import models
from django.db.models.fields.files import ImageFieldFile

from common.utils.images import convert_image_to_webp


class WebPImageFieldFile(ImageFieldFile):
    def save(self, name, content, save=True):
        file_name = getattr(content.file, "name", name)
        if not file_name.lower().endswith(".webp"):
            content = convert_image_to_webp(content)
            name = content.name
        super().save(name, content, save)


class WebPImageField(models.ImageField):
    attr_class = WebPImageFieldFile
