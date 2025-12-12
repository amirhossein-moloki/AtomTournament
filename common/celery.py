from celery.signals import before_task_publish, task_prerun
from .middleware import _thread_locals, get_current_request_id

@before_task_publish.connect
def propagate_request_id(sender=None, headers=None, **kwargs):
    """
    Injects the current request_id into the task headers before it's sent.
    This runs on the producer (e.g., web worker) side.
    """
    request_id = get_current_request_id()
    if request_id:
        headers['request_id'] = request_id

@task_prerun.connect
def load_request_id(sender=None, task_id=None, task=None, **kwargs):
    """
    Loads the request_id from the task headers into thread-local storage.
    This runs on the consumer (Celery worker) side.
    """
    request_id = task.request.get('request_id')
    _thread_locals.request_id = request_id

def setup_celery_signals():
    """
    This function is a placeholder to ensure the signals are registered
    when this module is imported.
    """
    pass
