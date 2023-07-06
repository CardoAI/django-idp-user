import jwt
import pytest
from unittest import mock
from idp_user.auth.authentication import AuthenticationBackend, AuthenticationError, MissingHeaderError
from idp_user.models.user import User
from idp_user.utils.typing import JwtData


class TestAuthenticationBackend:
    jwt_data: JwtData = {"other_claim": "value"}

    @pytest.fixture(autouse=True)
    def setup(self, auth_backend, mock_request):
        self._auth_backend = auth_backend
        self._mock_request = mock_request

    def test_access_token_required_missing_token(self):
        with mock.patch("idp_user.auth.authentication.AuthenticationBackend._get_request_header", return_value=None):
            with pytest.raises(AuthenticationError):
                self._auth_backend._access_token_required(self._mock_request)

    def test_header_required_missing_header(self):
        with pytest.raises(MissingHeaderError):
            self._mock_request.headers.get.return_value = None
            self._mock_request.META.get.return_value = None
            self._auth_backend._header_required(self._mock_request, "Header", "header")

    def test_get_access_token(self):
        self._mock_request.headers.get.return_value = "Bearer access_token"
        assert self._auth_backend._get_access_token(self._mock_request) == "access_token"

    def test_get_jwt_payload_invalid_token(self):
        with mock.patch("jwt.decode", side_effect=jwt.exceptions.InvalidTokenError):
            with pytest.raises(AuthenticationError):
                self._auth_backend._get_jwt_payload(self._mock_request)

    def test_verify_jwt_claims_missing_claim(self):
        with pytest.raises(AuthenticationError):
            self._auth_backend._verify_jwt_claims(self.jwt_data, ["username"])

    def test_verify_jwt_claim_missing_claim(self):
        with pytest.raises(AuthenticationError):
            self._auth_backend._verify_jwt_claim(self.jwt_data, "username")

    def test_get_request_header(self):
        self._mock_request.headers.get.return_value = "value"
        assert self._auth_backend._get_request_header(self._mock_request, "Header") == "value"

    def test_get_user(self):
        User.objects.create(username="test_user")
        assert AuthenticationBackend._get_user("test_user") is not None

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
