class DoesNotExist(Exception):
    def __init__(self, message="Record does not exist!"):
        super().__init__(message)


class AuthenticationError(Exception):
    def __init__(self, detail: str = "Authentication Error"):
        super().__init__(detail)


class MissingHeaderError(Exception):
    def __init__(self, header_name):
        super().__init__(f"Missing header: {header_name}")
