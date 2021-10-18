from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned


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
