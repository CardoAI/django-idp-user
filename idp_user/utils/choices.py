class ChoicesMixin:
    """
    A helper class, mostly useful to declare roles, in the form:

    class Roles(ChoicesMixin):
        RoleName = "role_database_name"
    """
    @classmethod
    def choices(cls):
        return {label: value for (label, value) in cls.__dict__.items() if not label.startswith('_')}

    @classmethod
    def as_list(cls):
        return [(value, label) for (label, value) in cls.__dict__.items() if not label.startswith('_')]

    @classmethod
    def as_dict(cls):
        return {value: label for (label, value) in cls.__dict__.items() if not label.startswith('_')}
