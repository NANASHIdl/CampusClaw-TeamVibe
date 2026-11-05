"""预置数据。

为什么需要它（第 3 课《种子数据必须满足什么》）：
隔离这条判据没法只靠一个班验证——只有一个班时，「跨班不可见」无从复现。
所以至少要两个班，每班各含教师与学生，且两班的资料标题必须可区分。

两个班的账号用同一套 `SEED_*` 派生：`teacher@x.edu` → `teacher+b@x.edu`。
这样不必为第二个班再造两把密钥，也不需要把口令写进代码。

只在 `APP_ENV=dev|test` 且 `SEED_*` 齐全时执行；生产环境出现 `SEED_*` 会在配置层直接
启动失败（02 §7），根本走不到这里。
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.ids import new_ulid
from app.core.security import hash_password
from app.models import ClassRoom, Material, Membership, User
from app.repositories import classes as classes_repo
from app.repositories import materials as materials_repo
from app.repositories import users as users_repo
from app.repositories.base import session_scope
from app.services.ingest import process_material
from app.services.materials import storage_dir

logger = logging.getLogger(__name__)

CLASS_A_NAME = "2026 秋 · 数据结构 · 1 班"
CLASS_B_NAME = "2026 秋 · 数据结构 · 2 班"

# 每班 3 份资料（07 §8）。标题刻意不重名，否则判据二无法分辨取到的是哪个班的数据。
SEED_MATERIALS: dict[str, list[tuple[str, str]]] = {
    CLASS_A_NAME: [
        (
            "第一章 主定理与递归树",
            "主定理的递归树证明\n\n"
            "递归树把分治递推式 T(n)=aT(n/b)+f(n) 展开成一棵树，逐层求和。\n"
            "当 f(n) 的增长慢于 n^(log_b a) 时，叶子层的代价占主导，结论是 T(n)=Θ(n^(log_b a))。\n"
            "当 f(n) 与 n^(log_b a) 同阶时，每一层的代价相当，总代价要乘上树高 log_b n。\n"
            "递归树不是严格的证明，它给出猜测，严格证明用替换法（代入归纳）。\n",
        ),
        (
            "第二章 平衡树的分裂",
            "B 树分裂的三种情况\n\n"
            "B 树插入到满节点时需要分裂：把中间关键字上提到父节点，左右两半各自成节点。\n"
            "情况一：父节点未满，直接接收上提的关键字。\n"
            "情况二：父节点已满，继续向上分裂，可能一直传到根。\n"
            "情况三：根节点分裂，树高加一，这是 B 树「所有叶子同深度」性质的来源。\n",
        ),
        (
            "第三章 贪心与交换论证",
            "贪心选择的交换论证\n\n"
            "证明贪心正确性的标准套路是交换论证：假设最优解与贪心解在某一步首次不同，\n"
            "把最优解里的那个选择换成贪心的选择，说明代价不变差，于是存在一个与贪心前缀一致的最优解。\n"
            "归纳下去，贪心解就是最优解。区间调度、霍夫曼编码都用这套论证。\n",
        ),
    ],
    CLASS_B_NAME: [
        (
            "B 班讲义 图与最短路",
            "单源最短路的两种算法\n\n"
            "Dijkstra 适用于非负权，用优先队列每次取出当前距离最小的点，复杂度 O((V+E)logV)。\n"
            "Bellman-Ford 允许负权边，做 V-1 轮松弛，还能检测负环。\n"
            "两者的共同前提是「最优子结构」：最短路的前缀也是最短路。\n",
        ),
        (
            "B 班讲义 动态规划状态设计",
            "状态设计与无后效性\n\n"
            "动态规划的关键不是写转移方程，而是把状态设计成「无后效」的：\n"
            "一旦确定了状态的划分，后面的决策不再依赖到达该状态的具体路径。\n"
            "背包问题用「前 i 件物品、容量 j」正是为了让路径信息被压进状态本身。\n",
        ),
        (
            "B 班讲义 摊还分析",
            "摊还分析的三种方法\n\n"
            "聚合分析：算出 n 次操作的总代价再平均。\n"
            "记账法：给每种操作预存代价，后面超额时支取。\n"
            "势能法：定义势函数，摊还代价等于实际代价加上势能变化。\n"
            "动态扩容数组的均摊 O(1) 是这三个方法共同的经典例子。\n",
        ),
    ],
}


def _derive_email(email: str, suffix: str) -> str:
    if "@" not in email:
        return f"{email}{suffix}"
    local, domain = email.split("@", 1)
    return f"{local}{suffix}@{domain}"


async def _ensure_user(session: AsyncSession, email: str, display_name: str, password: str) -> User:
    existing = await users_repo.get_by_email(session, email)
    if existing is not None:
        return existing
    user = User(
        id=new_ulid(),
        email=email,
        display_name=display_name,
        password_hash=hash_password(password),
        is_active=True,
    )
    users_repo.add(session, user)
    await session.flush()
    return user


async def _ensure_membership(session: AsyncSession, class_id: str, user_id: str, role: str) -> None:
    existing = await classes_repo.get_membership(session, class_id, user_id)
    if existing is not None:
        return
    session.add(Membership(id=new_ulid(), class_id=class_id, user_id=user_id, role=role))


async def _ensure_class(session: AsyncSession, name: str, owner_id: str) -> ClassRoom:
    existing = await classes_repo.get_class_by_name(session, name)
    if existing is not None:
        return existing
    room = ClassRoom(id=new_ulid(), name=name, join_code=_code_for(name), owner_id=owner_id)
    classes_repo.add_class(session, room)
    await session.flush()
    return room


def _code_for(name: str) -> str:
    """固定入班码，方便 README 直接写出来；两班使用不同的码。"""
    if name == CLASS_B_NAME:
        return "CLSBB222"
    return "CLSAA111"


async def _ensure_materials(
    session: AsyncSession, room: ClassRoom, uploader_id: str
) -> list[tuple[str, str]]:
    existing = await materials_repo.count_active(session, room.id)
    if existing > 0:
        return []

    directory = Path(storage_dir(room.id))
    await asyncio.to_thread(directory.mkdir, parents=True, exist_ok=True)

    pending: list[tuple[str, str]] = []
    for title, content in SEED_MATERIALS.get(room.name, []):
        material_id = new_ulid()
        stored = f"{material_id}.md"
        await asyncio.to_thread((directory / stored).write_text, content, "utf-8")
        session.add(
            Material(
                id=material_id,
                class_id=room.id,
                title=title,
                original_filename=f"{title}.md",
                stored_filename=stored,
                mime="text/markdown",
                size_bytes=len(content.encode("utf-8")),
                status="pending",
                chunk_count=0,
                uploaded_by=uploader_id,
            )
        )
        pending.append((material_id, room.id))
    return pending


async def ensure_seed_data() -> None:
    settings = get_settings()
    if not settings.is_dev:
        return
    required = (
        settings.SEED_TEACHER_EMAIL,
        settings.SEED_TEACHER_PASSWORD,
        settings.SEED_STUDENT_EMAIL,
        settings.SEED_STUDENT_PASSWORD,
    )
    if not all(required):
        logger.info("seed_skipped", extra={"reason": "seed_keys_missing"})
        return

    suffix = settings.SEED_CLASS_B_SUFFIX
    teacher_b_email = _derive_email(settings.SEED_TEACHER_EMAIL, suffix)
    student_b_email = _derive_email(settings.SEED_STUDENT_EMAIL, suffix)

    async with session_scope() as session:
        teacher = await _ensure_user(
            session, settings.SEED_TEACHER_EMAIL, "张老师", settings.SEED_TEACHER_PASSWORD
        )
        student = await _ensure_user(
            session, settings.SEED_STUDENT_EMAIL, "李明", settings.SEED_STUDENT_PASSWORD
        )
        teacher_b = await _ensure_user(
            session, teacher_b_email, "王老师", settings.SEED_TEACHER_PASSWORD
        )
        student_b = await _ensure_user(
            session, student_b_email, "王芳", settings.SEED_STUDENT_PASSWORD
        )

        room_a = await _ensure_class(session, CLASS_A_NAME, teacher.id)
        room_b = await _ensure_class(session, CLASS_B_NAME, teacher_b.id)

        await _ensure_membership(session, room_a.id, teacher.id, "teacher")
        await _ensure_membership(session, room_a.id, student.id, "student")
        await _ensure_membership(session, room_b.id, teacher_b.id, "teacher")
        await _ensure_membership(session, room_b.id, student_b.id, "student")

        pending = await _ensure_materials(session, room_a, teacher.id)
        pending += await _ensure_materials(session, room_b, teacher_b.id)
        await session.commit()

    # 入库放在事务外：嵌入与向量库都是外部调用（02 §5）
    for material_id, class_id in pending:
        await process_material(material_id, class_id)

    logger.info(
        "seed_ready",
        extra={"classes": 2, "materials_ingested": len(pending)},
    )
