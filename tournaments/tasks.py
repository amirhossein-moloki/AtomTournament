import logging

from celery import shared_task
from django.core.management import call_command

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=60,
    retry_backoff_max=600,
    retry_jitter=True,
    retry_kwargs={"max_retries": 3},
    soft_time_limit=900,
    time_limit=960,
    queue="long-running",
    ignore_result=True,
)
def run_seed_data_task(self, **options):
    """
    A Celery task to run the seed_data management command asynchronously.
    The options dictionary should contain the arguments for the command,
    e.g., {'users': 50, 'teams': 10, 'clean': True}
    """
    logger.info(f"Starting seed_data task with options: {options}")
    try:
        # The management command expects arguments like '--users', but call_command
        # passes them as keyword arguments without the '--'.
        # We need to filter out None values so call_command doesn't pass them.
        command_options = {k: v for k, v in options.items() if v is not None}

        call_command("seed_data", **command_options)

        logger.info("seed_data task completed successfully.")
    except Exception as exc:
        logger.error(
            "An error occurred during the seed_data task: %s", exc, exc_info=True
        )
        raise
