from typing import TypedDict, Union, List, Any, Optional


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
    app_config: Any
    permission_restrictions: dict[str, Union[bool, Any]]


Role = str
UserAppSpecificConfigs = dict[Role, AppSpecificConfigs]


class UserUpdateEvent(TypedDict):
    idp_user_id: int
    first_name: str
    last_name: str
    username: str
    email: str
    app_specific_configs: UserAppSpecificConfigs


"""
"data": [
   {
        "idp_user_id": 12,
        "first_name": "str",
        "last_name": "str",
        "username": "str",
        "email": "str",
        "app_specific_configs": {
            "app_identifier": {
                "Servicer": {
                    "app_config": {"vehicle_ids": [1, 2]},
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

UserRecordAppSpecificConfigs = dict[AppIdentifier, dict[TenantIdentifier, AppSpecificConfigs]]


class UserRecordDict(TypedDict):
    idp_user_id: int
    first_name: Optional[str]
    last_name: Optional[str]
    username: Optional[str]
    email: Optional[str]
    app_specific_configs: UserRecordAppSpecificConfigs


"""
Example of a user record from kafka:
{
    "first_name": "str",
    "last_name": "str",
    "username": "str",
    "email": "str",
    "app_specific_configs": {
        "app_identifier": {
            "tenant": {
                "Servicer": {
                    "app_config": {"vehicle_ids": [1, 2]},
                    "permission_restrictions": {
                        "viewDoD": {"vehicle_ids": [1]},
                        "synchronizeDoD": false
                    }
                }
            }
        }
    }
}
"""
