import logging
from collections import defaultdict
from copy import deepcopy

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from rest_framework.exceptions import PermissionDenied
from rest_framework.request import Request

from ..models import User
from ..models.user_role import ROLES, UserRole
from ..signals import pre_update_idp_user, post_update_idp_user
from ..typing import UserUpdateEvent, UserRecordDict
from ..utils.functions import get_or_none, keep_keys, update_record, cache_user_service_results

logger = logging.getLogger(__name__)

APP_IDENTIFIER = settings.IDP_USER_APP['APP_IDENTIFIER']
IN_DEV = settings.APP_ENV == "development"


class UserService:

    # Service Methods Used by Django Application
    @staticmethod
    def get_role(request: Request):
        return request.query_params.get('role')

    @staticmethod
    def authorize_resources_or_get_all_authorized_resources(
            user: User,
            role: ROLES,
            resource: str,
            resource_ids: list[int],
            permission: str = None
    ):
        if resource_ids:
            UserService.authorize_resources(
                user=user,
                role=role,
                resource=resource,
                resource_ids=resource_ids,
                permission=permission
            )
            return resource_ids
        else:
            return UserService.get_authorized_resources(
                user=user,
                role=role,
                resource=resource,
                permission=permission
            )

    @staticmethod
    def authorize_resources(user: User, role: ROLES, resource: str, resource_ids: list[int], permission: str = None):
        """
        It specifies if the user is authorized to access the objects/permissions that he is requesting
        Permissions that do have restrictable=True, are allowed from OPA, so we need to solve this on product level
        Args:
            user:           The user trying to access the resources
            resource:       Resource name, could be originator_instance_ids; vehicle_ids; portfolio_ids,
                                depending on how it was set up in IDP.
            resource_ids:   The ids of the resources within the configuration
            permission:     In case of specific permissions such as DodManager we can have
                            permission restrictions through IDP. The value is the name of the permission
            role:           ROLES as defined in the settings file.

        Returns: None; In case the requested objects are not accessible  it will raise errors instead.
        """

        user_role = UserRole.objects.get(user=user, role=role)

        if permission:
            permission_restrictions = user_role.permission_restrictions
            if permission_restrictions and permission in permission_restrictions.keys():
                permission_restriction = permission_restrictions.get(permission)
                restriction_value = permission_restriction.get(resource)
                if restriction_value is False:
                    raise PermissionDenied('You are not allowed to access the resources in the Requested Objects!')
                else:
                    if not set(resource_ids).issubset(set(restriction_value)):
                        raise PermissionDenied('You are not allowed to access the resources in the Requested Objects!')
                    else:
                        return

        # Check App config
        if not set(resource_ids).issubset(set(user_role.app_config.get(resource, {}))):
            raise PermissionDenied(f'You are not allowed to access the resources in the Requested Objects!')

    @staticmethod
    @cache_user_service_results
    def get_authorized_resources(user: User, role, resource: str, permission: str = None) -> list[int]:
        """
        It gets the authorized resources for the group that has been requested.
        Args:
            user:           Logged in User
            role:           ROLES as defined in the settings file.
            resource:       The resource being accessed. For example, vehicle_ids
            permission:     In case of specific permissions such as DodManager we can have
                            permission restrictions through IDP. The value is the name of the permission

        Returns:
            Resource Ids
        """
        assert ROLES.as_dict().get(role) is not None, f"Role does not exist: {role}"

        try:
            user_role = UserRole.objects.get(user=user, role=role)

            if permission:
                permission_restrictions = user_role.permission_restrictions
                if permission_restrictions and permission in permission_restrictions.keys():
                    permission_restriction = permission_restrictions.get(permission)
                    return permission_restriction.get(resource) or []

            return user_role.app_config.get(resource, [])
        except UserRole.DoesNotExist:
            return []

    @staticmethod
    def _create_or_update_user(data: UserUpdateEvent) -> User:
        user = get_or_none(User.objects, idp_user_id=data.get("idp_user_id"))
        user_data = keep_keys(data, [
            "idp_user_id",
            "username",
            "email",
            "first_name",
            "last_name",
        ])
        if user:
            update_record(user, **user_data)
            UserService._invalidate_user_cache_entries(user=user)
            return user
        else:
            return User.objects.create(**user_data)

    @staticmethod
    def _invalidate_user_cache_entries(user: User):
        """
        Invalidate all the entries in the cache for the given user.
        To do this, find all the entries that start with the app identifier and username of the user.
        """
        if settings.IDP_USER_APP.get('USE_REDIS_CACHE', False) and not IN_DEV:
            cache.delete_pattern(f"{APP_IDENTIFIER}-{user.username}*")

    @classmethod
    def update_user(cls, data: UserRecordDict):
        """
        Extract tenants from the user record and call _update_user for each tenant.
        Remove tenant information from the payload of _update_user since it is not needed
        inside of it.

        Send signals before and after calling the _update_user method for each tenant
        separately. This gives possibility to the project to react on the user update.

        One case of handling this signal is to switch database connection to the tenant's
        database. In this way the user can be updated in the correct database.

        """
        reported_user_app_configs = UserService._get_reported_user_app_configs(data)
        app_configs = reported_user_app_configs[APP_IDENTIFIER]
        tenants = app_configs.keys()

        for tenant in tenants:
            logger.info(f"Updating user {data['username']} for tenant {tenant}")
            pre_update_idp_user.send(sender=cls.__class__, tenant=tenant)
            user_record_for_tenant = deepcopy(data)
            user_record_for_tenant['app_specific_configs'] = app_configs[tenant]
            UserService._update_user(user_record_for_tenant)
            post_update_idp_user.send(sender=cls.__class__, tenant=tenant)

    @staticmethod
    @transaction.atomic
    def _update_user(data: UserUpdateEvent):
        """
        This method makes sure that the changes that are coming from the IDP
        for a user are propagated in the internal product Authorization Schemas

        Step 1: Create or update User Object
        Step 2: Create/Update/Delete User Roles for this user.
        """

        user = UserService._create_or_update_user(data)

        current_user_roles = defaultdict()
        for user_role in user.user_roles.all():
            current_user_roles[user_role.role] = user_role

        reported_user_app_configs = UserService._get_reported_user_app_configs(data)

        for role, role_data in reported_user_app_configs.items():
            if existing_user_role := current_user_roles.get(role):
                update_record(
                    existing_user_role,
                    permission_restrictions=role_data.get('permission_restrictions'),
                    app_config=role_data.get("app_config")
                )
            else:
                UserRole.objects.create(
                    user=user,
                    role=role,
                    permission_restrictions=role_data.get('permission_restrictions'),
                    app_config=role_data.get("app_config")
                )

        # Verify if any of the previous user roles is not being reported anymore
        # Delete it if this is the case
        for role, user_role in current_user_roles.items():  # type: str, UserRole
            if reported_user_app_configs.get(role) is None:
                user_role.delete()

    @staticmethod
    def _get_reported_user_app_configs(data):
        return data.get('app_specific_configs', {}).get(APP_IDENTIFIER, {})
