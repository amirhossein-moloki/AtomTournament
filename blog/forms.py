from django import forms
from .models import AuthorProfile
import json


class AuthorProfileForm(forms.ModelForm):
    class Meta:
        model = AuthorProfile
        fields = '__all__'

    def clean_social_links(self):
        social_links = self.cleaned_data.get('social_links')
        if not social_links:
            return {}

        # If it's already a dictionary (from the default widget), return it
        if isinstance(social_links, dict):
            return social_links

        # If it's a string, process it
        if isinstance(social_links, str):
            try:
                # Replace single quotes with double quotes for JSON compatibility
                social_links_str = social_links.replace("'", '"')
                return json.loads(social_links_str)
            except json.JSONDecodeError:
                raise forms.ValidationError("Invalid JSON format for social links.")

        return social_links
