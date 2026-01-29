from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, PlainTextResponse  # noqa: F401
from starlette.exceptions import HTTPException as StarletteHTTPException

from app_server.main import app
from app_server.share.my_exception import UnicornException


# カスタム例外ハンドラー
@app.exception_handler(UnicornException)
async def unicorn_exception_handler(_request: Request, exc: UnicornException):
    # content配下がレスポンス内容になる
    return JSONResponse(
        status_code=418,
        content={"message": f"Oops! {exc.name} did something. There goes a rainbow..."},
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(_request: Request, exc: StarletteHTTPException):
    # return PlainTextResponse(str(exc.detail), status_code=exc.status_code)
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": str(exc.detail)},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_request: Request, exc: RequestValidationError):
    # return PlainTextResponse(str(exc), status_code=400)
    return JSONResponse(
        status_code=400,
        content={"message": str(exc)},
    )
