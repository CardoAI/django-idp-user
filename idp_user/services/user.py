import logging
from collections import defaultdict
from copy import deepcopy
from datetime import datetime
from typing import Any, Optional, Union, Type

from django.conf import settings
from django.core.cache import cache
from django.db import transaction, models
from rest_framework.exceptions import PermissionDenied
from rest_framework.request import Request

from ..models import User
from ..models.user_role import UserRole
from ..producer import Producer
from ..settings import ROLES, APP_ENTITIES, IN_DEV, APP_IDENTIFIER, APP_ENTITY_RECORD_EVENT_TOPIC
from ..signals import pre_update_idp_user, post_update_idp_user, post_create_idp_user
from ..typing import UserTenantData, UserRecordDict, ALL, AppEntityTypeConfig, AppEntityRecordEventDict
from ..utils.functions import get_or_none, keep_keys, update_record, cache_user_service_results

logger = logging.getLogger(__name__)


class UserService:

    # Service Methods Used by Django Application
    @staticmethod
    def get_role(request: Request):
        return request.query_params.get('role')

    @staticmethod
    def authorize_and_get_records_or_get_all_allowed(
            user: User,
            role: ROLES,
            app_entity_type: str,
            app_entity_records_identifiers: Optional[list[Any]],
            permission: str = None
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

        if app_entity_records_identifiers:
            UserService.authorize_app_entity_records(
                user=user,
                role=role,
                app_entity_type=app_entity_type,
                app_entity_records_identifiers=app_entity_records_identifiers,
                permission=permission
            )
            return UserService._get_records(
                app_entity_type=app_entity_type,
                records_identifiers=app_entity_records_identifiers
            )
        else:
            return UserService.get_allowed_app_entity_records(
                user=user,
                role=role,
                app_entity_type=app_entity_type,
                permission=permission
            )

    @staticmethod
    def authorize_app_entity_records(
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

        assert app_entity_type in APP_ENTITIES.keys(), f"Unknown app entity: {app_entity_type}!"

        allowed_app_entity_records_identifiers = UserService._get_allowed_app_entity_records_identifiers(
            user=user,
            role=role,
            app_entity_type=app_entity_type,
            permission=permission
        )

        if allowed_app_entity_records_identifiers == ALL:
            return

        if not set(app_entity_records_identifiers).issubset(set(allowed_app_entity_records_identifiers)):
            raise PermissionDenied('You are not allowed to access the records in the requested entity!')

    @staticmethod
    def get_allowed_app_entity_records(
            user: User,
            role: ROLES,
            app_entity_type: str,
            permission: str = None
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

        assert app_entity_type in APP_ENTITIES.keys(), f"Unknown app entity: {app_entity_type}!"

        allowed_app_entity_records_identifiers = UserService._get_allowed_app_entity_records_identifiers(
            user=user,
            role=role,
            app_entity_type=app_entity_type,
            permission=permission
        )

        return UserService._get_records(
            app_entity_type=app_entity_type,
            records_identifiers=allowed_app_entity_records_identifiers
        )

    @staticmethod
    def _get_app_entity_type_configs(app_entity_type: str) -> AppEntityTypeConfig:
        try:
            return APP_ENTITIES[app_entity_type]
        except KeyError:
            raise KeyError(
                f"No config declared for app_entity_type={app_entity_type} "
                f"in IDP_USER_APP['APP_ENTITIES']!"
            )

    @staticmethod
    def _get_records(
            app_entity_type: str,
            records_identifiers: Union[list[Any], ALL]
    ) -> models.QuerySet:
        app_entity_type_configs = UserService._get_app_entity_type_configs(app_entity_type)
        model = app_entity_type_configs['model']

        if records_identifiers == ALL:
            return model.objects.all()
        else:
            model_identifier_attr = app_entity_type_configs['identifier_attr']
            return model.objects.filter(**{f"{model_identifier_attr}__in": records_identifiers})

    @staticmethod
    @cache_user_service_results
    def _get_allowed_app_entity_records_identifiers(
            user: User,
            role: ROLES,
            app_entity_type: str,
            permission: str = None
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
            user_role = UserRole.objects.get(user=user, role=role)

            # Permission restriction get precedence, if existing
            if permission:
                permission_restrictions = user_role.permission_restrictions
                if permission_restrictions and permission in permission_restrictions.keys():
                    permission_restriction = permission_restrictions.get(permission)
                    return permission_restriction.get(app_entity_type) or []

            # Verify if there is any restriction on the entity for the user
            app_entities_restrictions = user_role.app_entities_restrictions
            if app_entities_restrictions and (
                    app_entity_restriction := app_entities_restrictions.get(app_entity_type)
            ):
                return app_entity_restriction

            return ALL

        except UserRole.DoesNotExist:
            return []

    @staticmethod
    def _create_or_update_user(data: UserTenantData) -> User:
        user = get_or_none(User.objects, idp_user_id=data.get("idp_user_id"))
        user_data = keep_keys(data, [
            "idp_user_id",
            "username",
            "email",
            "first_name",
            "last_name",
            "is_active",
            "is_staff",
            "is_superuser",
            "date_joined",
        ])
        if user:
            update_record(user, **user_data)
            UserService._invalidate_user_cache_entries(user=user)
            return user
        else:
            user = User.objects.create(**user_data)
            post_create_idp_user.send(sender=UserService, user=user)

            return user

    @staticmethod
    def _invalidate_user_cache_entries(user: User):
        """
        Invalidate all the entries in the cache for the given user.
        To do this, find all the entries that start with the app identifier and username of the user.
        """
        if settings.IDP_USER_APP.get('USE_REDIS_CACHE', False) and not IN_DEV:
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
            if tenant not in settings.DATABASES.keys():
                logger.info(f"Tenant {tenant} not present, skipping.")
                continue

            logger.info(f"Updating user {data['username']} for tenant {tenant}")
            pre_update_idp_user.send(sender=cls.__class__, tenant=tenant)

            # Extract specific tenant information
            user_record_for_tenant = deepcopy(data)
            user_record_for_tenant['app_specific_configs'] = reported_user_app_configs[tenant]

            try:
                with transaction.atomic(using=tenant):
                    UserService._update_user(user_record_for_tenant)  # type: ignore
            finally:
                post_update_idp_user.send(sender=cls.__class__, tenant=tenant)

    @staticmethod
    def _update_user(data: UserTenantData):
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

        roles_data = data.get('app_specific_configs')

        for role, role_data in roles_data.items():
            if existing_user_role := current_user_roles.get(role):
                update_record(
                    existing_user_role,
                    permission_restrictions=role_data.get('permission_restrictions'),
                    app_entities_restrictions=role_data.get("app_entities_restrictions")
                )
            else:
                UserRole.objects.create(
                    user=user,
                    role=role,
                    permission_restrictions=role_data.get('permission_restrictions'),
                    app_entities_restrictions=role_data.get("app_entities_restrictions")
                )

        # Verify if any of the previous user roles is not being reported anymore
        # Delete it if this is the case
        for role, user_role in current_user_roles.items():  # type: str, UserRole
            if roles_data.get(role) is None:
                user_role.delete()

    @staticmethod
    def _get_reported_user_app_configs(data):
        return data.get('app_specific_configs', {}).get(APP_IDENTIFIER, {})

    @staticmethod
    def send_app_entity_record_event_to_kafka(app_entity_type: str, app_entity_record: Any, deleted=False):
        app_entity_type_config = APP_ENTITIES[app_entity_type]

        event: AppEntityRecordEventDict = {
            'app_identifier': APP_IDENTIFIER,
            'app_entity_type': app_entity_type,
            'record_identifier': getattr(app_entity_record, app_entity_type_config['identifier_attr']),
            'label': getattr(app_entity_record, app_entity_type_config['label_attr']),
            'deleted': deleted
        }

        logger.info(f"Sending update {event}...")

        Producer().send_message(
            topic=APP_ENTITY_RECORD_EVENT_TOPIC,
            key=str(datetime.now()),
            data=event
        )

    @staticmethod
    def _get_app_entity_type_from_model(model: Type[models.Model]):
        for app_entity_type, config in APP_ENTITIES.items():  # type: str, AppEntityTypeConfig
            if config['model'] == model:
                return app_entity_type

        raise Exception(f"App entity type for model {model} not found!")

    @staticmethod
    def process_app_entity_record_post_save(sender: Type[models.Model], instance, **kwargs):
        """
        Whenever an app entity record is saved (created/updated),
        send a message to Kafka to notify the IDP.

        kwargs are required for signal receivers.
        """

        UserService.send_app_entity_record_event_to_kafka(
            app_entity_type=UserService._get_app_entity_type_from_model(sender),
            app_entity_record=instance
        )

    @staticmethod
    def process_app_entity_record_post_delete(sender: Type[models.Model], instance, **kwargs):
        """
        Whenever an app entity record is deleted,
        send a message to Kafka to notify the IDP.

        kwargs are required for signal receivers.
        """

        UserService.send_app_entity_record_event_to_kafka(
            app_entity_type=UserService._get_app_entity_type_from_model(sender),
            app_entity_record=instance,
            deleted=True
        )
