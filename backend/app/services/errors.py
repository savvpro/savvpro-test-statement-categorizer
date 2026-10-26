class ServiceError(Exception):
    """Base class for errors the API turns into HTTP responses."""


class NotFoundError(ServiceError):
    pass


class UnprocessableError(ServiceError):
    pass
