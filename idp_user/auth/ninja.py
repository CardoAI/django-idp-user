import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import HttpRequest
from jwt import InvalidTokenError
from ninja.errors import HttpError
from ninja.security import HttpBearer

from idp_user.utils.functions import get_jwt_payload, authorize_request_with_idp, authorize_request_with_idp_async

logger = logging.getLogger()


class NinjaAuthBearer(HttpBearer):
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
    async def authenticate(self, request, token):
        username = self._get_username(token)
        if not username:
            return None

        user_model = get_user_model()
        user = await user_model.objects.filter(username=username).afirst()

        if user:
            request.user = user

        return user

    async def __call__(self, request):
        """Same as HttpBearer.__call__ but with async authenticate method."""

        headers = request.headers
        auth_value = headers.get(self.header)
        if not auth_value:
            return None
        parts = auth_value.split(" ")

        if parts[0].lower() != self.openapi_scheme:
            if settings.DEBUG:
                logger.error(f"Unexpected auth - '{auth_value}'")
            return None
        token = " ".join(parts[1:])

        return await self.authenticate(request, token)


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
