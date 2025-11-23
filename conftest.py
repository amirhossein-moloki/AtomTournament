import os
import django
from django.test.runner import DiscoverRunner
from django.test.utils import setup_test_environment, teardown_test_environment

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tournament_project.settings")

test_runner = None
old_config = None


def pytest_configure():
    global test_runner, old_config
    django.setup()
    setup_test_environment()
    test_runner = DiscoverRunner()
    old_config = test_runner.setup_databases()


def pytest_sessionfinish(session, exitstatus):
    if test_runner and old_config:
        test_runner.teardown_databases(old_config)
    teardown_test_environment()
