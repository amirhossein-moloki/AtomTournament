from celery import shared_task
from .services import generate_matches as generate_matches_service
from .services import approve_winner_submission_service


@shared_task(
    soft_time_limit=1800,  # 30 minutes soft limit
    time_limit=1900,       # ~31 minutes hard limit
)
def generate_matches_task(tournament_id):
    """
    Celery task to generate matches for a tournament.
    """
    from .models import Tournament
    try:
        tournament = Tournament.objects.get(id=tournament_id)
        generate_matches_service(tournament)
    except Tournament.DoesNotExist:
        # Handle the case where the tournament is not found
        pass

@shared_task(
    bind=True,
    autoretry_for=(Exception,), # برای تمام خطاها تلاش مجدد کن
    retry_kwargs={'max_retries': 5},
    retry_backoff=True, # با فاصله زمانی افزایشی
    retry_jitter=True, # برای جلوگیری از تداخل
    acks_late=True,
)
def approve_winner_submission_task(self, submission_id):
    """
    Celery task to approve a winner submission and pay the prize.
    """
    from .models import WinnerSubmission
    try:
        submission = WinnerSubmission.objects.get(id=submission_id)
        approve_winner_submission_service(submission)
    except WinnerSubmission.DoesNotExist:
        # Handle the case where the submission is not found
        pass
