from collections import defaultdict
from typing import List, TypedDict

from django.conf import settings
from django.db import transaction
from rest_framework.request import Request

from ..models import User
from ..models.user_role import ROLES, UserRole
from ..typing import UserUpdateEvent, UserFeaturesPermissions
from ..utils.exceptions import AuthException, forbidden
from ..utils.functions import get_or_none, keep_keys, update_record


class UserGroupPermissionsData(TypedDict):
    id: int
    feature_permissions: UserFeaturesPermissions


ALLOWED_FEATURES = [
    "dod_manager",
    "notes_manager",
    "cash_flow_simulation"
]

APP_IDENTIFIER = settings.IDP_USER_APP['APP_IDENTIFIER']


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

        user_role_instance = UserRole.objects.get(user=user, role=role)

        if permission:
            if permission_restriction := user_role_instance.get("permission_restrictions", {}).get(permission):
                if permission_restriction:
                    return set(resource_ids).issubset(set(permission_restriction.get(resource)))
                else:
                    raise AuthException(
                        forbidden(f'You are not allowed to access the resources in the Requested Objects! '))

        # Check App config
        if not set(resource_ids).issubset(set(user_role_instance.app_config.get(resource, {}))):
            raise AuthException(forbidden(f'You are not allowed to access the resources in the Requested Objects! '))

    @staticmethod
    def get_authorized_resources(user: User, role, resource: str) -> list[int]:
        """
        It gets the authorized resources for the group that has been requested.
        Args:
            user: Logged in User
            role: ROLES as defined in the settings file.
            resource: The resource being accessed. For example, vehicle_ids

        Returns:
            Resource Ids
        """
        assert ROLES.as_dict().get(role) is not None, f"Role does not exist: {role}"

        try:
            user_role = UserRole.objects.get(user=user, role=role)
            return user_role.app_config.get(resource, [])
        except UserRole.DoesNotExist:
            return []

    # Methods Used by Kafka Consumer to synchronize user/roles and permissions.
    @staticmethod
    def _validate_feature_permissions(feature_permissions: UserFeaturesPermissions):
        if not feature_permissions:
            return

        for key in feature_permissions.keys():
            if key not in ALLOWED_FEATURES:
                raise ValueError(f"Key {key} is invalid as a feature! Acceptable values: {ALLOWED_FEATURES}!")

    @staticmethod
    def _create_or_update_user(data: UserUpdateEvent) -> User:
        user = get_or_none(User.objects, username=data.get("username"))
        user_data = keep_keys(data, [
            "idp_user_id",
            "username",
            "email",
            "first_name",
            "last_name",
        ])
        if user:
            update_record(user, **user_data)
            return user
        else:
            return User.objects.create(**user_data)

    @staticmethod
    @transaction.atomic
    def update_user(data: UserUpdateEvent):
        """
        This method makes sure that the changes that are coming from the IDP
        for a user are propagated in the internal product Authorization Schemas

        Step 1: Create or update User Object
        Step 2: Create/Update/Delete Group Role for this user.
        """

        user = UserService._create_or_update_user(data)

        current_user_roles = defaultdict()
        for user_role in user.user_roles.all():
            current_user_roles[user_role.role] = user_role

        reported_user_app_configs = data.get('app_specific_configs', {}).get(APP_IDENTIFIER, {})

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
