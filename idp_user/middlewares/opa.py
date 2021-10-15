import json
import logging
import os
from json import JSONDecodeError
from typing import Callable, List, Literal, Optional

import jwt
import requests
from django.conf import settings
from django.core.handlers.wsgi import WSGIRequest
from requests import Response

from ..models import User
from ..typing import JwtData
from ..utils.exceptions import AuthException, bad_gateway, forbidden, unauthorized

logger = logging.getLogger(__name__)


APP_IDENTIFIER = settings.IDP_USER_APP["APP_IDENTIFIER"]


class OpaAuthMiddleware:
    def __init__(self, get_response: Callable):
        self._get_response = get_response

    def __call__(self, request: WSGIRequest):

        try:
            # Require auth headers
            self._auth_required(request)
            # Get jwt payload from access token
            jwt_data = self._get_jwt_payload(request)
            # Check if required user claims are provided
            self._verify_jwt_claims(jwt_data, ['user_id', 'username'])
            # Check if user id added by ingress in the request is the same as the user id in the token
            self._verify_user_id(request, jwt_data)
            # Check if user is authorized to retrieve the resource
            self._authorize(request)

            # Set the user in the request for later access
            request.cardo_user = self._get_user(jwt_data['username'])
            return self._get_response(request)

        except AuthException as exception:
            return exception.as_response()

    @classmethod
    def _auth_required(cls, request: WSGIRequest):
        cls._access_token_required(request)
        cls._ingress_headers_required(request)

    @classmethod
    def _access_token_required(cls, request: WSGIRequest):
        cls._header_required(request, 'Authorization', 'token.', lambda x: x.startswith('Bearer '))

    @classmethod
    def _ingress_headers_required(cls, request: WSGIRequest):
        cls._header_required(request, 'X-USER-ID', 'user id.', lambda x: x.isdigit())
        cls._header_required(request, 'X-ROLES-FUNCTIONALITIES', 'roles functionalities.')

    @classmethod
    def _header_required(
            cls,
            request: WSGIRequest,
            header: str,
            header_human_name: str,
            validation_func: Optional[Callable] = None,
    ):
        header = cls._get_request_header(request, header)
        if not header:
            raise AuthException(unauthorized(f'Missing {header_human_name}'))
        if validation_func and not validation_func(header):
            raise AuthException(unauthorized(f'Invalid {header_human_name}'))

    @classmethod
    def _verify_user_id(cls, request: WSGIRequest, jwt_data: JwtData):
        if not int(cls._get_request_header(request, 'X-USER-ID')) == jwt_data['user_id']:
            raise AuthException(unauthorized('Invalid token.'))

    @classmethod
    def _get_access_token(cls, request: WSGIRequest) -> str:
        auth_header = cls._get_request_header(request, 'Authorization')
        return auth_header.replace('Bearer ', '')

    @classmethod
    def _get_jwt_payload(cls, request: WSGIRequest) -> JwtData:
        try:
            # Signature already verified from ingress before
            data = jwt.decode(cls._get_access_token(request), algorithms=['HS256'], options={'verify_signature': False})
        except Exception:
            raise AuthException(unauthorized('Invalid token.'))
        return data

    @classmethod
    def _verify_jwt_claims(cls, jwt_data: JwtData, claims: List[Literal['user_id', 'username']]):
        for claim in claims:
            cls._verify_jwt_claim(jwt_data, claim)

    @classmethod
    def _verify_jwt_claim(cls, jwt_data: JwtData, claim: Literal['user_id', 'username']):
        try:
            jwt_data[claim]
        except KeyError:
            raise AuthException(unauthorized('Invalid token.'))

    @classmethod
    def _authorize(cls, request: WSGIRequest):
        response = cls._get_opa_response(request)

        if not response.ok:
            raise AuthException(bad_gateway('Cannot authorize at the moment.'))

        try:
            response_body = response.json()
        except JSONDecodeError:
            raise AuthException(bad_gateway('Cannot authorize at the moment.'))

        if not response_body.get('result', False):
            raise AuthException(forbidden())
        return True

    @classmethod
    def _get_opa_response(cls, request: WSGIRequest) -> Response:
        url = f'http://{settings.OPA_DOMAIN}/{settings.OPA_VERSION}/data/{APP_IDENTIFIER}/{settings.APP_ENV}/allow'

        role = request.GET.get('role')
        roles_functionalities = json.loads(cls._get_request_header(request, 'X-ROLES-FUNCTIONALITIES'))
        allowed_functionalities = roles_functionalities.get(role, [])

        request_body = {
            'input': {
                'allowed_functionalities': allowed_functionalities,
                'path': cls._get_resource_path(request),
                'method': request.method,
                'role': role
            }
        }

        # Ask OPA for a policy decision
        return requests.post(url, json=request_body)

    @classmethod
    def _get_resource_path(cls, request: WSGIRequest) -> str:
        # Get the path as a list (removing leading and trailing /)
        request_path_as_list = request.path.strip('/').split('/')
        # Remove id values from path and add <id> as placeholder instead
        request_path_as_list = [p if not p.isdigit() else '<id>' for p in request_path_as_list]
        return '/'.join(request_path_as_list)

    @staticmethod
    def _get_request_header(request: WSGIRequest, header: str) -> str:
        return request.headers.get(header)

    @staticmethod
    def _get_user(username: str) -> User:
        try:
            return User.objects.get(username=username)
        except User.DoesNotExist:
            raise AuthException(unauthorized())


class OpaAuthMiddlewareDev(OpaAuthMiddleware):

    def __call__(self, request: WSGIRequest):
        try:
            # Check if ingress headers are provided
            self._ingress_headers_required(request)

        except AuthException:
            if settings.IDP_USER_APP.get('USE_LOCAL_IDP_IN_DEV', False):
                # Ingress headers not available, call the IDP validate directly
                request = OpaAuthMiddlewareDev.__inject_headers_through_idp(request)
                return super().__call__(request)
            else:
                return self.__skip_auth_headers_and_opa(request)

    @staticmethod
    def __inject_headers_through_idp(request: WSGIRequest):
        response = requests.get(
            url=f"http://{os.getenv('IDP_URL')}/api/validate/?app=equalizer",
            headers={
                "Authorization": request.headers.get('Authorization'),
                "HTTP_HOST": "localhost"
            }
        )

        # Headers dict cannot be modified, insert the headers as META,
        # that will be used by the overriden method _get_request_header
        request.META['X-USER-ID'] = response.headers.get('X-USER-ID')
        request.META['X-ROLES-FUNCTIONALITIES'] = response.headers.get('X-ROLES-FUNCTIONALITIES')

        return request

    @staticmethod
    def _get_request_header(request: WSGIRequest, header: str) -> str:
        return request.headers.get(header) or request.META.get(header)

    def __skip_auth_headers_and_opa(self, request: WSGIRequest):
        try:
            # Require access token
            self._access_token_required(request)
            # Get jwt payload from access token
            jwt_data = self._get_jwt_payload(request)
            # Check if required user claims are provided
            self._verify_jwt_claims(jwt_data, ['user_id', 'username'])
            # Set the user in the request for later access
            request.cardo_user = self._get_user(jwt_data['username'])
            return self._get_response(request)

        except AuthException as exception:
            return exception.as_response()
