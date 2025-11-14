from django import forms
from .models import AuthorProfile
import json


class AuthorProfileForm(forms.ModelForm):
    class Meta:
        model = AuthorProfile
        fields = '__all__'

