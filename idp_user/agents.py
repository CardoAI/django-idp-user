import faust
from asgiref.sync import sync_to_async
from django.conf import settings
from django.utils.module_loading import import_string
from faust import StreamT

from .services import UserService
from .settings import CONSUMER_APP_ENV

app = import_string(settings.IDP_USER_APP['FAUST_APP_PATH'])

"""
{
    "username": "",
    "first_name": "",
    "last_name": "",
    "email": "",
    "app_specific_configs": {
        "app_identifier": {
            "tenant": {
                "Servicer": {
                    "app_entities_restrictions": {"vehicle": [1, 2]},
                    "permission_restrictions": {
                        "synchronizeDoD": False
                    }
                }
            },
        }
    }
}
"""


class UserRecord(faust.Record):
    first_name: str
    last_name: str
    username: str
    email: str
    is_active: bool
    is_staff: bool
    is_superuser: bool
    date_joined: str
    app_specific_configs: dict


USER_UPDATES_TOPIC_NAME = f"{CONSUMER_APP_ENV}_user_updates"

user_updates = app.topic(USER_UPDATES_TOPIC_NAME, value_type=UserRecord)


@sync_to_async
def update_user(user_record: UserRecord):
    UserService.process_user(user_record.asdict())


@app.agent(user_updates)
async def update_user_stream_processor(user_records: StreamT[UserRecord]):
    async for user_record in user_records:
        if user_record.app_specific_configs.get(settings.IDP_USER_APP['APP_IDENTIFIER']):
            await update_user(user_record)
