import aiohttp
from django.conf import settings

from idp_user.services.async_user import UserServiceAsync
from idp_user.utils.functions import parse_query_params_from_scope

IDP_URL = settings.IDP_USER_APP.get("IDP_URL")


class IDPChannelsAuthenticationMiddleware:
    user_service_cls = UserServiceAsync

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope.get("user"):
            return await self.app(scope, receive, send)

        query_params = parse_query_params_from_scope(scope)
        authorization_access_token = query_params.get("authorization", [None])[0]
        if not authorization_access_token:
            return await self.app(scope, receive, send)
        username = await self._get_username(authorization_access_token)
        if not username:
            return await self.app(scope, receive, send)
        user = await self._get_user(username)
        if user:
            scope["user"] = user
            scope["authorization_access_token"] = authorization_access_token

        return await self.app(scope, receive, send)

    async def _get_username(self, access_token):
        headers = {"Authorization": f"Bearer {access_token}"}
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(f"{IDP_URL}/api/users/me/") as resp:
                if resp.status != 200:
                    return None
                response = await resp.json()
                return response.get("username")

    async def _get_user(self, username):
        return await self.user_service_cls.get_user(username=username)
