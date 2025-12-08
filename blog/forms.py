from django import forms
from django.contrib.admin.widgets import AdminFileWidget
from django.utils.html import format_html
from .models import Comment, Media, Page, Post
from django_ckeditor_5.widgets import CKEditor5Widget


class ImagePreviewWidget(AdminFileWidget):
    def render(self, name, value, attrs=None, renderer=None):
        output = []
        if value and getattr(value, "url", None):
            image_url = value.url
            file_name = str(value)
            output.append(
                f'<a href="{image_url}" target="_blank">'
                f'<img src="{image_url}" alt="{file_name}" width="150" height="150" '
                f'style="object-fit: cover;"/></a>'
            )
        output.append(super().render(name, value, attrs, renderer))
        return format_html(''.join(output))


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ('content',)


class PostAdminForm(forms.ModelForm):
    content = forms.CharField(widget=CKEditor5Widget(config_name="default"))

    class Meta:
        model = Post
        fields = '__all__'


class PageAdminForm(forms.ModelForm):
    content = forms.CharField(widget=CKEditor5Widget(config_name="default"))

    class Meta:
        model = Page
        fields = '__all__'


class MediaAdminForm(forms.ModelForm):
    file = forms.FileField(required=False)

    class Meta:
        model = Media
        fields = ('file', 'alt_text', 'title')
