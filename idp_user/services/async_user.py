import logging
from collections import defaultdict
from typing import Any, Optional, Union

from asgiref.sync import sync_to_async
from django.core.exceptions import PermissionDenied
from django.db import models
from django.db.models import Q, QuerySet
from django.http import HttpRequest

from idp_user.models import User
from idp_user.models.user_role import UserRole
from idp_user.settings import APP_ENTITIES, ROLES
from idp_user.signals import post_create_idp_user
from idp_user.utils.functions import (
    cache_user_service_results,
    get_or_none,
    keep_keys,
    parse_query_params_from_scope,
    update_record,
)
from idp_user.utils.typing import ALL, AppEntityTypeConfig, UserTenantData

logger = logging.getLogger(__name__)


class UserServiceAsync:
    # Service Methods Used by Django Application
    @staticmethod
    def get_role(request: HttpRequest):
        return request.query_params.get("role")

    @staticmethod
    async def get_role_from_scope(scope):
        query_params = parse_query_params_from_scope(scope)
        return query_params.get("role")[0] if query_params.get("role") else None

    @staticmethod
    async def authorize_and_get_records_or_get_all_allowed(
        user: User,
        role: ROLES,
        app_entity_type: str,
        app_entity_records_identifiers: Optional[list[Any]],
        permission: str = None,
    ) -> models.QuerySet:
        """
        Make sure that the user can access the entity records being requested and return them.
        If no identifiers are being provided, return all allowed entity records.

        Args:
            user:                           The user performing the request
            role:                           The role that the user is acting as.
            app_entity_type:                The app entity being accessed
            app_entity_records_identifiers: The identifiers of the records belonging to the specified app entity
            permission:                     In case of specific permissions we can have permission restrictions
                                                through IDP. The value is the name of the permission


        Raises:
            PermissionDenied: In case the requested records are not allowed
        """

        if not app_entity_records_identifiers:
            return await UserServiceAsync.get_allowed_app_entity_records(
                user=user,
                role=role,
                app_entity_type=app_entity_type,
                permission=permission,
            )
        await UserServiceAsync.authorize_app_entity_records(
            user=user,
            role=role,
            app_entity_type=app_entity_type,
            app_entity_records_identifiers=app_entity_records_identifiers,
            permission=permission,
        )
        return await UserServiceAsync._get_records(
            app_entity_type=app_entity_type,
            records_identifiers=app_entity_records_identifiers,
        )

    @staticmethod
    async def authorize_app_entity_records(
        user: User,
        role: ROLES,
        app_entity_type: str,
        app_entity_records_identifiers: list[Any],
        permission: str = None,
    ):
        """
        Verify if the user has access to the requested entity records.
        If a permission is specified and it has restrictable=True, the access is verified based on it.

        Args:
            user:                           The user performing the request
            role:                           The role that the user is acting as.
            app_entity_type:                The app entity being accessed
            app_entity_records_identifiers: The identifiers of the records belonging to the specified app entity
            permission:                     In case of specific permissions we can have permission restrictions
                                                through IDP. The value is the name of the permission

        Raises:
            PermissionDenied: In case the requested records are not allowed
        """

        assert (
            app_entity_type in APP_ENTITIES.keys()
        ), f"Unknown app entity: {app_entity_type}!"
        allowed_app_entity_records_identifiers = (
            await UserServiceAsync._get_allowed_app_entity_records_identifiers(
                user=user,
                role=role,
                app_entity_type=app_entity_type,
                permission=permission,
            )
        )
        if allowed_app_entity_records_identifiers == ALL:
            return

        if not set(app_entity_records_identifiers).issubset(
            set(allowed_app_entity_records_identifiers)
        ):
            raise PermissionDenied(
                "You are not allowed to access the records in the requested entity!"
            )

    @staticmethod
    async def get_allowed_app_entity_records(
        user: User, role: ROLES, app_entity_type: str, permission: str = None
    ) -> models.QuerySet:
        """
        Gets the app entity records that the user can access.

        Args:
            user:               The user performing the request
            role:               The role that the user is acting as.
            app_entity_type:    The app entity being accessed
            permission:         In case of specific permissions we can have permission restrictions
                                    through IDP. The value is the name of the permission

        Returns:
            QuerySet of App Entity Records that the user can access
        """

        assert (
            app_entity_type in APP_ENTITIES.keys()
        ), f"Unknown app entity: {app_entity_type}!"

        allowed_app_entity_records_identifiers = (
            await UserServiceAsync._get_allowed_app_entity_records_identifiers(
                user=user,
                role=role,
                app_entity_type=app_entity_type,
                permission=permission,
            )
        )
        return await UserServiceAsync._get_records(
            app_entity_type=app_entity_type,
            records_identifiers=allowed_app_entity_records_identifiers,
        )

    @staticmethod
    async def _get_app_entity_type_configs(app_entity_type: str) -> AppEntityTypeConfig:
        try:
            return APP_ENTITIES[app_entity_type]
        except KeyError as e:
            raise KeyError(
                f"No config declared for app_entity_type={app_entity_type} "
                f"in IDP_USER_APP['APP_ENTITIES']!"
            ) from e

    @staticmethod
    async def _get_records(
        app_entity_type: str, records_identifiers: Union[list[Any], ALL]
    ) -> models.QuerySet:
        app_entity_type_configs = await UserServiceAsync._get_app_entity_type_configs(
            app_entity_type
        )
        model = app_entity_type_configs["model"]

        if records_identifiers == ALL:
            return await sync_to_async(list)(model.objects.all())
        model_identifier_attr = app_entity_type_configs["identifier_attr"]
        return await sync_to_async(model.objects.filter)(
            **{f"{model_identifier_attr}__in": records_identifiers}
        )

    @staticmethod
    @cache_user_service_results
    async def _get_allowed_app_entity_records_identifiers(
        user: User, role: ROLES, app_entity_type: str, permission: str = None
    ) -> Union[list[Any], ALL]:
        """
        Gets the identifiers of the app entity records that the user can access.
        If no restriction both on role and permission level, return '__all__'

        Args:
            user:               The user performing the request
            role:               The role that the user is acting as.
            app_entity_type:    The app entity being accessed
            permission:         In case of specific permissions we can have permission restrictions
                                    through IDP. The value is the name of the permission

        Returns:
            List of identifiers of App Entity Records that the user can access
        """
        assert ROLES.as_dict().get(role) is not None, f"Role does not exist: {role}"

        try:
            user_role = await UserRole.objects.aget(user=user, role=role)
        except UserRole.DoesNotExist:
            return []

        # Permission restriction get precedence, if existing, for the given app_entity
        if permission:
            permission_restrictions = user_role.permission_restrictions
            if permission_restrictions and permission in permission_restrictions.keys():
                permission_restriction = permission_restrictions.get(permission)
                if permission_app_entity_restriction := permission_restriction.get(
                    app_entity_type
                ):
                    return permission_app_entity_restriction

        # Verify if there is any restriction on the entity for the user
        app_entities_restrictions = user_role.app_entities_restrictions
        if app_entities_restrictions and (
            app_entity_restriction := app_entities_restrictions.get(app_entity_type)
        ):
            return app_entity_restriction

        return ALL

    @staticmethod
    async def _create_or_update_user(data: UserTenantData) -> User:
        user = await sync_to_async(get_or_none)(
            User.objects, username=data.get("username")
        )
        user_data = keep_keys(
            data,
            [
                "username",
                "email",
                "first_name",
                "last_name",
                "is_active",
                "is_staff",
                "is_superuser",
                "date_joined",
            ],
        )
        if user:
            await sync_to_async(update_record)(user, **user_data)
        else:
            user = await User.objects.acreate(**user_data)
            post_create_idp_user.send(sender=UserServiceAsync, user=user)
        return user

    @staticmethod
    async def _update_user(data: UserTenantData):
        """
        This method makes sure that the changes that are coming from the IDP
        for a user are propagated in the internal product Authorization Schemas

        Step 1: Create or update User Object
        Step 2: Create/Update/Delete User Roles for this user.
        """

        user = await UserServiceAsync._create_or_update_user(data)

        current_user_roles = defaultdict()
        async for user_role in user.user_roles.all():
            current_user_roles[user_role.role] = user_role

        roles_data = data.get("app_specific_configs")

        for role, role_data in roles_data.items():
            if existing_user_role := current_user_roles.get(role):
                await sync_to_async(update_record)(
                    existing_user_role,
                    permission_restrictions=role_data.get("permission_restrictions"),
                    app_entities_restrictions=role_data.get(
                        "app_entities_restrictions"
                    ),
                )
            else:
                await UserRole.objects.acreate(
                    user=user,
                    role=role,
                    permission_restrictions=role_data.get("permission_restrictions"),
                    app_entities_restrictions=role_data.get(
                        "app_entities_restrictions"
                    ),
                )

        # Verify if any of the previous user roles is not being reported anymore
        # Delete it if this is the case
        for role, user_role in current_user_roles.items():  # type: str, UserRole
            if roles_data.get(role) is None:
                user_role.delete()

    @staticmethod
    async def get_users_with_access_to_app_entity_record(
        app_entity_type: str, record_identifier: Any, roles: list[str]
    ) -> QuerySet:
        """
        Get users that have access to the required app entity record in the given roles.
        """

        assert (
            app_entity_type in APP_ENTITIES.keys()
        ), f"Unknown app entity: {app_entity_type}!"

        roles = await sync_to_async(UserRole.objects.filter)(
            Q(user__is_active=True)
            & Q(role__in=roles)
            & (
                Q(app_entities_restrictions__isnull=True)
                | Q(**{f"app_entities_restrictions__{app_entity_type}__isnull": True})
                | Q(
                    **{
                        f"app_entities_restrictions__{app_entity_type}__contains": record_identifier
                    }
                )
            )
        )
        return await sync_to_async(User.objects.filter)(
            pk__in=list(roles.values_list("user__pk", flat=True))
        )

    @staticmethod
    async def get_user(username: str) -> User:
        """
        Get user by username
        """
        return await sync_to_async(get_or_none)(User.objects, username=username)
