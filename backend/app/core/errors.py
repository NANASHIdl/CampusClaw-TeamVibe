"""错误码登记表与统一响应结构。

规范依据：
- docs/specs/02-后端开发规范.md §3（统一响应结构、错误码分区、/health 例外）
- openspec/changes/2026-10-28-bootstrap-skeleton/specs/platform-core/spec.md（PC-04 ~ PC-07）

新增错误码必须同时登记到本文件的 ErrorCode 枚举与 02 §3 的表，否则视为缺陷。
"""

from __future__ import annotations

from enum import IntEnum
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import get_logger

logger = get_logger(module="api")


class ErrorCode(IntEnum):
    """已登记的全部错误码。区间含义见 02 §3。"""

    OK = 0

    # 1000–1099 参数与校验（400）
    INVALID_PARAM = 1001
    OUT_OF_RANGE = 1002
    INVALID_ENUM = 1003
    INVALID_PAGINATION = 1004
    INVALID_SORT = 1005

    # 1100–1199 未认证（401）
    UNAUTHENTICATED = 1101
    INVALID_SESSION = 1102

    # 1200–1299 未授权与跨资源（404，与 1301 逐字节一致）
    CROSS_CLASS = 1201
    INSUFFICIENT_ROLE = 1202

    # 1300–1399 资源不存在（404）
    NOT_FOUND = 1301
    MATERIAL_NOT_FOUND = 1302

    # 1400–1499 业务规则不满足（409）
    STATE_NOT_ALLOWED = 1401
    QUOTA_EXCEEDED = 1402

    # 1500–1599 依赖不可达（503）
    NOT_IMPLEMENTED = 1500  # 骨架期占位：能力未实现，HTTP 501（PC-15）
    LLM_UNREACHABLE = 1501
    VECTOR_UNREACHABLE = 1502
    STORAGE_UNREACHABLE = 1503

    # 1600–1699 频率限制（429）
    RATE_LIMITED = 1601

    # 1700–1799 服务内部错误（500）
    INTERNAL = 1701


HTTP_STATUS: dict[ErrorCode, int] = {
    ErrorCode.OK: status.HTTP_200_OK,
    ErrorCode.INVALID_PARAM: status.HTTP_400_BAD_REQUEST,
    ErrorCode.OUT_OF_RANGE: status.HTTP_400_BAD_REQUEST,
    ErrorCode.INVALID_ENUM: status.HTTP_400_BAD_REQUEST,
    ErrorCode.INVALID_PAGINATION: status.HTTP_400_BAD_REQUEST,
    ErrorCode.INVALID_SORT: status.HTTP_400_BAD_REQUEST,
    ErrorCode.UNAUTHENTICATED: status.HTTP_401_UNAUTHORIZED,
    ErrorCode.INVALID_SESSION: status.HTTP_401_UNAUTHORIZED,
    ErrorCode.CROSS_CLASS: status.HTTP_404_NOT_FOUND,
    ErrorCode.INSUFFICIENT_ROLE: status.HTTP_404_NOT_FOUND,
    ErrorCode.NOT_FOUND: status.HTTP_404_NOT_FOUND,
    ErrorCode.MATERIAL_NOT_FOUND: status.HTTP_404_NOT_FOUND,
    ErrorCode.STATE_NOT_ALLOWED: status.HTTP_409_CONFLICT,
    ErrorCode.QUOTA_EXCEEDED: status.HTTP_409_CONFLICT,
    ErrorCode.NOT_IMPLEMENTED: status.HTTP_501_NOT_IMPLEMENTED,
    ErrorCode.LLM_UNREACHABLE: status.HTTP_503_SERVICE_UNAVAILABLE,
    ErrorCode.VECTOR_UNREACHABLE: status.HTTP_503_SERVICE_UNAVAILABLE,
    ErrorCode.STORAGE_UNREACHABLE: status.HTTP_503_SERVICE_UNAVAILABLE,
    ErrorCode.RATE_LIMITED: status.HTTP_429_TOO_MANY_REQUESTS,
    ErrorCode.INTERNAL: status.HTTP_500_INTERNAL_SERVER_ERROR,
}

# 资源不存在与跨班访问的文案必须完全一致（AGENTS.md §1.1）
NOT_FOUND_MESSAGE = "资源不存在"


class ApiError(Exception):
    """业务异常。由全局处理器转成统一信封，路由函数不手写外层。"""

    def __init__(
        self,
        code: ErrorCode,
        message: str | None = None,
        *,
        http_status: int | None = None,
    ) -> None:
        self.code = code
        self.message = message or DEFAULT_MESSAGES.get(code, NOT_FOUND_MESSAGE)
        self.http_status = http_status or HTTP_STATUS[code]
        super().__init__(self.message)


