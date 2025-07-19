from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
# from smsir_python import Smsir

# sms = Smsir(settings.SMSIR_API_KEY, settings.SMSIR_LINE_NUMBER)

@shared_task
def send_sms_notification(phone_number, context):
    """
    Sends an SMS notification using sms.ir.
    """
    # message = render_to_string("notifications/sms/tournament_joined.txt", context)
    # sms.send(message, phone_number)
    pass
    pass


@shared_task
def send_email_notification(email, subject, context):
    """
    Sends an email notification.
    """
    html_message = render_to_string(
        "notifications/email/tournament_joined.html", context
    )
    send_mail(
        subject,
        None,
        settings.EMAIL_HOST_USER,
        [email],
        fail_silently=False,
        html_message=html_message,
    )
