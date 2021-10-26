from drf_spectacular.extensions import OpenApiAuthenticationExtension
from drf_spectacular.openapi import AutoSchema
from drf_spectacular.utils import OpenApiParameter

from idp_user.auth.authentication import AuthenticationBackend


class BearerTokenScheme(OpenApiAuthenticationExtension):
    target_class = AuthenticationBackend  # full import path OR class ref
    name = 'IDPAuthentication'  # name used in the schema

    def get_security_definition(self, auto_schema):
        return {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }


class AutoSchemaWithRole(AutoSchema):
    def get_override_parameters(self):
        return [
            OpenApiParameter("role", type=str, location=OpenApiParameter.QUERY, required=True),
        ]
