from django import forms
from .models import Comment, Media


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ('content',)


class MediaAdminForm(forms.ModelForm):
    file = forms.FileField()

    class Meta:
        model = Media
        fields = (
            'file', 'alt_text', 'title',
            'storage_key', 'url', 'type', 'mime', 'size_bytes',
            'uploaded_by'
        )
