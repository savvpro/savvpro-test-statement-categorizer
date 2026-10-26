from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.services.errors import NotFoundError, UnprocessableError


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(NotFoundError)
    async def _not_found(_: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(UnprocessableError)
    async def _unprocessable(_: Request, exc: UnprocessableError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(exc)})
