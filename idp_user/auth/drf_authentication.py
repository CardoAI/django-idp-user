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

    @classmethod
    def _get_username(cls, token) -> JwtData:
        try:
            jwt_payload = get_jwt_payload(token)
            if "username" not in jwt_payload:
                raise AuthenticationFailed("Invalid token: username not present.")
            return jwt_payload["username"]
        except InvalidTokenError as e:
            raise AuthenticationFailed(f"Invalid token: {str(e)}")

    def authenticate_credentials(self, token: str):
        user = get_or_none(User.objects, username=self._get_username(token))
        return user, self


class DRFAuthenticationBackendWithIDPAuthorization(AuthenticationBackend):
    def _get_token(self, request: Request):
        """
        This part of the token validation is the same as what DRF is doing in TokenAuthentication.authenticate
        """
        auth = get_authorization_header(request).split()

        if not auth or auth[0].lower() != self.keyword.lower().encode():
            return None

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

    def authenticate(self, request):
        token = self._get_token(request)

        if auth_error := authorize_request_with_idp(request, token):
            raise AuthenticationFailed(auth_error)

        return super().authenticate_credentials(token)
