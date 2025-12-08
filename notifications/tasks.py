import logging

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from sms_ir import SmsIr

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    retry_kwargs={"max_retries": 5},
    rate_limit="10/m",
    ignore_result=True,
    queue='high_priority'
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
        message = f"کد تأیید شما: {context['code']}"
    elif "tournament_name" in context:
        message = (
            f"شما به تورنمنت {context['tournament_name']} پیوستید. "
            f"شناسه اتاق: {context.get('room_id', 'نامشخص')}"
        )
    else:
        message = f"یک اعلان جدید دارید: {context}"

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
    queue='high_priority'
)
def send_email_notification(
    self, subject, message, recipient_list, html_message=None
):
    """
    Sends an email notification. It can be plain text, HTML, or both.
    """
    if not isinstance(recipient_list, list):
        recipient_list = [recipient_list]

    logger.info(
        f"Attempting to send email to {recipient_list} with subject '{subject}'"
    )
    try:
        send_mail(
            subject,
            message,
            settings.EMAIL_HOST_USER,
            recipient_list,
            fail_silently=False,
            html_message=html_message,
        )
        logger.info(f"Successfully sent email to {recipient_list}")
    except Exception as e:
        logger.error(
            f"Failed to send email to {recipient_list} with subject '{subject}'. Error: {e}",
            exc_info=True,
        )
        # Re-raise the exception to allow Celery to handle retries
        raise


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
                    # The content generation is now handled here, before calling the task.
                    html_message = render_to_string(
                        "notifications/email/tournament_joined.html", context
                    )
                    plain_message = (
                        f"شما به تورنمنت {tournament.name} پیوستید.\n"
                        f"شناسه اتاق: {context.get('room_id', 'نامشخص')}\n"
                        f"رمز عبور: {context.get('password', 'نامشخص')}"
                    )
                    send_email_notification.delay(
                        subject="اطلاعات مسابقه شما",
                        message=plain_message,
                        recipient_list=[p.email],
                        html_message=html_message,
                    )
                if p.phone_number:
                    send_sms_notification.delay(str(p.phone_number), context)
