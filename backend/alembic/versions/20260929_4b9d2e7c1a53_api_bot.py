"""api del agente de voz: api_keys y bot_consultas_log

Revision ID: 4b9d2e7c1a53
Revises: 61c0d05ac8d9
Create Date: 2026-09-29 10:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "4b9d2e7c1a53"
down_revision: str | Sequence[str] | None = "61c0d05ac8d9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "api_keys",
        sa.Column("id", sa.SmallInteger(), autoincrement=True, nullable=False),
        sa.Column("nombre", sa.String(length=60), nullable=False),
        sa.Column("prefijo", sa.String(length=12), nullable=False),
        sa.Column("key_hash", sa.String(length=64), nullable=False),
        sa.Column("scopes", postgresql.ARRAY(sa.Text()), server_default=sa.text("'{bot:read}'"), nullable=False),
        sa.Column("activo", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("ultimo_uso_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("revocada_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_api_keys")),
        sa.UniqueConstraint("key_hash", name=op.f("uq_api_keys_key_hash")),
        sa.UniqueConstraint("nombre", name=op.f("uq_api_keys_nombre")),
    )
    op.create_table(
        "bot_consultas_log",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("api_key_id", sa.SmallInteger(), nullable=True),
        sa.Column("tool", sa.String(length=60), nullable=False),
        sa.Column("caller_id", sa.String(length=15), nullable=True),
        sa.Column("parametros", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("encontrado", sa.Boolean(), nullable=False),
        sa.Column("coincide_caller", sa.Boolean(), nullable=True),
        sa.Column("resultado", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("codigo_http", sa.SmallInteger(), nullable=False),
        sa.Column("latencia_ms", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["api_key_id"],
            ["api_keys.id"],
            name=op.f("fk_bot_consultas_log_api_key_id_api_keys"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_bot_consultas_log")),
    )
    op.create_index(
        "ix_bot_consultas_log_created_at",
        "bot_consultas_log",
        [sa.literal_column("created_at DESC")],
        unique=False,
    )
    op.create_index("ix_bot_consultas_log_tool_created_at", "bot_consultas_log", ["tool", "created_at"], unique=False)
    op.create_index("ix_bot_consultas_log_caller_id", "bot_consultas_log", ["caller_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_bot_consultas_log_caller_id", table_name="bot_consultas_log")
    op.drop_index("ix_bot_consultas_log_tool_created_at", table_name="bot_consultas_log")
    op.drop_index("ix_bot_consultas_log_created_at", table_name="bot_consultas_log")
    op.drop_table("bot_consultas_log")
    op.drop_table("api_keys")
