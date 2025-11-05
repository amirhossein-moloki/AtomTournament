from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from sms_ir import SmsIr


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    retry_kwargs={"max_retries": 5},
    rate_limit="20/m",
    ignore_result=True,
)
def send_sms_notification(self, phone_number, context):
    """
    Sends an SMS notification using sms.ir.
    """
    if not settings.SMSIR_API_KEY:
        print(f"--- FAKE SMS to {phone_number}: {context} ---")
        return

    smsir = SmsIr(
        api_key=settings.SMSIR_API_KEY, line_number=settings.SMSIR_LINE_NUMBER
    )

    # Simple message formatting based on context
    if "code" in context:
        message = f"Your verification code is: {context['code']}"
    elif "tournament_name" in context:
        message = f"You have joined the tournament: {context['tournament_name']}. Room ID: {context.get('room_id', 'N/A')}"
    else:
        message = f"You have a new notification: {context}"

    # The smsir library expects a list of numbers.
    smsir.send_bulk(message, [str(phone_number)])


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    retry_kwargs={"max_retries": 4},
    ignore_result=True,
)
def send_email_notification(self, email, subject, template_name, context):
    """
    Sends an email notification using a specified template.
    """
    html_message = render_to_string(template_name, context)
    send_mail(
        subject,
        None,  # Plain text message, can be empty if HTML message is provided
        settings.EMAIL_HOST_USER,
        [email],
        fail_silently=False,
        html_message=html_message,
    )


@shared_task(ignore_result=True)
def send_tournament_credentials(tournament_id):
    """
    Sends tournament credentials to all participants for their specific matches.
    """
    from tournaments.models import Tournament

    tournament = Tournament.objects.get(id=tournament_id)

    for match in tournament.matches.all():
        # Assuming individual tournaments for simplicity. A similar logic can be applied for teams.
        if (
            match.match_type == "individual"
            and match.participant1_user
            and match.participant2_user
        ):
            participants = [match.participant1_user, match.participant2_user]

            for i, p in enumerate(participants):
                opponent = participants[1 - i]
                context = {
                    "tournament_name": tournament.name,
                    "room_id": match.room_id,
                    "password": match.password,
                    "opponent_name": opponent.username,
                }

                if p.email:
                    send_email_notification.delay(
                        p.email,
                        "Your Tournament Match Credentials",
                        "notifications/email/tournament_joined.html",
                        context,
                    )
                if p.phone_number:
                    send_sms_notification.delay(str(p.phone_number), context)
