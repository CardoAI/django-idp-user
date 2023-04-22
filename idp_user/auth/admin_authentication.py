from typing import Optional

import requests
from django.conf import settings
from django.contrib.auth.backends import ModelBackend

from idp_user.models.user import User
from idp_user.utils.functions import get_or_none

IDP_URL = settings.IDP_USER_APP.get("IDP_URL")
HTTP_200_OK = 200


class IDPAuthBackend(ModelBackend):
    def authenticate(self, request, **kwargs):
        access_token = self._fetch_token(request)
        if not access_token:
            return None

        response = requests.get(
            url=f"{IDP_URL}/api/users/me/",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        username = response.json()["username"]
        return get_or_none(User.objects, username=username)

    @staticmethod
    def _fetch_token(request) -> Optional[str]:
        response = requests.post(
            url=f"{IDP_URL}/api/login/",
            json={
                "username": request.POST.get("username"),
                "password": request.POST.get("password"),
            },
        )

        if response.status_code == HTTP_200_OK:
            return response.json()["access"]