DEFAULT_MESSAGES: dict[ErrorCode, str] = {
    ErrorCode.INVALID_PARAM: "参数不合法",
    ErrorCode.OUT_OF_RANGE: "参数超出允许范围",
    ErrorCode.INVALID_ENUM: "取值不在允许的枚举内",
    ErrorCode.INVALID_PAGINATION: "分页参数不合法",
    ErrorCode.INVALID_SORT: "排序字段不在白名单内",
    ErrorCode.UNAUTHENTICATED: "未登录或会话已过期",
    ErrorCode.INVALID_SESSION: "会话令牌无效",
    ErrorCode.CROSS_CLASS: NOT_FOUND_MESSAGE,
    ErrorCode.INSUFFICIENT_ROLE: NOT_FOUND_MESSAGE,
    ErrorCode.NOT_FOUND: NOT_FOUND_MESSAGE,
    ErrorCode.MATERIAL_NOT_FOUND: NOT_FOUND_MESSAGE,
    ErrorCode.STATE_NOT_ALLOWED: "当前状态不允许该操作",
    ErrorCode.QUOTA_EXCEEDED: "超出配额",
    ErrorCode.NOT_IMPLEMENTED: "未实现",
    ErrorCode.LLM_UNREACHABLE: "模型服务暂不可用",
    ErrorCode.VECTOR_UNREACHABLE: "检索服务暂不可用，可改用关键词模式",
    ErrorCode.STORAGE_UNREACHABLE: "文件服务暂不可用",
    ErrorCode.RATE_LIMITED: "请求过于频繁，请稍后再试",
    ErrorCode.INTERNAL: "服务内部错误",
}


def not_implemented(route: str) -> ApiError:
    """骨架期占位：登记一条日志并返回 501 异常。

    返回 501 而不是 404，避免调用方把「路由没挂上」和「能力没实现」混为一谈（PC-15）。
    """
    logger.info("not_implemented", module="api", route=route)
    return ApiError(ErrorCode.NOT_IMPLEMENTED, "未实现")


def request_id_of(request: Request) -> str:
    """取当前请求的 request_id；中间件未跑到时兜底生成。"""
    request_id = getattr(request.state, "request_id", None)
    if request_id:
        return str(request_id)
    from app.core.ids import new_ulid

    return new_ulid()


def envelope(
    code: ErrorCode | int,
    message: str,
    data: Any,
    request_id: str,
) -> dict[str, Any]:
    """统一外层结构：{code, message, data, request_id}。"""
    return {
        "code": int(code),
        "message": message,
        "data": data,
        "request_id": request_id,
    }


def _error_response(
    request: Request,
    code: ErrorCode,
    message: str,
    http_status: int,
) -> JSONResponse:
    return JSONResponse(
        status_code=http_status,
        content=envelope(code, message, None, request_id_of(request)),
    )


def register_exception_handlers(app: FastAPI) -> None:
    """装配全局异常处理器。所有失败都从这里出去，路由函数只管抛。"""

    @app.exception_handler(ApiError)
    async def _api_error(request: Request, exc: ApiError) -> JSONResponse:
        logger.warning(
            "api_error",
            module="api",
            error_code=int(exc.code),
            route=request.url.path,
        )
        return _error_response(request, exc.code, exc.message, exc.http_status)

    @app.exception_handler(RequestValidationError)
    async def _validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        # 结构校验在 api/ 的绑定环节完成（02 §4），失败统一 1001
        fields = sorted({".".join(str(p) for p in err["loc"]) for err in exc.errors()})
        logger.warning(
            "param_invalid",
            module="api",
            error_code=int(ErrorCode.INVALID_PARAM),
            fields=fields,
            route=request.url.path,
        )
        return _error_response(
            request,
            ErrorCode.INVALID_PARAM,
            DEFAULT_MESSAGES[ErrorCode.INVALID_PARAM],
            status.HTTP_400_BAD_REQUEST,
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        if exc.status_code == status.HTTP_404_NOT_FOUND:
            # 未知路径与「资源不存在」返回一致，不泄露路由是否存在（PC-05）
            return _error_response(
                request,
                ErrorCode.NOT_FOUND,
                NOT_FOUND_MESSAGE,
                status.HTTP_404_NOT_FOUND,
            )
        if exc.status_code == status.HTTP_401_UNAUTHORIZED:
            return _error_response(
                request,
                ErrorCode.UNAUTHENTICATED,
                DEFAULT_MESSAGES[ErrorCode.UNAUTHENTICATED],
                status.HTTP_401_UNAUTHORIZED,
            )
        return _error_response(
            request,
            ErrorCode.INTERNAL,
            DEFAULT_MESSAGES[ErrorCode.INTERNAL],
            exc.status_code,
        )

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        # 堆栈只进日志，不进响应体（02 §3）
        logger.exception(
            "unhandled_error",
            module="api",
            error_code=int(ErrorCode.INTERNAL),
            route=request.url.path,
        )
        return _error_response(
            request,
            ErrorCode.INTERNAL,
            DEFAULT_MESSAGES[ErrorCode.INTERNAL],
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
