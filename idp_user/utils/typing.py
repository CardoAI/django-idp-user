from typing import Any, List, Optional, Type, TypedDict, Union

from django.db import models

ALL = "all"


class JwtData(TypedDict):
    iat: int
    nbf: int
    jti: str
    exp: str
    type: str
    fresh: str
    user_id: int
    email: str
    username: str


class UserFeaturesPermissions(TypedDict):
    dod_manager: Union[List, bool]
    cash_flow_projection: Union[List, bool]
    notes_manager: Union[List, bool]


class AppSpecificConfigs(TypedDict):
    app_entities_restrictions: Optional[dict[str, list]]
    permission_restrictions: dict[str, Union[bool, Any]]
    organization: Optional[str]


Role = str
UserAppSpecificConfigs = dict[Role, AppSpecificConfigs]


class UserTenantData(TypedDict):
    first_name: str
    last_name: str
    username: str
    email: str
    is_active: bool
    is_staff: bool
    is_superuser: bool
    date_joined: str
    app_specific_configs: UserAppSpecificConfigs


"""
"data": [
   {
        "first_name": "str",
        "last_name": "str",
        "username": "str",
        "email": "str",
        "is_active": "bool",
        "is_staff": "bool",
        "is_superuser": "bool",
        "date_joined": "datetime"
        "app_specific_configs": {
            "app_identifier": {
                "Servicer": {
                    "app_entities_restrictions": {"vehicle": [1, 2]},
                    "permission_restrictions": {
                        "viewDoD": {"vehicle_ids": [1]},
                        "synchronizeDoD": false
                    }
                }
            }
        }
    }
]
"""

# ===
AppIdentifier = str
TenantIdentifier = str

UserRecordAppSpecificConfigs = dict[
    AppIdentifier, dict[TenantIdentifier, AppSpecificConfigs]
]


class UserRecordDict(TypedDict):
    first_name: str
    last_name: str
    username: str
    email: str
    is_active: bool
    is_staff: bool
    is_superuser: bool
    date_joined: str
    app_specific_configs: UserRecordAppSpecificConfigs


"""
Example of a user record from kafka:
{
    "first_name": "str",
    "last_name": "str",
    "username": "str",
    "email": "str",
    "is_active": "bool",
    "is_staff": "bool",
    "is_superuser": "bool",
    "date_joined": "datetime"
    "app_specific_configs": {
        "app_identifier": {
            "tenant": {
                "Servicer": {
                    "app_entities_restrictions": {"vehicle": [1, 2]},
                    "permission_restrictions": {
                        "viewDoD": {"vehicle": [1]},
                        "synchronizeDoD": false
                    }
                }
            }
        }
    }
}
"""


class AppEntityTypeConfig(TypedDict):
    model: Union[str, Type[models.Model]]
    identifier_attr: str
    label_attr: str


class AppEntityRecordEventDict(TypedDict):
    app_identifier: str
    app_entity_type: str
    record_identifier: Any
    deleted: bool
    label: Optional[str]
