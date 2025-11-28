from django.db.models import ImageField, FileField
from django.db.models.fields.files import ImageFieldFile, FieldFile
from common.optimization import optimize_image, optimize_video


from django.core.files.base import ContentFile

class OptimizedImageFieldFile(ImageFieldFile):
    def save(self, name, content, save=True):
        # Optimize the image before saving
        optimization_result = optimize_image(content)
        if optimization_result:
            buffer = optimization_result['buffer']
            filename = optimization_result['filename']
            # Save the optimized content
            super().save(filename, ContentFile(buffer.read()), save)
        else:
            # Save the original content if optimization fails
            super().save(name, content, save)


class OptimizedImageField(ImageField):
    attr_class = OptimizedImageFieldFile


class OptimizedVideoFieldFile(FieldFile):
    def save(self, name, content, save=True):
        # Call the parent save method first
        super().save(name, content, save)
        # Then, trigger the video optimization task
        optimize_video.delay(self.path)


class OptimizedVideoField(FileField):
    attr_class = OptimizedVideoFieldFile


class OptimizedFileFieldFile(FieldFile):
    def save(self, name, content, save=True):
        # Check the file extension
        ext = name.split('.')[-1].lower()
        if ext in ['jpg', 'jpeg', 'png', 'webp']:
            optimization_result = optimize_image(content)
            if optimization_result:
                buffer = optimization_result['buffer']
                filename = optimization_result['filename']
                super().save(filename, ContentFile(buffer.read()), save)
            else:
                super().save(name, content, save)
        else:
            super().save(name, content, save)
            if ext in ['mp4', 'mov', 'avi', 'mkv']:
                optimize_video.delay(self.path)


class OptimizedFileField(FileField):
    attr_class = OptimizedFileFieldFile
