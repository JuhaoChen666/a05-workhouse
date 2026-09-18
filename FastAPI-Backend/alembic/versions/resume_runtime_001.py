"""Durable generation execution and observable results; Refs #1."""
import sqlalchemy as sa
from alembic import op, context

revision = "resume_runtime_001"
down_revision = "phase2_experience_001"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("resume_generation_jobs", sa.Column("run_token", sa.String(36, collation="utf8mb4_bin")))
    op.add_column("resume_generation_jobs", sa.Column("result_metadata", sa.JSON(none_as_null=True)))
    op.add_column("experience_import_batches", sa.Column("source_optimization_id", sa.String(36)))
    for name in ("retry_count", "ai_attempt_count", "ai_failure_count"):
        op.add_column("experience_import_batches", sa.Column(name, sa.Integer, nullable=False, server_default="0"))
    op.drop_constraint("ck_experience_source", "experience_items", type_="check")
    op.create_check_constraint("ck_experience_source", "experience_items", "source_type IN ('MANUAL','PDF_IMPORT','MARKDOWN_IMPORT')")


def downgrade():
    # Refuse destructive narrowing while historical Markdown provenance is in use.
    if context.is_offline_mode():
        raise RuntimeError("rollback requires online provenance preflight; prefer application-only rollback")
    if op.get_bind().execute(sa.text("SELECT 1 FROM experience_items WHERE source_type='MARKDOWN_IMPORT' LIMIT 1")).first() or op.get_bind().execute(sa.text("SELECT 1 FROM experience_import_batches WHERE source_optimization_id IS NOT NULL LIMIT 1")).first():
        raise RuntimeError("Markdown imports exist; keep the additive migration when rolling back application code")
    op.drop_constraint("ck_experience_source", "experience_items", type_="check")
    op.create_check_constraint("ck_experience_source", "experience_items", "source_type IN ('MANUAL','PDF_IMPORT')")
    op.drop_column("experience_import_batches", "source_optimization_id")
    for name in ("ai_failure_count", "ai_attempt_count", "retry_count"):
        op.drop_column("experience_import_batches", name)
    op.drop_column("resume_generation_jobs", "result_metadata")
    op.drop_column("resume_generation_jobs", "run_token")
