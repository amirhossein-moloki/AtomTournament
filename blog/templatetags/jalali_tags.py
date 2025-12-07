from django import template
from jalali_date import date2jalali

register = template.Library()

@register.filter(name='jalali_date')
def to_jalali_date(gregorian_date):
    if gregorian_date:
        return date2jalali(gregorian_date).strftime('%Y/%m/%d')
    return ''
