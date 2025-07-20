from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from smsir_python import Smsir

sms = Smsir(settings.SMSIR_API_KEY, settings.SMSIR_LINE_NUMBER)

@shared_task
def send_sms_notification(phone_number, context):
    """
    Sends an SMS notification using sms.ir.
    """
    message = render_to_string("notifications/sms/tournament_joined.txt", context)
    sms.send(message, phone_number)


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


@shared_task
def send_tournament_credentials(tournament_id):
    """
    Sends tournament credentials to all participants.
    """
    from tournaments.models import Tournament

    tournament = Tournament.objects.get(id=tournament_id)
    participants = tournament.participants.all()
    context = {
        "tournament_name": tournament.name,
        "room_id": "your_room_id",  # Replace with actual room ID
        "password": "your_password",  # Replace with actual password
    }
    for participant in participants:
        if participant.user.email:
            send_email_notification.delay(
                participant.user.email, "Tournament Credentials", context
            )
        if participant.user.phone_number:
            send_sms_notification.delay(str(participant.user.phone_number), context)
