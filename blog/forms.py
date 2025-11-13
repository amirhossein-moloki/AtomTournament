import json
from django import forms
from .models import AuthorProfile

class AuthorProfileForm(forms.ModelForm):
    class Meta:
        model = AuthorProfile
        fields = '__all__'

    def clean_social_links(self):
        # The data from the admin textarea will be a string.
        social_links_str = self.cleaned_data.get('social_links')

        # If the field is empty, return an empty dictionary, which is the default.
        if not social_links_str:
            return {}

        # If Django has already parsed it as a dict, return it.
        if isinstance(social_links_str, dict):
            return social_links_str

        try:
            # Attempt to parse the string as JSON.
            return json.loads(social_links_str)
        except json.JSONDecodeError:
            # If parsing fails, it might be due to single quotes.
            # We'll try to fix this common mistake.
            try:
                corrected_str = social_links_str.replace("'", '"')
                return json.loads(corrected_str)
            except json.JSONDecodeError:
                # If it still fails, raise a validation error.
                raise forms.ValidationError(
                    "فرمت JSON نامعتبر است. لطفاً از double quotes برای key و value استفاده کنید. "
                    'مثال: {"telegram": "@username", "instagram": "username"}'
                )
