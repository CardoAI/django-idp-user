import faust
from asgiref.sync import sync_to_async
from django.conf import settings
from django.utils.module_loading import import_string
from faust import StreamT

from idp_user.services import UserService
from idp_user.settings import CONSUMER_APP_ENV

app = import_string(settings.IDP_USER_APP["FAUST_APP_PATH"])

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


async def update_user(user_record: UserRecord):
    await sync_to_async(UserService.process_user)(user_record.asdict())


async def verify_if_user_exists_and_delete_roles(user_record: UserRecord):
    await sync_to_async(UserService.verify_if_user_exists_and_delete_roles)(
        user_record.asdict()
    )


@app.agent(user_updates)
async def update_user_stream_processor(user_records: StreamT[UserRecord]):
    async for user_record in user_records:
        if user_record.app_specific_configs.get(
            settings.IDP_USER_APP["APP_IDENTIFIER"]
        ):
            await update_user(user_record)
        else:
            # Having arrived here means that the user does not have access in the current app
            # Verify however if the user already exists in the database of any tenant
            # If this is the case, delete his/her roles
            await verify_if_user_exists_and_delete_roles(user_record)
