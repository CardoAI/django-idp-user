import json
import logging
from json import JSONDecodeError

import requests
from django.conf import settings
from django.core.handlers.wsgi import WSGIRequest
from requests import Response
from rest_framework import permissions

from idp_user.services import OpaService

APP_IDENTIFIER = settings.IDP_USER_APP["APP_IDENTIFIER"]

logger = logging.getLogger(__name__)


class OpaCheckPermission(permissions.BasePermission):
    message = 'Opa has blocked you from accessing the resource!'

    @classmethod
    def _get_opa_response(cls, request: WSGIRequest) -> Response:
        opa_domain = settings.IDP_USER_APP['OPA_DOMAIN']
        opa_version = settings.IDP_USER_APP['OPA_VERSION']
        url = f"{opa_domain}/{opa_version}/data/{APP_IDENTIFIER}/{settings.APP_ENV}/allow"

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

    @staticmethod
    def _get_request_header(request: WSGIRequest, header: str) -> str:
        return request.headers.get(header) or request.META.get(header)

    @classmethod
    def _get_resource_path(cls, request: WSGIRequest) -> str:
        # Get the path as a list (removing leading and trailing /)
        request_path_as_list = request.path.strip('/').split('/')
        # Remove id values from path and add <id> as placeholder instead
        request_path_as_list = [p if not p.isdigit() else '<id>' for p in request_path_as_list]
        return '/'.join(request_path_as_list)

    def has_permission(self, request, view):

        logger.info(f"OPA: Checking permission for {view}!")
        response = self._get_opa_response(request)
        if not response.ok:
            logger.info(f"OPA: Cannot Authorize at the moment!")
            return False
        try:
            response_body = response.json()
        except JSONDecodeError:
            logger.info(f"OPA: Decode Error, cannot Authorize at the moment!")
            return False

        try:
            allow = response_body['result']
            if not allow:
                logger.info(f"OPA: Forbidden Resource!")
                return False
            logger.info(f"OPA: Resource is granted!")
            return True
        except KeyError:
            # If the key result is not present in the response,
            # it means the policy for this app does not exist in OPA
            # Update OPA with the necessary policy and data in this case
            logger.info("Opa: Policy/Data is missing, instructing IDP to recreate the rules")
            OpaService.update_opa(authorization_header=request.headers.get('Authorization'))
            # Reattempt authorize
            logger.info("OPA: Re-attempting Permissions")
            return self.has_permission(request, view)
