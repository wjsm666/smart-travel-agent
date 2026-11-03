"""Sanitized error types shared across backend modules."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class AppError(Exception):
    def __init__(self, code: str, message: str, status_code: int) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


class ValidationError(AppError):
    def __init__(self, message: str = "请求内容不符合要求。") -> None:
        super().__init__("VALIDATION_ERROR", message, 422)


class NotFoundError(AppError):
    def __init__(self, message: str = "未找到所需记录。") -> None:
        super().__init__("NOT_FOUND", message, 404)


class StorageError(AppError):
    def __init__(self, message: str = "示例数据读取失败，请检查本地数据文件。") -> None:
        super().__init__("STORAGE_ERROR", message, 500)


class AgentUnavailable(AppError):
    def __init__(self, message: str = "AI 规划暂不可用，请检查模型服务配置。") -> None:
        super().__init__("AGENT_UNAVAILABLE", message, 503)


class AgentTimeout(AppError):
    def __init__(self) -> None:
        super().__init__("AGENT_TIMEOUT", "AI 规划请求超时，请稍后重试。", 504)


class AgentInvalidOutput(AppError):
    def __init__(self) -> None:
        super().__init__("AGENT_INVALID_OUTPUT", "AI 生成的行程不符合要求，请重试。", 502)


class AgentLimitExceeded(AppError):
    def __init__(self) -> None:
        super().__init__("AGENT_LIMIT_EXCEEDED", "AI 规划超过调用次数限制。", 502)


class ServiceNotReady(AppError):
    """Temporary integration response until member A's services are available."""

    def __init__(self) -> None:
        super().__init__("SERVICE_NOT_READY", "行程校验服务尚未接入。", 503)


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(_request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code, content={"code": exc.code, "message": exc.message}
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation(_request: Request, _exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={"code": "VALIDATION_ERROR", "message": "请求内容不符合要求。"},
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
        if exc.status_code == 404:
            return JSONResponse(
                status_code=404, content={"code": "NOT_FOUND", "message": "接口或记录不存在。"}
            )
        return JSONResponse(
            status_code=exc.status_code, content={"code": "HTTP_ERROR", "message": "请求无法处理。"}
        )
