"""Application errors that map onto the API's {code, message} error shape."""

from __future__ import annotations


class AppError(Exception):
    status_code = 400
    code = "bad_request"

    def __init__(self, message: str, *, code: str | None = None, status_code: int | None = None):
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code
        if status_code is not None:
            self.status_code = status_code


class FileProblem(AppError):
    """The uploaded file cannot be turned into transactions."""

    status_code = 422
    code = "file_corrupt"


class NotFound(AppError):
    status_code = 404
    code = "statement_not_found"


class InvalidCategory(AppError):
    status_code = 422
    code = "invalid_category"
