import logging
from collections import defaultdict
from copy import deepcopy
from datetime import datetime
from typing import Any, Optional, Type, Union

from asgiref.sync import async_to_sync, sync_to_async
from django.conf import settings
from django.core.cache import cache
from django.db import models, transaction
from django.db.models import Q, QuerySet
from rest_framework.exceptions import PermissionDenied
from rest_framework.request import Request

from idp_user.models import User
from idp_user.models.user_role import UserRole
from idp_user.producer import AioKafkaProducer
from idp_user.settings import (
    APP_ENTITIES,
    APP_ENTITY_RECORD_EVENT_TOPIC,
    APP_IDENTIFIER,
    IN_DEV,
    ROLES,
    TENANTS,
)
from idp_user.signals import (
    post_create_idp_user,
    post_update_idp_user,
    pre_update_idp_user,
)
from idp_user.typing import (
    ALL,
    AppEntityRecordEventDict,
    AppEntityTypeConfig,
    UserRecordDict,
    UserTenantData,
)
from idp_user.utils.exceptions import UnsupportedAppEntityType
from idp_user.utils.functions import (
    cache_user_service_results,
    get_or_none,
    keep_keys,
    parse_query_params_from_scope,
    update_record,
)

logger = logging.getLogger(__name__)


class UserService:
    # Service Methods Used by Django Application
    @staticmethod
    async def get_role(request: Request):
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
            return await UserService.get_allowed_app_entity_records(
                user=user,
                role=role,
                app_entity_type=app_entity_type,
                permission=permission,
            )
        await UserService.authorize_app_entity_records(
            user=user,
            role=role,
            app_entity_type=app_entity_type,
            app_entity_records_identifiers=app_entity_records_identifiers,
            permission=permission,
        )
        return await UserService._get_records(
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
            await UserService._get_allowed_app_entity_records_identifiers(
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
            await UserService._get_allowed_app_entity_records_identifiers(
                user=user,
                role=role,
                app_entity_type=app_entity_type,
                permission=permission,
            )
        )
        return await UserService._get_records(
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
        app_entity_type_configs = await UserService._get_app_entity_type_configs(
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
            UserService._invalidate_user_cache_entries(user=user)
        else:
            user = await User.objects.acreate(**user_data)
            post_create_idp_user.send(sender=UserService, user=user)
        return user

    @staticmethod
    def _invalidate_user_cache_entries(user: User):
        """
        Invalidate all the entries in the cache for the given user.
        To do this, find all the entries that start with the app identifier and username of the user.
        """
        if settings.IDP_USER_APP.get("USE_REDIS_CACHE", False) and not IN_DEV:
            cache.delete_pattern(f"{APP_IDENTIFIER}-{user.username}*")

    @classmethod
    def process_user(cls, data: UserRecordDict):
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
        tenants = reported_user_app_configs.keys()

        for tenant in tenants:
            if tenant not in TENANTS:
                logger.info(f"Tenant {tenant} not present, skipping.")
                continue

            logger.info(f"Updating user {data['username']} for tenant {tenant}")
            pre_update_idp_user.send(sender=cls.__class__, tenant=tenant)

            # Extract specific tenant information
            user_record_for_tenant = deepcopy(data)
            user_record_for_tenant["app_specific_configs"] = reported_user_app_configs[
                tenant
            ]

            try:
                with transaction.atomic(using=tenant):
                    async_update_user = async_to_sync(cls._update_user)
                    async_update_user(user_record_for_tenant)
            finally:
                post_update_idp_user.send(sender=cls.__class__, tenant=tenant)

    @classmethod
    def verify_if_user_exists_and_delete_roles(cls, data: UserRecordDict):
        """
        Verify if the user exists in any of the tenants and delete all the roles associated with it.
        """
        for tenant in TENANTS:
            pre_update_idp_user.send(sender=cls.__class__, tenant=tenant)

            if user := get_or_none(User.objects, username=data["username"]):
                logger.info(
                    f"Deleting roles for user {data['username']} in tenant {tenant}"
                )
                UserRole.objects.filter(user=user).delete()  # type: ignore

            post_update_idp_user.send(sender=cls.__class__, tenant=tenant)

    @staticmethod
    async def _update_user(data: UserTenantData):
        """
        This method makes sure that the changes that are coming from the IDP
        for a user are propagated in the internal product Authorization Schemas

        Step 1: Create or update User Object
        Step 2: Create/Update/Delete User Roles for this user.
        """

        user = await UserService._create_or_update_user(data)

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
    def _get_reported_user_app_configs(data):
        return data.get("app_specific_configs", {}).get(APP_IDENTIFIER, {})

    @staticmethod
    def send_app_entity_record_event_to_kafka(
        app_entity_type: str, app_entity_record: Any, deleted=False
    ):
        app_entity_type_config = APP_ENTITIES[app_entity_type]

        event: AppEntityRecordEventDict = {
            "app_identifier": APP_IDENTIFIER,
            "app_entity_type": app_entity_type,
            "record_identifier": getattr(
                app_entity_record, app_entity_type_config["identifier_attr"]
            ),
            "label": getattr(app_entity_record, app_entity_type_config["label_attr"]),
            "deleted": deleted,
        }

        producer = AioKafkaProducer()
        async_send_message = producer.send_message

        sync_send_message = async_to_sync(async_send_message)

        key = str(datetime.now())

        try:
            sync_send_message(topic=APP_ENTITY_RECORD_EVENT_TOPIC, key=key, data=event)
        except Exception as e:
            logger.error(f"Error while sending message to Kafka: {e}. Message: {event}")

    @staticmethod
    def _get_app_entity_type_from_model(model: Type[models.Model]):
        for (
            app_entity_type,
            config,
        ) in APP_ENTITIES.items():  # type: str, AppEntityTypeConfig
            if config["model"] == model:
                return app_entity_type

        raise UnsupportedAppEntityType(model)

    @staticmethod
    def process_app_entity_record_post_save(
        sender: Type[models.Model], instance, **kwargs
    ):
        """
        Whenever an app entity record is saved (created/updated),
        send a message to Kafka to notify the IDP.

        kwargs are required for signal receivers.
        """

        UserService.send_app_entity_record_event_to_kafka(
            app_entity_type=UserService._get_app_entity_type_from_model(sender),
            app_entity_record=instance,
        )

    @staticmethod
    def process_app_entity_record_post_delete(
        sender: Type[models.Model], instance, **kwargs
    ):
        """
        Whenever an app entity record is deleted,
        send a message to Kafka to notify the IDP.

        kwargs are required for signal receivers.
        """

        UserService.send_app_entity_record_event_to_kafka(
            app_entity_type=UserService._get_app_entity_type_from_model(sender),
            app_entity_record=instance,
            deleted=True,
        )

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
