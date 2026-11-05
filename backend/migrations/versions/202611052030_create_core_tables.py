"""create core tables of lesson 3/4

第 3 课五张表（classes / users / auth_sessions / materials / chunks）+ memberships + login_attempts。
回滚动作：按外键逆序 drop 全部本迁移创建的表。

Revision ID: 202611052030
Revises:
Create Date: 2026-11-05 20:30:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "202611052030"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=26), primary_key=True),
        sa.Column("email", sa.String(length=160), nullable=False),
        sa.Column("display_name", sa.String(length=60), nullable=False),
        sa.Column("password_hash", sa.String(length=72), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "classes",
        sa.Column("id", sa.String(length=26), primary_key=True),
        sa.Column("name", sa.String(length=40), nullable=False),
        sa.Column("join_code", sa.String(length=8), nullable=False),
        sa.Column(
            "owner_id",
            sa.String(length=26),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_classes_join_code", "classes", ["join_code"], unique=True)

    op.create_table(
        "memberships",
        sa.Column("id", sa.String(length=26), primary_key=True),
        sa.Column(
            "class_id",
            sa.String(length=26),
            sa.ForeignKey("classes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.String(length=26),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(length=10), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("class_id", "user_id", name="uq_memberships_class_user"),
        sa.CheckConstraint("role IN ('teacher', 'student')", name="ck_memberships_role"),
    )
    op.create_index("ix_memberships_class_id", "memberships", ["class_id"])
    op.create_index("ix_memberships_user_id", "memberships", ["user_id"])

    op.create_table(
        "auth_sessions",
        sa.Column("id", sa.String(length=26), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(length=26),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "class_id",
            sa.String(length=26),
            sa.ForeignKey("classes.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ip", sa.String(length=45), nullable=False, server_default=""),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_auth_sessions_token_hash", "auth_sessions", ["token_hash"], unique=True)
    op.create_index("ix_auth_sessions_user_id", "auth_sessions", ["user_id"])

    op.create_table(
        "login_attempts",
        sa.Column("id", sa.String(length=26), primary_key=True),
        sa.Column("email", sa.String(length=160), nullable=False),
        sa.Column("ip", sa.String(length=45), nullable=False, server_default=""),
        sa.Column("fail_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("email", "ip", name="uq_login_attempts_email_ip"),
    )

    op.create_table(
        "materials",
        sa.Column("id", sa.String(length=26), primary_key=True),
        sa.Column(
            "class_id",
            sa.String(length=26),
            sa.ForeignKey("classes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("original_filename", sa.String(length=200), nullable=False),
        sa.Column("stored_filename", sa.String(length=80), nullable=False),
        sa.Column("mime", sa.String(length=80), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(length=12), nullable=False, server_default="pending"),
        sa.Column("failure_reason", sa.String(length=200), nullable=True),
        sa.Column("chunk_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "uploaded_by",
            sa.String(length=26),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint("size_bytes > 0", name="ck_materials_size_positive"),
        sa.CheckConstraint(
            "status IN ('pending', 'processing', 'ready', 'failed')", name="ck_materials_status"
        ),
    )
    op.create_index(
        "ix_materials_class_created", "materials", ["class_id", "created_at", "id"]
    )
    op.create_index("ix_materials_class_status", "materials", ["class_id", "status"])

    op.create_table(
        "chunks",
        sa.Column("id", sa.String(length=26), primary_key=True),
        sa.Column(
            "material_id",
            sa.String(length=26),
            sa.ForeignKey("materials.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("class_id", sa.String(length=26), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("char_count", sa.Integer(), nullable=False),
        sa.Column("char_start", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("char_end", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("vector_id", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("material_id", "chunk_index", name="uq_chunks_material_index"),
        sa.CheckConstraint("chunk_index >= 0", name="ck_chunks_index_non_negative"),
        sa.CheckConstraint("char_start >= 0", name="ck_chunks_char_start"),
    )
    op.create_index("ix_chunks_material_id", "chunks", ["material_id"])
    op.create_index("ix_chunks_class", "chunks", ["class_id"])


def downgrade() -> None:
    op.drop_index("ix_chunks_class", table_name="chunks")
    op.drop_index("ix_chunks_material_id", table_name="chunks")
    op.drop_table("chunks")
    op.drop_index("ix_materials_class_status", table_name="materials")
    op.drop_index("ix_materials_class_created", table_name="materials")
    op.drop_table("materials")
    op.drop_table("login_attempts")
    op.drop_index("ix_auth_sessions_user_id", table_name="auth_sessions")
    op.drop_index("ix_auth_sessions_token_hash", table_name="auth_sessions")
    op.drop_table("auth_sessions")
    op.drop_index("ix_memberships_user_id", table_name="memberships")
    op.drop_index("ix_memberships_class_id", table_name="memberships")
    op.drop_table("memberships")
    op.drop_index("ix_classes_join_code", table_name="classes")
    op.drop_table("classes")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
