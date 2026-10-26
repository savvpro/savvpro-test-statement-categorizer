"""Service-level failures. The API layer maps each to an HTTP status and an ErrorOut body."""


class ServiceError(Exception):
    status_code = 400
    code = "bad_request"

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class InvalidUpload(ServiceError):
    code = "invalid_upload"


class UploadTooLarge(ServiceError):
    status_code = 413
    code = "file_too_large"


class NotFound(ServiceError):
    status_code = 404
    code = "not_found"


class InvalidCategory(ServiceError):
    status_code = 422
    code = "invalid_category"


class DuplicateStatement(ServiceError):
    status_code = 409
    code = "duplicate_statement"

    def __init__(self, statement_id: int) -> None:
        super().__init__(f"this file was already uploaded as statement {statement_id}")
        self.statement_id = statement_id
