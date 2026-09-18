"""P2 persistence; this mutable definition is not imported by migrations."""
import sqlalchemy as sa
from sqlalchemy.dialects.mysql import DATETIME

TABLE_NAMES = ("experience_import_batches", "experience_import_drafts")


def define_import_tables(metadata, legacy_resume_type=None):
    identity = sa.String(36, collation="utf8mb4_bin")
    options = dict(mysql_engine="InnoDB", mysql_charset="utf8mb4", mysql_collate="utf8mb4_unicode_ci")
    batch = sa.Table(TABLE_NAMES[0], metadata,
        sa.Column("id", identity, primary_key=True), sa.Column("user_id", sa.Integer, nullable=False),
        sa.Column("source_resume_id", legacy_resume_type or sa.BigInteger,
                  sa.ForeignKey("resumes.id", ondelete="RESTRICT")),
        sa.Column("source_asset", sa.JSON(none_as_null=True)),
        sa.Column("source_optimization_id", sa.String(36)),
        sa.Column("retry_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("ai_attempt_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("ai_failure_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("pages", sa.JSON(none_as_null=True), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("error", sa.JSON(none_as_null=True)),
        sa.Column("confirmation_digest", sa.String(64)),
        sa.Column("confirmation_result", sa.JSON(none_as_null=True)),
        sa.Column("created_at", DATETIME(fsp=6), nullable=False),
        sa.Column("updated_at", DATETIME(fsp=6), nullable=False),
        sa.Column("expires_at", DATETIME(fsp=6), nullable=False),
        sa.Column("files_purged_at", DATETIME(fsp=6)),
        sa.UniqueConstraint("id", "user_id", name="uq_import_batch_owner"),
        sa.CheckConstraint("user_id > 0 AND expires_at >= created_at", name="ck_import_batch_ranges"),
        sa.CheckConstraint("status IN ('PROCESSING','READY','FAILED','CONFIRMED','CANCELLED','EXPIRED')", name="ck_import_batch_status"),
        sa.CheckConstraint("JSON_TYPE(pages) = 'ARRAY'", name="ck_import_batch_pages"),
        sa.CheckConstraint("source_asset IS NULL OR JSON_TYPE(source_asset) = 'OBJECT'", name="ck_import_batch_asset"),
        sa.CheckConstraint("error IS NULL OR JSON_TYPE(error) = 'OBJECT'", name="ck_import_batch_error"),
        sa.CheckConstraint("status <> 'CONFIRMED' OR (confirmation_digest IS NOT NULL AND confirmation_result IS NOT NULL)", name="ck_import_batch_receipt"),
        sa.CheckConstraint("confirmation_result IS NULL OR JSON_TYPE(confirmation_result) = 'OBJECT'", name="ck_import_batch_result"),
        sa.Index("ix_import_owner_created", "user_id", "created_at"),
        sa.Index("ix_import_cleanup", "user_id", "files_purged_at", "status", "expires_at"), **options)
    draft = sa.Table(TABLE_NAMES[1], metadata,
        sa.Column("id", identity, primary_key=True), sa.Column("batch_id", identity, nullable=False),
        sa.Column("user_id", sa.Integer, nullable=False),
        sa.Column("content", sa.JSON(none_as_null=True), nullable=False),
        sa.Column("issues", sa.JSON(none_as_null=True), nullable=False),
        sa.Column("locator", sa.JSON(none_as_null=True), nullable=False),
        sa.Column("revision", sa.Integer, nullable=False), sa.Column("sort_order", sa.Integer, nullable=False),
        sa.Column("created_at", DATETIME(fsp=6), nullable=False),
        sa.Column("updated_at", DATETIME(fsp=6), nullable=False),
        sa.ForeignKeyConstraint(["batch_id", "user_id"], ["experience_import_batches.id", "experience_import_batches.user_id"], ondelete="CASCADE"),
        sa.CheckConstraint("user_id > 0 AND revision > 0 AND sort_order >= 0", name="ck_import_draft_ranges"),
        sa.CheckConstraint("JSON_TYPE(content) = 'OBJECT' AND JSON_TYPE(locator) = 'OBJECT' AND JSON_TYPE(issues) = 'ARRAY'", name="ck_import_draft_json"),
        sa.Index("ix_import_draft_owner_batch", "user_id", "batch_id", "sort_order", "id"), **options)
    return batch, draft
