from celery import shared_task
from django.core.management import call_command
import logging

logger = logging.getLogger(__name__)

@shared_task
def run_seed_data_task(**options):
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

        call_command('seed_data', **command_options)

        logger.info("seed_data task completed successfully.")
        return "Data seeding process completed successfully."
    except Exception as e:
        logger.error(f"An error occurred during the seed_data task: {e}", exc_info=True)
        return f"An error occurred: {e}"
