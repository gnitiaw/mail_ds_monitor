"""统一响应包装模型。

按照契约要求，所有 API 响应应包含：
- code: 状态码
- message: 状态信息
- data: 实际数据
"""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """统一 API 响应结构。"""

    code: int = 0
    message: str = "success"
    data: T | None = None


class PagedData(BaseModel, Generic[T]):
    """分页数据结构。"""

    items: list[T]
    page: int
    page_size: int
    total: int


def success(data: Any = None, message: str = "success") -> dict:
    """构建成功响应。"""
    return {
        "code": 0,
        "message": message,
        "data": data,
    }


def error(code: int, message: str, data: Any = None) -> dict:
    """构建错误响应。"""
    return {
        "code": code,
        "message": message,
        "data": data,
    }


# 契约定义的错误码
class ErrorCode:
    """契约定义的错误码。"""

    PARAM_ERROR = 40001
    UNAUTHORIZED = 40101
    FORBIDDEN = 40301
    NOT_FOUND = 40401
    CONFLICT = 40901
    SINGLE_PROJECT_CONFLICT = 40902
    EXPORT_BLOCKED = 40903
    SYSTEM_ERROR = 50001
