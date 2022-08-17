class AuthenticationError(Exception):
    def __init__(self, detail: str = "Authentication Error"):
        super().__init__(detail)


class MissingHeaderError(Exception):
    def __init__(self, header_name):
        super().__init__(f"Missing header: {header_name}")


class UnsupportedAppEntityType(Exception):
    def __init__(self, app_entity_type):
        super().__init__(f"Unsupported app entity type: {str(app_entity_type)}")
