from django import template
from django.utils.safestring import mark_safe
from jalali_date import date2jalali

register = template.Library()

@register.filter(name='jalali_date')
def to_jalali_date(gregorian_date):
    if gregorian_date:
        return date2jalali(gregorian_date).strftime('%Y/%m/%d')
    return ''

@register.filter
def jalali_admin_safe_readonly(date):
    """
    Safely formats a Jalali date for the Django admin's readonly fields.
    """
    if date:
        return mark_safe(f'<div class="jalali-date-input">{date2jalali(date).strftime("%Y/%m/%d")}</div>')
    return ''
