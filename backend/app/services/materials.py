"""资料业务：上传入库、列表、详情、受控下载、软删。

第 3 课的四道检查按序落地（《上传入库流程》）：
1. 角色——在 `core/deps.require_role("teacher")`，路由装配时即拦；
2. 扩展名 + MIME 白名单——本文件第一道；
3. 大小与数量——本文件第二道，**读完字节再判**，不采信请求头里的 size；
4. 落盘与写库——先写文件再写行，任一失败都回滚文件，不留无主文件。

事务边界：本文件负责 `commit()`；`repositories/` 不提交（02 §5）。
外部调用（嵌入、向量库）不在这里做——提交后由 `services/ingest.py` 在后台跑，
避免"事务里夹带外部调用"。
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import ApiError, ErrorCode
from app.core.ids import new_ulid
from app.models import Material
from app.repositories import chunks as chunks_repo
from app.repositories import materials as materials_repo
from app.services.auth import Principal

logger = logging.getLogger(__name__)

# 扩展名 → (落盘 MIME, 允许的客户端声明)。空串表示客户端没声明，按扩展名推定。
_TEXT_TYPES = frozenset({"text/plain", "application/octet-stream", ""})
EXT_MIME: dict[str, tuple[str, frozenset[str]]] = {
    "md": ("text/markdown", _TEXT_TYPES | {"text/markdown"}),
    "txt": ("text/plain", _TEXT_TYPES),
}

# 本班资料总数上限（materials spec MT-05）
MAX_MATERIALS_PER_CLASS = 500
TITLE_MAX = 120
FILENAME_MAX = 200
CHUNK_PAGE_SIZE = 200


@dataclass(frozen=True, slots=True)
class IncomingFile:
    """API 层把 `UploadFile` 转成这个结构再交给业务层——services/ 不认识 FastAPI。"""

    filename: str
    content_type: str
    data: bytes


def storage_dir(class_id: str) -> Path:
    return Path(get_settings().UPLOAD_DIR) / class_id


def sanitize_filename(raw: str) -> str:
    """原始文件名只作展示：去掉路径、控制字符、HTML 元字符，截断到 200 字符。"""
    base = raw.replace("\\", "/").split("/")[-1]
    cleaned = "".join(char for char in base if char.isprintable() and char not in '<>:"|?*').strip()
    cleaned = cleaned.lstrip(".")
    return cleaned[:FILENAME_MAX] or "unnamed"


def _extension_of(filename: str) -> str:
    if "." not in filename:
        return ""
    return filename.rsplit(".", 1)[-1].lower()


def _require_class(principal: Principal) -> str:
    if not principal.class_id:
        # 会话没有指向任何班级：与"班级已不存在"同样处理（RT-13）
        raise ApiError(ErrorCode.NOT_FOUND)
    return principal.class_id


def _validate_one(item: IncomingFile, allowed: list[str], max_bytes: int) -> tuple[str, str]:
    """返回 (扩展名, 落盘 MIME)；不合法直接抛 400。"""
    ext = _extension_of(item.filename)
    if ext not in allowed or ext not in EXT_MIME:
        raise ApiError(ErrorCode.INVALID_PARAM, f"仅支持 {'/'.join(allowed)} 格式")

    expected_mime, allowed_declared = EXT_MIME[ext]
    declared = (item.content_type or "").lower().split(";")[0].strip()
    if declared not in allowed_declared:
        raise ApiError(ErrorCode.INVALID_PARAM, f"文件类型与扩展名不符：{declared or '未知'}")

    size = len(item.data)
    if size <= 0:
        raise ApiError(ErrorCode.INVALID_PARAM, "文件内容为空")
    if size > max_bytes:
        raise ApiError(ErrorCode.OUT_OF_RANGE, f"单个文件不得超过 20 MiB（上限 {max_bytes} 字节）")
    return ext, expected_mime


async def upload(
    session: AsyncSession, principal: Principal, files: list[IncomingFile]
) -> list[Material]:
    settings = get_settings()
    class_id = _require_class(principal)
    allowed = settings.allowed_extensions

    if not files:
        raise ApiError(ErrorCode.INVALID_PARAM, "未选择文件")
    if len(files) > settings.UPLOAD_MAX_FILES:
        raise ApiError(
            ErrorCode.OUT_OF_RANGE,
            f"单批最多 {settings.UPLOAD_MAX_FILES} 个文件",
        )

    # 整批先校验，任一条不合法就整批拒绝，不落半批数据（MT-04）
    validated = [_validate_one(item, allowed, settings.UPLOAD_MAX_BYTES) for item in files]

    existing = await materials_repo.count_active(session, class_id)
    if existing + len(files) > MAX_MATERIALS_PER_CLASS:
        raise ApiError(ErrorCode.QUOTA_EXCEEDED, f"本班资料数已达 {MAX_MATERIALS_PER_CLASS} 条上限")

    directory = storage_dir(class_id)
    await asyncio.to_thread(directory.mkdir, parents=True, exist_ok=True)

    written: list[Path] = []
    created: list[Material] = []
    try:
        for item, (ext, mime) in zip(files, validated, strict=True):
            material_id = new_ulid()
            stored_filename = f"{material_id}.{ext}"
            target = directory / stored_filename
            await asyncio.to_thread(target.write_bytes, item.data)
            written.append(target)

            original = sanitize_filename(item.filename)
            title = original.rsplit(".", 1)[0][:TITLE_MAX] or original
            material = Material(
                id=material_id,
                class_id=class_id,
                title=title,
                original_filename=original,
                stored_filename=stored_filename,
                mime=mime,
                size_bytes=len(item.data),
                status="pending",
                chunk_count=0,
                uploaded_by=principal.user_id,
            )
            session.add(material)
            created.append(material)

        await session.commit()
    except Exception:
        # 写库失败要把已经落盘的文件删掉，否则磁盘上留下无主文件（第 3 课判据三的反面）
        for path in written:
            try:
                await asyncio.to_thread(path.unlink, True)
            except OSError:
                logger.warning("upload_cleanup_failed", extra={"path": str(path)})
        await session.rollback()
        raise

    logger.info(
        "materials_uploaded",
        extra={"class_id": class_id, "count": len(created), "user_id": principal.user_id},
    )
    return created


async def list_materials(
    session: AsyncSession,
    principal: Principal,
    *,
    page: int,
    page_size: int,
    sort: str,
    order: str,
    status: str | None,
) -> tuple[list[Material], int]:
    class_id = _require_class(principal)
    offset = (page - 1) * page_size
    items = await materials_repo.list_page(
        session,
        class_id,
        status=status,
        sort=sort,
        order=order,
        offset=offset,
        limit=page_size,
    )
    total = await materials_repo.count_page(session, class_id, status)
    return items, total


async def get_material(session: AsyncSession, principal: Principal, material_id: str) -> Material:
    class_id = _require_class(principal)
    material = await materials_repo.get_in_class(session, material_id, class_id)
    if material is None:
        # 跨班与不存在走同一个出口：这里不区分，响应自然逐字节一致
        raise ApiError(ErrorCode.NOT_FOUND)
    return material


async def list_chunks(
    session: AsyncSession, principal: Principal, material_id: str, chunk_page: int
) -> list[tuple[int, str, int, int, int]]:
    material = await get_material(session, principal, material_id)
    offset = (chunk_page - 1) * CHUNK_PAGE_SIZE
    rows = await chunks_repo.list_by_material(
        session, material.id, offset=offset, limit=CHUNK_PAGE_SIZE
    )
    return [
        (row.chunk_index, row.content, row.char_count, row.char_start, row.char_end) for row in rows
    ]


async def resolve_file(
    session: AsyncSession, principal: Principal, material_id: str
) -> tuple[Path, Material]:
    """先归属判定，再碰磁盘。路径由服务端拼，不用客户端给的任何字符串（03 §6）。"""
    material = await get_material(session, principal, material_id)
    path = storage_dir(material.class_id) / material.stored_filename
    if not await asyncio.to_thread(path.is_file):
        logger.warning("material_file_missing", extra={"material_id": material.id})
        raise ApiError(ErrorCode.NOT_FOUND)
    return path, material


async def soft_delete(session: AsyncSession, principal: Principal, material_id: str) -> datetime:
    material = await get_material(session, principal, material_id)
    if principal.role != "teacher":
        raise ApiError(ErrorCode.INSUFFICIENT_ROLE)
    deleted_at = await materials_repo.soft_delete(session, material.id, material.class_id)
    await session.commit()
    logger.info("material_soft_deleted", extra={"material_id": material.id})
    return deleted_at
