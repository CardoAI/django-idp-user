import os
from unittest import mock

import pytest

from idp_user.auth.drf_authentication import AuthenticationBackend


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        # runtests()
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")


@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    """
    This fixture enables database access for all tests.
    """
    pass


@pytest.fixture
def auth_backend() -> AuthenticationBackend:
    return AuthenticationBackend()


@pytest.fixture
def mock_request():
    with mock.patch("rest_framework.request.Request"):
        request = mock.MagicMock()
        request.headers = mock.MagicMock()
        request.META = mock.MagicMock()
        return request
