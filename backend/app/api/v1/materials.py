"""资料路由（骨架期空壳）。

准入声明：上传与删除需教师（`require_role`），列表、详情、原文需登录（`get_current_user`）。
业务实现见 tasks.md 第 4 组（materials）。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.deps import get_current_user, require_role
from app.core.errors import not_implemented

router = APIRouter(prefix="/materials", tags=["materials"])


@router.get("", summary="资料列表（分页）", dependencies=[Depends(get_current_user)])
async def list_materials() -> None:
    raise not_implemented("/api/v1/materials")


@router.post("", summary="教师上传资料", dependencies=[Depends(require_role)])
async def upload_material() -> None:
    raise not_implemented("/api/v1/materials")


@router.get("/{material_id}", summary="资料详情", dependencies=[Depends(get_current_user)])
async def read_material(material_id: str) -> None:
    raise not_implemented("/api/v1/materials/{id}")


@router.get(
    "/{material_id}/file",
    summary="原文受控下载",
    dependencies=[Depends(get_current_user)],
)
async def download_material(material_id: str) -> None:
    raise not_implemented("/api/v1/materials/{id}/file")


@router.delete("/{material_id}", summary="软删资料", dependencies=[Depends(require_role)])
async def delete_material(material_id: str) -> None:
    raise not_implemented("/api/v1/materials/{id}")
