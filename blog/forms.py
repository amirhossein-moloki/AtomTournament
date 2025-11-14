from django import forms
from .models import AuthorProfile
import json


class AuthorProfileForm(forms.ModelForm):
    class Meta:
        model = AuthorProfile
        fields = '__all__'

    def clean_social_links(self):
        social_links = self.cleaned_data.get('social_links', '{}')
        if isinstance(social_links, str):
            try:
                # Replace single quotes with double quotes for JSON compatibility
                social_links = social_links.replace("'", '"')
                return json.loads(social_links)
            except json.JSONDecodeError:
                raise forms.ValidationError("Invalid JSON format for social links.")
        return social_links
