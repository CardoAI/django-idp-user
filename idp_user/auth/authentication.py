import logging
import os
from typing import Optional, Callable, Literal, List, Dict

import jwt
import requests
from django.conf import settings
from django.contrib.auth.backends import ModelBackend
from rest_framework import authentication
from rest_framework.request import Request

from idp_user.models import User
from idp_user.typing import JwtData
from idp_user.utils.exceptions import AuthenticationError, MissingHeaderError

logger = logging.getLogger(__name__)

APP_IDENTIFIER = settings.IDP_USER_APP.get("APP_IDENTIFIER")
BASE_URL = settings.IDP_USER_APP.get("IDP_URL")

# Allow header injection only if in Development Environment, for testing purposes
INJECT_HEADERS = settings.IDP_USER_APP.get("INJECT_HEADERS_IN_DEV", False) and settings.APP_ENV == 'development'


class AuthenticationBackend(authentication.TokenAuthentication):

    @classmethod
    def _auth_required(cls, request: Request):
        cls._access_token_required(request)
        cls._ingress_headers_required(request)

    @classmethod
    def _access_token_required(cls, request: Request):
        try:
            cls._header_required(request, 'Authorization', 'token', lambda x: x.startswith('Bearer '))
        except MissingHeaderError:
            raise AuthenticationError("Missing Token.")

    @classmethod
    def _ingress_headers_required(cls, request: Request):
        cls._header_required(request, 'X-USER-ID', 'User ID', lambda x: x.isdigit())
        cls._header_required(request, 'X-ROLES-FUNCTIONALITIES', 'roles functionalities')

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
    def _verify_user_id(cls, request: Request, jwt_data: JwtData):
        if not int(cls._get_request_header(request, 'X-USER-ID')) == jwt_data['user_id']:
            raise AuthenticationError('Invalid token.')

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
    def _verify_jwt_claims(cls, jwt_data: JwtData, claims: List[Literal['user_id']]):
        for claim in claims:
            cls._verify_jwt_claim(jwt_data, claim)

    @classmethod
    def _verify_jwt_claim(cls, jwt_data: JwtData, claim: Literal['user_id']):
        try:
            jwt_data[claim]
        except KeyError:
            raise AuthenticationError('Invalid token.')

    @staticmethod
    def _get_request_header(request: Request, header: str) -> str:
        return request.headers.get(header) or request.META.get(header)

    @staticmethod
    def _get_user(user_id: int) -> User:
        try:
            return User.objects.get(idp_user_id=user_id)
        except User.DoesNotExist:
            pass

    @staticmethod
    def _inject_headers_through_idp(request: Request):
        response = requests.get(
            url=f"{BASE_URL}/api/validate/?app={APP_IDENTIFIER}",
            headers={
                "Authorization": request.headers.get('Authorization'),
            }
        )
        if response.ok:
            # Headers dict cannot be modified, insert the headers as META,
            # that will be used by the overriden method _get_request_header
            request.META['X-USER-ID'] = response.headers.get('X-USER-ID')
            request.META['X-ROLES-FUNCTIONALITIES'] = response.headers.get('X-ROLES-FUNCTIONALITIES')
            return request

    def _skip_auth_headers_and_opa(self, request: Request):
        try:
            # Require access token
            self._access_token_required(request)
            # Get jwt payload from access token
            jwt_data = self._get_jwt_payload(request)
            # Check if required user claims are provided
            self._verify_jwt_claims(jwt_data, ['user_id'])

            return self._get_user(jwt_data['user_id']), self

        except AuthenticationError:
            return None, None

    def authenticate(self, request: Request):
        try:
            # Check if ingress headers are provided
            self._ingress_headers_required(request)

            self._access_token_required(request)

            jwt_data = self._get_jwt_payload(request)
            # Check if required user claims are provided
            self._verify_jwt_claims(jwt_data, ['user_id'])
            # Check if user id added by ingress in the request is the same as the user id in the token
            self._verify_user_id(request, jwt_data)
            # Set the user in the request for later access
            return self._get_user(jwt_data['user_id']), self

        except MissingHeaderError:
            if INJECT_HEADERS:
                request = self._inject_headers_through_idp(request)
                if not request:
                    return None, None
                return self.authenticate(request)
            else:
                return self._skip_auth_headers_and_opa(request)
        except AuthenticationError:
            return None, None


class IDPAuthBackend(ModelBackend):

    def authenticate(self, request, **kwargs):
        access_token = self.fetch_token(request)
        if not access_token:
            return None
        response = requests.get(f"{BASE_URL}/api/users/me/", headers={
            "Authorization": f"Bearer {access_token}"})
        username = response.json()["username"]
        try:
            # Assuming that username is unique identifier for the user in IDP
            return User.objects.filter(username=username).first()
        except User.DoesNotExist:
            pass

    def fetch_token(self, request) -> Optional[str]:
        res = requests.post(f"{BASE_URL}/api/login/", json=self.generate_login_payload(request))
        if res.status_code == 200:
            return res.json()['access']
        return None

    @staticmethod
    def generate_login_payload(request) -> Dict[str, str]:
        """Generate the payload needed to make request to the IDP /login path"""
        return {"username": request.POST.get("username"),
                "password": request.POST.get("password")}
