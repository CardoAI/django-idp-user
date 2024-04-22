import base64
import json
import os
from typing import Optional
from urllib.parse import parse_qs

import boto3
import jwt
import requests
from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpRequest
from requests import HTTPError

APP_IDENTIFIER = settings.IDP_USER_APP.get("APP_IDENTIFIER")
IDP_URL = settings.IDP_USER_APP.get("IDP_URL")


def keep_keys(dictionary, keys):
    return {k: v for k, v in dictionary.items() if k in keys}


def get_or_none(records, *args, **kwargs):
    try:
        return records.get(*args, **kwargs)
    except ObjectDoesNotExist:
        return None


def update_record(record, save=True, **data):
    if data:
        for key, value in data.items():
            setattr(record, key, value)
        if save:
            record.save()
    return record


def cache_user_service_results(function):
    from idp_user.settings import APP_IDENTIFIER, IN_DEV

    def wrapper(user, *args, **kwargs):
        cache_key = f"{APP_IDENTIFIER}-{user.username}-{function.__name__}"
        for arg in args:
            cache_key += f",{arg}"
        for key, value in kwargs.items():
            cache_key += f",{key}={value}"

        result = cache.get(cache_key)
        if result:
            return json.loads(result)
        result = function(user=user, *args, **kwargs)  # noqa
        cache.set(cache_key, json.dumps(result))
        return result

    if IN_DEV or not settings.IDP_USER_APP.get('USE_REDIS_CACHE', False):
        return function

    return wrapper


def get_kafka_bootstrap_servers(include_uri_scheme=True):
    """
    If ARN is available, it means we can connect to the production servers.
    We have to find the bootstrap servers and create the connection using them.
    """
    if kafka_arn := settings.KAFKA_ARN:
        resource = boto3.client("kafka", region_name=os.getenv("AWS_REGION", "eu-central-1"))
        response = resource.get_bootstrap_brokers(
            ClusterArn=base64.b64decode(kafka_arn).decode("utf-8")
        )
        assert (
                "BootstrapBrokerStringTls" in response.keys()
        ), "Something went wrong while receiving kafka servers!"

        bootstrap_servers = response.get("BootstrapBrokerStringTls").split(",")
        if not include_uri_scheme:
            return bootstrap_servers
        return [f"kafka://{host}" for host in bootstrap_servers]
    else:
        kafka_url = settings.KAFKA_BROKER
        return f"kafka://{kafka_url}" if include_uri_scheme else kafka_url


def parse_query_params_from_scope(scope):
    """
    Parse query params from scope

    Parameters:
        scope (dict): scope from consumer

    Returns:
        dict: query params
    """
    return parse_qs(scope["query_string"].decode("utf-8"))


def get_jwt_payload(token: str) -> dict:
    """
    Get payload from JWT token.

    Args:
        token (str): JWT token

    Returns:
        dict: payload

    Raises:
        jwt.exceptions.InvalidTokenError: If token is invalid
    """
    return jwt.decode(
        token,
        algorithms=["HS256"],
        options={"verify_signature": False},  # Signature is verified from IDP
    )


def authorize_request_with_idp(request: HttpRequest, token: str) -> Optional[str]:
    """
    Validate token with IDP.

    Args:
        request: The original request
        token: The JWT token provided

    Return:
        The error message if any, otherwise None
    """
    query_params = {"app": APP_IDENTIFIER}
    if tenant := request.headers.get("X-TENANT"):
        query_params["tenant"] = tenant

    try:
        response = requests.get(
            f"{IDP_URL}/api/validate/",
            params=query_params,
            headers={
                "Authorization": f"Bearer {token}",
                "X-Original-Method": request.method,
                "X-Auth-Request-Redirect": request.get_full_path(),
            }
        )
        response.raise_for_status()
    except HTTPError as e:
        try:
            error_message = e.response.json().get("detail")
        except Exception:
            error_message = str(e)

        return error_message
