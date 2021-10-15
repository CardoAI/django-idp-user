from collections import defaultdict

from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.db.models import QuerySet


def exclude_keys(dictionary, keys):
    return {k: v for k, v in dictionary.items() if k not in keys}


def keep_keys(dictionary, keys):
    return {k: v for k, v in dictionary.items() if k in keys}


def exclude_none_values(dictionary):
    return {k: v for k, v in dictionary.items() if v is not None}


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


def get_choice_value(choices, human_string):
    """Get database representation of a choice for a human readable value"""

    for value, representation in choices:
        if representation == human_string:
            return value
    return None
