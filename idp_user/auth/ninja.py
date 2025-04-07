import logging
from typing import Optional

from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import HttpRequest
from jwt import InvalidTokenError
from ninja.errors import HttpError
from ninja.security import HttpBearer

from idp_user.utils.functions import get_jwt_payload, authorize_request_with_idp, authorize_request_with_idp_async

logger = logging.getLogger()


class NinjaAuthBearer(HttpBearer):
    def __call__(self, request: HttpRequest):
        token = self._get_token(request)
        if not token:
            return None

        return self.authenticate(request, token)

    def _get_token(self, request: HttpRequest) -> Optional[str]:
        if token_in_header := self._get_token_from_header(request):
            return token_in_header

        if token_in_cookie := self._get_token_from_cookie(request):
            return token_in_cookie

    def _get_token_from_header(self, request: HttpRequest) -> Optional[str]:
        """
        This part of the token validation is similar top what Django ninja is doing in HttpBearer.__call__
        """
        headers = request.headers
        auth_value = headers.get(self.header)
        if not auth_value:
            return None
        parts = auth_value.split(" ")

        if parts[0].lower() != self.openapi_scheme:
            if settings.DEBUG:
                logger.error(f"Unexpected auth - '{auth_value}'")
            return None

        return " ".join(parts[1:])

    @staticmethod
    def _get_token_from_cookie(request: HttpRequest) -> Optional[str]:
        """
        When interacting with a browser, the access token is stored in a cookie.
        """
        return request.COOKIES.get("access_token")

    @staticmethod
    def _get_username(token):
        try:
            jwt_payload = get_jwt_payload(token)
        except InvalidTokenError:
            return None

        return jwt_payload.get('username')

    def authenticate(self, request, token):
        username = self._get_username(token)
        if not username:
            return None

        user_model = get_user_model()
        user = user_model.objects.filter(username=username).first()

        if user:
            request.user = user

        return user


class NinjaAuthBearerAsync(NinjaAuthBearer):
    """
    Same as NinjaAuthBearer, but just with async __call__ and authenticate methods.
    """

    async def __call__(self, request: HttpRequest):
        token = self._get_token(request)
        if not token:
            return None

        return await self.authenticate(request, token)

    async def authenticate(self, request, token):
        username = self._get_username(token)
        if not username:
            return None

        user_model = get_user_model()
        user = await user_model.objects.filter(username=username).afirst()

        if user:
            request.user = user

        return user


class NinjaAuthBearerWithIDPAuthorization(NinjaAuthBearer):
    def authenticate(self, request: HttpRequest, token: str):
        auth_error = authorize_request_with_idp(request, token)
        if auth_error:
            raise HttpError(403, auth_error)

        return super().authenticate(request, token)


class NinjaAuthBearerAsyncWithIDPAuthorization(NinjaAuthBearerAsync):
    async def authenticate(self, request: HttpRequest, token: str):
        auth_error = await authorize_request_with_idp_async(request, token)
        if auth_error:
            raise HttpError(403, auth_error)

        return await super().authenticate(request, token)
