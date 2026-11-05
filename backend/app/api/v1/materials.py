"""资料路由。

准入声明：上传与删除只允许本班教师（`require_role("teacher")` → 404 `1202`）；
列表、详情、原文需登录（`get_current_user`），班级由会话决定，不看参数。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, BackgroundTasks, File, Query, Request, Response, UploadFile
from fastapi.responses import FileResponse

from app.core.deps import CurrentUser, DbSession, TeacherOnly
from app.core.errors import ApiError, ErrorCode, success
from app.schemas import ChunkOut, MaterialDeleteOut, MaterialDetailOut, MaterialOut, MaterialPageOut
from app.services import ingest as ingest_service
from app.services import materials as materials_service

router = APIRouter(prefix="/materials", tags=["materials"])

# MT-10：筛选与排序只接受白名单值，非法值必须报错，不得静默忽略后返回全量
ALLOWED_STATUS = {"pending", "processing", "ready", "failed"}
ALLOWED_SORTS = {"created_at", "title"}
ALLOWED_ORDERS = {"asc", "desc"}
# 读文件时的分块大小，避免把 20 MiB 一次性读进内存
_READ_CHUNK = 1 << 20


def _content_disposition(filename: str) -> str:
    """RFC 6266：ASCII 兜底名 + 完整 UTF-8 名，两个都给。

    为什么不能只给 `filename*`：Starlette 遇到非 ASCII 文件名时**只**输出
    `filename*=utf-8''…`，不附带 ASCII 的 `filename=`。Chrome / Edge / Firefox 认，
    但下载工具、部分移动端浏览器和不解析 RFC 5987 的客户端会拿到空文件名，
    表现为「点了没反应」或存成一个无扩展名的文件。这里补一个 `material.md` 之类的
    兜底名，由客户端自己挑能用的那个。
    """
    suffix = Path(filename).suffix
    if not suffix or not suffix.isascii():
        suffix = ""
    return f"attachment; filename=\"material{suffix}\"; filename*=UTF-8''{quote(filename, safe='')}"


def _file_headers(material: Any) -> dict[str, str]:
    return {
        "Content-Disposition": _content_disposition(material.original_filename),
        "X-Content-Type-Options": "nosniff",
        "Cache-Control": "private, no-store",
    }


def _to_out(material: Any) -> MaterialOut:
    return MaterialOut(
        id=material.id,
        title=material.title,
        original_filename=material.original_filename,
        mime=material.mime,
        size_bytes=material.size_bytes,
        status=material.status,
        failure_reason=material.failure_reason,
        chunk_count=material.chunk_count,
        created_at=material.created_at,
    )


async def _read_limited(upload: UploadFile, max_bytes: int) -> bytes:
    """边读边判上限：客户端声明的长度不可信，只有读出来的字节数算数。"""
    buffer = bytearray()
    while True:
        chunk = await upload.read(_READ_CHUNK)
        if not chunk:
            break
        buffer.extend(chunk)
        if len(buffer) > max_bytes:
            raise ApiError(ErrorCode.OUT_OF_RANGE, "单个文件不得超过 20 MiB")
    return bytes(buffer)


@router.get("", summary="资料列表（分页，本班）")
async def list_materials(
    request: Request,
    session: DbSession,
    principal: CurrentUser,
    page: int = Query(default=1, description="页码，从 1 开始"),
    page_size: int = Query(default=20, description="每页条数，上限 50"),
    sort: str = Query(default="created_at"),
    order: str = Query(default="desc"),
    status: str | None = Query(default=None),
) -> dict[str, Any]:
    # 分页越界不静默钳位，直接 1004（02 §8 判据）
    if page < 1 or page_size < 1 or page_size > 50:
        raise ApiError(ErrorCode.INVALID_PAGINATION, "分页参数不合法：page ≥ 1，1 ≤ page_size ≤ 50")
    if sort not in ALLOWED_SORTS:
        raise ApiError(ErrorCode.INVALID_SORT, "排序字段不在白名单内")
    if order not in ALLOWED_ORDERS:
        raise ApiError(ErrorCode.INVALID_SORT, "排序方向只接受 asc/desc")
    if status is not None and status not in ALLOWED_STATUS:
        raise ApiError(ErrorCode.INVALID_ENUM, "status 只接受 pending/processing/ready/failed")

    items, total = await materials_service.list_materials(
        session,
        principal,
        page=page,
        page_size=page_size,
        sort=sort,
        order=order,
        status=status,
    )
    body = MaterialPageOut(
        total=total, page=page, page_size=page_size, items=[_to_out(item) for item in items]
    )
    return success(request, body)


@router.post("", summary="教师上传资料（教师，multipart，单批 ≤ 20 个）")
async def upload_materials(
    request: Request,
    background: BackgroundTasks,
    session: DbSession,
    principal: TeacherOnly,
    # File(...) 是 FastAPI 的声明式用法，默认值就是依赖标记，不是普通默认参数
    files: list[UploadFile] = File(  # noqa: B008
        ..., description=".md / .txt，单个 ≤ 20 MiB"
    ),
) -> dict[str, Any]:
    from app.core.config import get_settings

    settings = get_settings()
    incoming = [
        materials_service.IncomingFile(
            filename=upload.filename or "",
            content_type=upload.content_type or "",
            data=await _read_limited(upload, settings.UPLOAD_MAX_BYTES),
        )
        for upload in files
    ]

    created = await materials_service.upload(session, principal, incoming)
    # 入库是后台任务：请求先返回 pending，切片与向量在事务外做（02 §5）
    for material in created:
        background.add_task(ingest_service.process_material, material.id, material.class_id)

    return success(
        request,
        {"total": len(created), "items": [_to_out(material) for material in created]},
        message="created",
    )


@router.get("/{material_id}", summary="资料详情（含切片）")
async def read_material(
    material_id: str,
    request: Request,
    session: DbSession,
    principal: CurrentUser,
    chunk_page: int = Query(default=1, ge=1),
) -> dict[str, Any]:
    material = await materials_service.get_material(session, principal, material_id)
    rows = await materials_service.list_chunks(session, principal, material_id, chunk_page)
    base = _to_out(material)
    body = MaterialDetailOut(
        **base.model_dump(),
        chunks=[
            ChunkOut(
                chunk_index=index,
                content=content,
                char_count=char_count,
                char_start=char_start,
                char_end=char_end,
            )
            for index, content, char_count, char_start, char_end in rows
        ],
    )
    return success(request, body)


@router.get("/{material_id}/file", summary="原文受控下载（先归属判定再流式返回）")
async def download_material(
    material_id: str, session: DbSession, principal: CurrentUser
) -> FileResponse:
    path, material = await materials_service.resolve_file(session, principal, material_id)
    # 原文是字节流，套统一信封没有意义；MT-14 单独约定了这两个响应头
    # filename 不交给 FileResponse 生成：它的非 ASCII 分支不会带 ASCII 兜底名
    return FileResponse(path=str(path), media_type=material.mime, headers=_file_headers(material))


@router.head("/{material_id}/file", include_in_schema=False)
async def head_material_file(
    material_id: str, session: DbSession, principal: CurrentUser
) -> Response:
    """HEAD 与 GET 同权：只是不返回正文。

    浏览器的下载管理器、杀毒软件与 Office 之类的客户端会先发 HEAD 探一次，
    只注册 GET 时这里回 405，它们会直接判定「下载失败」。状态码也必须与 GET 一致
    （未登录 401、跨班 404），否则又是一条可枚举的旁路。
    """
    _, material = await materials_service.resolve_file(session, principal, material_id)
    return Response(status_code=200, media_type=material.mime, headers=_file_headers(material))


@router.delete("/{material_id}", summary="软删资料（教师）")
async def delete_material(
    material_id: str,
    request: Request,
    background: BackgroundTasks,
    session: DbSession,
    principal: TeacherOnly,
) -> dict[str, Any]:
    material = await materials_service.get_material(session, principal, material_id)
    deleted_at = await materials_service.soft_delete(session, principal, material_id)
    background.add_task(
        ingest_service.delete_material_assets,
        material.id,
        material.class_id,
        material.stored_filename,
    )
    return success(request, MaterialDeleteOut(id=material.id, deleted_at=deleted_at))
