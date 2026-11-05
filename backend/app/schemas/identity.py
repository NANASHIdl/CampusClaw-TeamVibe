"""身份与会话的出入参。

结构校验只在这里（02 §4）：进入 services/ 的对象一律视为已校验。
注意：不引入 `EmailStr`——它要求额外安装 `email-validator`，本项目锁定依赖里没有，
用正则表达式达到同一效果，不为此新增依赖。
"""

from __future__ import annotations

from pydantic import BaseModel, Field

# 校内邮箱量级的宽松校验：本地部分 1–64、域名带点、总长不超 160
EMAIL_PATTERN = r"^[A-Za-z0-9._%+-]{1,64}@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"


class LoginIn(BaseModel):
    email: str = Field(pattern=EMAIL_PATTERN, max_length=160)
    # 8–72：下界防弱口令，上界是 bcrypt 的硬上限（03 §10）
    password: str = Field(min_length=8, max_length=72)


class ClassBrief(BaseModel):
    id: str
    name: str
    role: str


class LoginOut(BaseModel):
    """ID-02：data 含 id / display_name / role / classes，不含任何令牌与口令哈希。"""

    id: str
    display_name: str
    role: str
    # 当前生效的班级（来自服务端会话），前端用它显示「我在哪个班」
    class_id: str | None
    classes: list[ClassBrief]


class MeOut(BaseModel):
    """ID-08 / ID-09：角色与班级全部来自服务端会话。"""

    id: str
    display_name: str
    role: str
    class_id: str | None
    classes: list[ClassBrief]
