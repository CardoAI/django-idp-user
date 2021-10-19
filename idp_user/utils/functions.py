import json

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned


APP_IDENTIFIER = settings.IDP_USER_APP['APP_IDENTIFIER']


def keep_keys(dictionary, keys):
    return {k: v for k, v in dictionary.items() if k in keys}


def get_or_none(records, *args, **kwargs):
    try:
        return records.get(*args, **kwargs)
    except ObjectDoesNotExist:
        return None
    except MultipleObjectsReturned:
        return records.filter(*args, **kwargs)[0]


def update_record(record, save=True, **data):
    if data:
        for key, value in data.items():
            setattr(record, key, value)
        if save:
            record.save()
    return record


def cache_user_service_results(function):
    def wrapper(user, *args, **kwargs):
        cache_key = f"{APP_IDENTIFIER}-{user.username}-{function.__name__}"
        for arg in args:
            cache_key += f",{arg}"
        for key, value in kwargs.items():
            cache_key += f",{key}={value}"

        result = cache.get(cache_key)
        if result:
            return json.loads(result)
        else:
            result = function(user=user, *args, **kwargs)
            cache.set(cache_key, json.dumps(result))
            return result

    # Return the original function if USE_REDIS_CACHE is False
    return wrapper if settings.IDP_USER_APP.get('USE_REDIS_CACHE', False) else function
