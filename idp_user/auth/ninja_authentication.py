from django.contrib.auth import get_user_model
from django.http import HttpRequest
from jwt import InvalidTokenError
from ninja.security import HttpBearer

from idp_user.utils.functions import get_jwt_payload, authorize_request_with_idp


class NinjaAuthBearer(HttpBearer):
    def authenticate(self, request, token):
        try:
            jwt_payload = get_jwt_payload(token)
        except InvalidTokenError:
            return None

        username = jwt_payload.get('username')
        if not username:
            return None

        user_model = get_user_model()
        return user_model.objects.filter(username=username).first()


class NinjaAuthBearerWithIDPAuthorization(HttpBearer):
    def authenticate(self, request: HttpRequest, token: str):
        auth_error = authorize_request_with_idp(request, token)
        if auth_error:
            return None

        return super().authenticate(request, token)
