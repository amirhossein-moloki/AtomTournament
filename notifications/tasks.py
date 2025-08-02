from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string


@shared_task
def send_sms_notification(phone_number, context):
    """
    Sends an SMS notification using sms.ir.
    This is a placeholder. The actual implementation for sending SMS
    using the sms.ir API would go here.
    """
    # from smsir_python import Smsir
    # smsir = Smsir(api_key=settings.SMSIR_API_KEY, line_number=settings.SMSIR_LINE_NUMBER)
    # message = f"Your notification: {context}" # Customize message based on context
    # smsir.send_bulk(message, [phone_number])
    print(f"--- FAKE SMS to {phone_number}: {context} ---") # Placeholder for development
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


@shared_task
def send_tournament_credentials(tournament_id):
    """
    Sends tournament credentials to all participants for their specific matches.
    """
    from tournaments.models import Tournament

    tournament = Tournament.objects.get(id=tournament_id)

    for match in tournament.matches.all():
        # Assuming individual tournaments for simplicity. A similar logic can be applied for teams.
        if match.match_type == 'individual' and match.participant1_user and match.participant2_user:
            participants = [match.participant1_user, match.participant2_user]
            context = {
                "tournament_name": tournament.name,
                "room_id": match.room_id,
                "password": match.password,
                "opponent_name": "" # Placeholder for opponent's name
            }

            for i, p in enumerate(participants):
                # Set the opponent's name for the notification context
                opponent = participants[1-i]
                context["opponent_name"] = opponent.username

                if p.email:
                    send_email_notification.delay(
                        p.email, "Your Tournament Match Credentials", context
                    )
                if p.phone_number:
                    send_sms_notification.delay(str(p.phone_number), context)
