import logging
import requests
from django.conf import settings
from pybreaker import CircuitBreaker, CircuitBreakerError

logger = logging.getLogger(__name__)

# Circuit Breaker Configuration
FAIL_MAX = settings.EXTERNAL_HTTP_FAILURE_THRESHOLD
RESET_TIMEOUT = settings.EXTERNAL_HTTP_RESET_TIMEOUT

# A dictionary to hold circuit breakers for different services
circuit_breakers = {
    'default': CircuitBreaker(fail_max=FAIL_MAX, reset_timeout=RESET_TIMEOUT),
}

class HttpClient:
    def __init__(self, service_name='default'):
        if service_name not in circuit_breakers:
            circuit_breakers[service_name] = CircuitBreaker(
                fail_max=FAIL_MAX, reset_timeout=RESET_TIMEOUT
            )
        self.breaker = circuit_breakers[service_name]

    @staticmethod
    def _get_timeout():
        return settings.EXTERNAL_HTTP_TIMEOUT_SECONDS

    def _request_wrapper(self, method, url, **kwargs):
        """Wrapper to be called by the circuit breaker."""
        response = method(url, **kwargs)
        response.raise_for_status()
        return response

    def post(self, url, **kwargs):
        kwargs.setdefault('timeout', self._get_timeout())
        try:
            return self.breaker.call(self._request_wrapper, requests.post, url, **kwargs)
        except CircuitBreakerError:
            logger.error(f"Circuit open for POST {url}")
            raise
        except requests.RequestException as e:
            logger.error(f"HTTP POST request failed: {e}")
            raise

    def get(self, url, **kwargs):
        kwargs.setdefault('timeout', self._get_timeout())
        try:
            return self.breaker.call(self._request_wrapper, requests.get, url, **kwargs)
        except CircuitBreakerError:
            logger.error(f"Circuit open for GET {url}")
            raise
        except requests.RequestException as e:
            logger.error(f"HTTP GET request failed: {e}")
            raise
