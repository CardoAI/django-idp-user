import logging
from typing import Optional, Callable, Literal, List

import jwt
import requests
from django.conf import settings
from django.contrib.auth.backends import ModelBackend
from rest_framework import authentication, status
from rest_framework.request import Request

from idp_user.models import User
from idp_user.typing import JwtData
from idp_user.utils.exceptions import AuthenticationError, MissingHeaderError
from idp_user.utils.functions import get_or_none

logger = logging.getLogger(__name__)

APP_IDENTIFIER = settings.IDP_USER_APP.get("APP_IDENTIFIER")
IDP_URL = settings.IDP_USER_APP.get("IDP_URL")


class AuthenticationBackend(authentication.TokenAuthentication):

    @classmethod
    def _access_token_required(cls, request: Request):
        try:
            cls._header_required(request, 'Authorization', 'token', lambda x: x.startswith('Bearer '))
        except MissingHeaderError:
            raise AuthenticationError("Missing Token.")

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
        auth_header = cls._get_request_header(request, 'Authorization')
        return auth_header.replace('Bearer ', '')

    @classmethod
    def _get_jwt_payload(cls, request: Request) -> JwtData:
        try:
            # Signature already verified from ingress before
            data = jwt.decode(cls._get_access_token(request), algorithms=['HS256'], options={'verify_signature': False})
        except Exception:
            raise AuthenticationError('Invalid token.')
        return data

    @classmethod
    def _verify_jwt_claims(cls, jwt_data: JwtData, claims: List[Literal['username']]):
        for claim in claims:
            cls._verify_jwt_claim(jwt_data, claim)

    @classmethod
    def _verify_jwt_claim(cls, jwt_data: JwtData, claim: Literal['username']):
        try:
            jwt_data[claim]
        except KeyError:
            raise AuthenticationError('Invalid token.')

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
            self._verify_jwt_claims(jwt_data, ['username'])
            return self._get_user(jwt_data['username']), self
        except (AuthenticationError, MissingHeaderError):
            return None, None


class IDPAuthBackend(ModelBackend):

    def authenticate(self, request, **kwargs):
        access_token = self._fetch_token(request)
        if not access_token:
            return None

        response = requests.get(
            url=f"{IDP_URL}/api/users/me/",
            headers={
                "Authorization": f"Bearer {access_token}"
            })
        username = response.json()["username"]
        return get_or_none(User.objects, username=username)

    def _fetch_token(self, request) -> Optional[str]:
        response = requests.post(
            url=f"{IDP_URL}/api/login/",
            json={
                "username": request.POST.get("username"),
                "password": request.POST.get("password")
            })

        if response.status_code == status.HTTP_200_OK:
            return response.json()['access']
