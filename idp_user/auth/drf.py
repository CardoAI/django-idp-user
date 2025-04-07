from typing import Optional

from jwt.exceptions import InvalidTokenError
from rest_framework import authentication
from rest_framework.authentication import get_authorization_header
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.request import Request

from idp_user.models.user import User
from idp_user.utils.functions import get_or_none, get_jwt_payload, authorize_request_with_idp
from idp_user.utils.typing import JwtData


class AuthenticationBackend(authentication.TokenAuthentication):
    keyword = "Bearer"

    def authenticate(self, request):
        token = self._get_token(request)
        if not token:
            return None

        return self.authenticate_credentials(token)

    def authenticate_credentials(self, token: str):
        user = get_or_none(User.objects, username=self._get_username(token))
        return user, self

    @classmethod
    def _get_username(cls, token) -> JwtData:
        try:
            jwt_payload = get_jwt_payload(token)
            if "username" not in jwt_payload:
                raise AuthenticationFailed("Invalid token: username not present.")
            return jwt_payload["username"]
        except InvalidTokenError as e:
            raise AuthenticationFailed(f"Invalid token: {str(e)}")

    def _get_token(self, request: Request) -> Optional[str]:
        if token_in_header := self._get_token_from_header(request):
            return token_in_header

        if token_in_cookie := self._get_token_from_cookie(request):
            return token_in_cookie

    def _get_token_from_header(self, request: Request) -> Optional[str]:
        """
        This part of the token validation is similar to what DRF is doing in TokenAuthentication.authenticate
        """
        auth = get_authorization_header(request).split()

        if not auth:
            return None

        if auth[0].lower() != self.keyword.lower().encode():
            raise AuthenticationFailed("Invalid token header: not bearer.")

        if len(auth) == 1:
            msg = 'Invalid token header. No credentials provided.'
            raise AuthenticationFailed(msg)
        elif len(auth) > 2:
            msg = 'Invalid token header. Token string should not contain spaces.'
            raise AuthenticationFailed(msg)

        try:
            token = auth[1].decode()
        except UnicodeError:
            msg = 'Invalid token header. Token string should not contain invalid characters.'
            raise AuthenticationFailed(msg)

        return token

    @staticmethod
    def _get_token_from_cookie(request: Request) -> Optional[str]:
        """
        When interacting with a browser, the access token is stored in a cookie.
        """
        return request.COOKIES.get("access_token")


class DRFAuthenticationBackendWithIDPAuthorization(AuthenticationBackend):
    def authenticate(self, request):
        token = self._get_token(request)
        if not token:
            return None

        if auth_error := authorize_request_with_idp(request, token):
            raise AuthenticationFailed(auth_error)

        return super().authenticate_credentials(token)
