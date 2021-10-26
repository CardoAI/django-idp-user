class DoesNotExist(Exception):
    def __init__(self, message="Record does not exist!"):
        super().__init__(message)


class AuthenticationError(Exception):
    def __init__(self, detail: str = "Authentication Error"):
        super().__init__(detail)


class MissingHeadersError(Exception):
    def __init__(self, detail: str = "Missing Headers Error"):
        super().__init__(detail)
