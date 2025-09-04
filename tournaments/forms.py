from django import forms

class SeedDataForm(forms.Form):
    users = forms.IntegerField(
        label="تعداد کاربران",
        required=False,
        min_value=0,
        help_text="تعداد کاربران جدیدی که باید ایجاد شوند."
    )
    teams = forms.IntegerField(
        label="تعداد تیم‌ها",
        required=False,
        min_value=0,
        help_text="تعداد تیم‌های جدیدی که باید ایجاد شوند."
    )
    tournaments = forms.IntegerField(
        label="تعداد تورنومنت‌ها",
        required=False,
        min_value=0,
        help_text="تعداد تورنومنت‌های جدیدی که باید ایجاد شوند."
    )
    matches = forms.IntegerField(
        label="تعداد مسابقات",
        required=False,
        min_value=0,
        help_text="تعداد مسابقات جدیدی که باید ایجاد شوند."
    )
    transactions = forms.IntegerField(
        label="تعداد تراکنش‌ها",
        required=False,
        min_value=0,
        help_text="تعداد تراکنش‌های جدیدی که باید ایجاد شوند."
    )
    chats = forms.IntegerField(
        label="تعداد پیام‌های چت",
        required=False,
        min_value=0,
        help_text="تعداد پیام‌های چت جدیدی که باید ایجاد شوند."
    )
    clean = forms.BooleanField(
        label="پاک‌سازی دیتابیس",
        required=False,
        help_text="اگر انتخاب شود، تمام داده‌های تستی موجود قبل از ساخت داده‌های جدید پاک خواهند شد."
    )

    def clean(self):
        cleaned_data = super().clean()
        # Ensure at least one field has a value greater than 0
        if not any(cleaned_data.get(field) for field in self.fields if isinstance(self.fields[field], forms.IntegerField) and cleaned_data.get(field, 0) > 0):
            raise forms.ValidationError("حداقل باید تعداد یکی از موارد برای ساخت مشخص شود.", code='no_action')
        return cleaned_data
