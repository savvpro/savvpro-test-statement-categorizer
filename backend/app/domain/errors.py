"""Domain-level errors, translated to HTTP responses at the API boundary."""


class DomainError(Exception):
    """Base class for expected, user-facing failures."""


class StatementError(DomainError):
    """The file as a whole cannot be read as a statement."""


class UnsupportedFormatError(DomainError):
    """No reader is registered for the uploaded file type."""


class FileTooLargeError(DomainError):
    """The upload exceeds the configured size limit."""
