
import logging
from .middleware import get_current_request_id

class RequestIDFilter(logging.Filter):
    """
    A logging filter that injects the current request_id into log records.
    """
    def filter(self, record):
        record.request_id = get_current_request_id()
        return True
