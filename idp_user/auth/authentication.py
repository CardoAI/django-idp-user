import logging
from typing import Callable, List, Literal, Optional

import jwt
from django.conf import settings
from rest_framework import authentication
from rest_framework.request import Request

from idp_user.models.user import User
from idp_user.utils.exceptions import AuthenticationError, MissingHeaderError
from idp_user.utils.functions import get_or_none
from idp_user.utils.typing import JwtData

logger = logging.getLogger(__name__)

APP_IDENTIFIER = settings.IDP_USER_APP.get("APP_IDENTIFIER")
IDP_URL = settings.IDP_USER_APP.get("IDP_URL")


class AuthenticationBackend(authentication.TokenAuthentication):
    @classmethod
    def _access_token_required(cls, request: Request):
        try:
            cls._header_required(
                request, "Authorization", "token", lambda x: x.startswith("Bearer ")
            )
        except MissingHeaderError as e:
            raise AuthenticationError("Missing Token.") from e

    @classmethod
    def _header_required(
        cls,
        request: Request,
        header: str,
        header_human_name: str,
        validation_func: Optional[Callable] = None,
    ):
        header = cls._get_request_header(request, header)
        if not header:
            raise MissingHeaderError(header_human_name)
        if validation_func and not validation_func(header):
            raise MissingHeaderError(header_human_name)

    @classmethod
    def _get_access_token(cls, request: Request) -> str:
        auth_header = cls._get_request_header(request, "Authorization")
        return auth_header.replace("Bearer ", "")

    @classmethod
    def _get_jwt_payload(cls, request: Request) -> JwtData:
        try:
            # Signature already verified from ingress before
            data = jwt.decode(
                cls._get_access_token(request),
                algorithms=["HS256"],
                options={"verify_signature": False},
            )
        except Exception as e:
            raise AuthenticationError("Invalid token.") from e
        return data

    @classmethod
    def _verify_jwt_claims(cls, jwt_data: JwtData, claims: List[Literal["username"]]):
        for claim in claims:
            cls._verify_jwt_claim(jwt_data, claim)

    @classmethod
    def _verify_jwt_claim(cls, jwt_data: JwtData, claim: Literal["username"]):
        try:
            jwt_data[claim]
        except KeyError as e:
            raise AuthenticationError("Invalid token.") from e

    @staticmethod
    def _get_request_header(request: Request, header: str) -> str:
        return request.headers.get(header) or request.META.get(header)

    @staticmethod
    def _get_user(username: str) -> Optional[User]:
        return get_or_none(User.objects, username=username)

    def authenticate(self, request: Request):
        try:
            self._access_token_required(request)
            jwt_data = self._get_jwt_payload(request)
            self._verify_jwt_claims(jwt_data, ["username"])
            user = self._get_user(jwt_data["username"])
            auth = self
        except (AuthenticationError, MissingHeaderError):
            user = None
            auth = None
        return user, auth
