
import uuid
from threading import local

_thread_locals = local()

def get_current_request_id():
    """Returns the request_id for the current request."""
    return getattr(_thread_locals, 'request_id', None)

class RequestIDMiddleware:
    """
    Middleware to inject a unique request_id into each request.
    The request_id is stored in thread-local storage to be accessible
    throughout the request lifecycle.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = str(uuid.uuid4())
        _thread_locals.request_id = request_id
        response = self.get_response(request)
        response['X-Request-ID'] = request_id
        return response
