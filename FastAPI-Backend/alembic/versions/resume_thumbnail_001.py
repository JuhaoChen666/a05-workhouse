"""Persist derived first-page resume previews without changing frozen documents."""
import sqlalchemy as sa
from sqlalchemy.dialects.mysql import DATETIME
from alembic import op, context

revision = "resume_thumbnail_001"
down_revision = "resume_review_002"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "resume_thumbnails",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("source_kind", sa.String(length=16), nullable=False),
        sa.Column("source_id", sa.String(length=36, collation="utf8mb4_bin"), nullable=False),
        sa.Column("source_sha256", sa.String(length=64), nullable=False),
        sa.Column("asset", sa.JSON(none_as_null=True), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("available_at", DATETIME(fsp=6), nullable=False),
        sa.Column("created_at", DATETIME(fsp=6), nullable=False),
        sa.Column("updated_at", DATETIME(fsp=6), nullable=False),
        sa.CheckConstraint("user_id > 0 AND source_kind IN ('uploaded','generated')", name="ck_thumbnail_source"),
        sa.CheckConstraint("status IN ('PENDING','PROCESSING','READY','FAILED') AND attempt_count BETWEEN 0 AND 3", name="ck_thumbnail_status"),
        sa.CheckConstraint("asset IS NULL OR JSON_TYPE(asset) = 'OBJECT'", name="ck_thumbnail_asset_object"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "source_kind", "source_id", name="uq_thumbnail_source"),
        mysql_engine="InnoDB", mysql_charset="utf8mb4", mysql_collate="utf8mb4_unicode_ci",
    )
    op.create_index("ix_thumbnail_queue", "resume_thumbnails", ["status", "available_at", "updated_at"])


def downgrade():
    if context.is_offline_mode():
        raise RuntimeError("Thumbnail downgrade needs an online empty-table preflight")
    bind = op.get_bind()
    if bind.execute(sa.text("SELECT 1 FROM resume_thumbnails LIMIT 1")).first():
        raise RuntimeError("Thumbnail tasks or assets exist; retain the additive migration during application rollback")
    op.drop_index("ix_thumbnail_queue", table_name="resume_thumbnails")
    op.drop_table("resume_thumbnails")
