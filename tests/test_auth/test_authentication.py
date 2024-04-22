from unittest import mock

import pytest

from idp_user.auth.drf import AuthenticationBackend
from idp_user.models.user import User
from idp_user.utils.typing import JwtData


class TestAuthenticationBackend:
    jwt_data: JwtData = {"other_claim": "value"}

    @pytest.fixture(autouse=True)
    def setup(self, auth_backend, mock_request):
        self._auth_backend = auth_backend
        self._mock_request = mock_request

    def test_authenticate(self):
        access_token = "access_token"
        jwt_payload = {"username": "test_user"}
        auth_header = f"Bearer {access_token}"
        self._mock_request.headers.get.return_value = auth_header
        with mock.patch.object(
                AuthenticationBackend,
                "_get_user",
                return_value=User(username=jwt_payload["username"]),
        ):
            with mock.patch("jwt.decode", return_value=jwt_payload):
                user, auth = self._auth_backend.authenticate(self._mock_request)
                assert user is not None and auth is not None
