import faust
from asgiref.sync import sync_to_async
from django.conf import settings
from django.utils.module_loading import import_string
from faust import StreamT

from .services import UserService

app = import_string(settings.IDP_USER_APP['FAUST_APP_PATH'])

"""
{
    "idp_user_id": 12,
    "username": "",
    "first_name": "",
    "last_name": "",
    "email": "",
    "app_specific_configs": {
        "app_identifier": {
            "Servicer": {
                "app_config": {"vehicle_ids": [1, 2]},
                "permission_restrictions": {
                    "synchronizeDoD": False
                }
            }
        }
    }
}
"""


class UserRecord(faust.Record):
    idp_user_id: int
    first_name: str = None
    last_name: str = None
    username: str = None
    email: str = None
    app_specific_configs: dict = None


user_updates = app.topic(settings.IDP_USER_APP['USER_UPDATES_TOPIC_NAME'], value_type=UserRecord)


@sync_to_async
def update_user(user_record: UserRecord):
    UserService.update_user(user_record.asdict())


@app.agent(user_updates)
async def update_user_stream_processor(user_records: StreamT[UserRecord]):
    async for user_record in user_records:
        if user_record.app_specific_configs.get(settings.IDP_USER_APP['APP_IDENTIFIER']):
            await update_user(user_record)
