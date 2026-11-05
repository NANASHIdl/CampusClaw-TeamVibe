"""班级与成员的出入参。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ClassCreateIn(BaseModel):
    name: str = Field(min_length=2, max_length=40)


class ClassJoinIn(BaseModel):
    # 入班码固定 8 位，大写字母 + 数字（数据字典 § classes）
    join_code: str = Field(min_length=8, max_length=8, pattern=r"^[A-Z0-9]{8}$")


class ClassOut(BaseModel):
    id: str
    name: str
    role: str
    member_count: int
    # 只在「我是本班教师」时返回；学生看到的入班码会把班级变成公开注册
    join_code: str | None = None


class MemberOut(BaseModel):
    user_id: str
    display_name: str
    role: str


class MemberListOut(BaseModel):
    class_id: str
    members: list[MemberOut]
