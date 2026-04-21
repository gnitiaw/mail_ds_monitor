"""统一异常处理器。

确保所有错误响应都符合契约定义的统一结构：
{
    "code": <error_code>,
    "message": "<error_message>",
    "data": null
}
"""

from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.schemas.common import ErrorCode, error


class BusinessException(Exception):
    """业务异常基类。"""

    def __init__(self, code: int, message: str, data: any = None):
        self.code = code
        self.message = message
        self.data = data
        super().__init__(message)


class NotFoundError(BusinessException):
    """资源不存在异常。"""

    def __init__(self, message: str = "资源不存在"):
        super().__init__(ErrorCode.NOT_FOUND, message)


class ConflictError(BusinessException):
    """状态冲突异常。"""

    def __init__(self, message: str, code: int = ErrorCode.CONFLICT):
        super().__init__(code, message)


class ParamError(BusinessException):
    """参数错误异常。"""

    def __init__(self, message: str):
        super().__init__(ErrorCode.PARAM_ERROR, message)


class UnauthorizedError(BusinessException):
    """未登录异常。"""

    def __init__(self, message: str = "未登录"):
        super().__init__(ErrorCode.UNAUTHORIZED, message)


class ForbiddenError(BusinessException):
    """无权限异常。"""

    def __init__(self, message: str = "无权限"):
        super().__init__(ErrorCode.FORBIDDEN, message)


def register_exception_handlers(app: FastAPI) -> None:
    """注册统一异常处理器。"""

    @app.exception_handler(BusinessException)
    async def business_exception_handler(request: Request, exc: BusinessException) -> JSONResponse:
        """处理业务异常。"""
        return JSONResponse(
            status_code=_http_status_from_code(exc.code),
            content=error(exc.code, exc.message, exc.data),
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        """处理 HTTP 异常，转换为统一格式。"""
        # 如果 detail 已经是统一格式（字典包含 code/message），直接使用
        if isinstance(exc.detail, dict) and "code" in exc.detail and "message" in exc.detail:
            return JSONResponse(
                status_code=exc.status_code,
                content=error(exc.detail["code"], exc.detail["message"], exc.detail.get("data")),
            )

        # 否则根据 HTTP 状态码映射到契约错误码
        code = _map_http_to_contract_code(exc.status_code)
        message = str(exc.detail) if exc.detail else _default_message_for_code(code)

        return JSONResponse(
            status_code=exc.status_code,
            content=error(code, message),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        """处理请求验证错误。"""
        # 提取验证错误信息
        errors = exc.errors()
        if errors:
            first_error = errors[0]
            loc = " -> ".join(str(x) for x in first_error.get("loc", []))
            msg = first_error.get("msg", "参数验证失败")
            message = f"{loc}: {msg}"
        else:
            message = "参数验证失败"

        return JSONResponse(
            status_code=422,
            content=error(ErrorCode.PARAM_ERROR, message),
        )

    @app.exception_handler(ValidationError)
    async def pydantic_validation_handler(request: Request, exc: ValidationError) -> JSONResponse:
        """处理 Pydantic 验证错误。"""
        errors = exc.errors()
        if errors:
            first_error = errors[0]
            loc = " -> ".join(str(x) for x in first_error.get("loc", []))
            msg = first_error.get("msg", "数据验证失败")
            message = f"{loc}: {msg}"
        else:
            message = "数据验证失败"

        return JSONResponse(
            status_code=422,
            content=error(ErrorCode.PARAM_ERROR, message),
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """处理未捕获的异常。"""
        # 生产环境不暴露详细错误信息
        return JSONResponse(
            status_code=500,
            content=error(ErrorCode.SYSTEM_ERROR, "系统异常"),
        )


def _http_status_from_code(code: int) -> int:
    """根据契约错误码映射 HTTP 状态码。"""
    http_family = code // 100

    if http_family == 404:
        return 404
    elif http_family == 409:
        return 409
    elif http_family == 400:
        return 400
    elif http_family == 401:
        return 401
    elif http_family == 403:
        return 403
    elif http_family == 500:
        return 500
    else:
        return 400


def _map_http_to_contract_code(http_status: int) -> int:
    """根据 HTTP 状态码映射契约错误码。"""
    mapping = {
        400: ErrorCode.PARAM_ERROR,
        401: ErrorCode.UNAUTHORIZED,
        403: ErrorCode.FORBIDDEN,
        404: ErrorCode.NOT_FOUND,
        409: ErrorCode.CONFLICT,
        422: ErrorCode.PARAM_ERROR,
        500: ErrorCode.SYSTEM_ERROR,
    }
    return mapping.get(http_status, ErrorCode.SYSTEM_ERROR)


def _default_message_for_code(code: int) -> str:
    """根据错误码返回默认消息。"""
    messages = {
        ErrorCode.PARAM_ERROR: "参数错误",
        ErrorCode.UNAUTHORIZED: "未登录",
        ErrorCode.FORBIDDEN: "无权限",
        ErrorCode.NOT_FOUND: "资源不存在",
        ErrorCode.CONFLICT: "状态冲突",
        ErrorCode.SINGLE_PROJECT_CONFLICT: "V1 仅允许单项目试点，当前已有其他启用中的项目配置",
        ErrorCode.EXPORT_BLOCKED: "当前报告禁止导出",
        ErrorCode.SYSTEM_ERROR: "系统异常",
    }
    return messages.get(code, "未知错误")
