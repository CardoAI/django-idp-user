from rest_framework.views import exception_handler
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response, Response as DRFResponse
from rest_framework.status import HTTP_400_BAD_REQUEST, HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN, HTTP_502_BAD_GATEWAY


def bad_request(message="Bad request."):
    return Response({"message": message}, HTTP_400_BAD_REQUEST)


def unauthorized(message="Unauthorized."):
    return Response({"message": message}, HTTP_401_UNAUTHORIZED)


def forbidden(message="Forbidden."):
    return Response({"message": message}, HTTP_403_FORBIDDEN)


def bad_gateway(message="Bad Gateway."):
    return Response({"message": message}, HTTP_502_BAD_GATEWAY)


class AuthException(Exception):
    def __init__(self, response: DRFResponse):
        self._response = response
        self._response.accepted_renderer = JSONRenderer()
        self._response.accepted_media_type = 'application/json'
        self._response.content_type = 'application/json'
        self._response.renderer_context = {}

    def as_response(self) -> DRFResponse:
        return self._response.render()


def custom_exception_handler(exc, context):
    # Call REST framework's default exception handler first,
    # to get the standard error response.
    response = exception_handler(exc, context)

    # Now add the HTTP status code to the response.
    if isinstance(exc, AuthException):
        return exc.as_response()

    return response
