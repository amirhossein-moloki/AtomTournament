import logging
from django.http import JsonResponse
from django.db import connection
from django_redis import get_redis_connection
from celery import current_app

logger = logging.getLogger(__name__)

def healthz(request):
    """
    Health check endpoint.
    """
    checks = {
        'database': False,
        'redis': False,
        'celery': False,
    }
    status_code = 503

    # Check database
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            row = cursor.fetchone()
            if row and row[0] == 1:
                checks['database'] = True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")

    # Check Redis
    try:
        redis_conn = get_redis_connection("default")
        if redis_conn.ping():
            checks['redis'] = True
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")

    # Check Celery
    try:
        celery_inspect = current_app.control.inspect()
        stats = celery_inspect.stats()
        if stats:
            checks['celery'] = True
    except Exception as e:
        logger.error(f"Celery health check failed: {e}")


    if all(checks.values()):
        status_code = 200

    return JsonResponse(checks, status=status_code)
