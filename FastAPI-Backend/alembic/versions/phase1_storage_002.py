"""Require complete latex outputs; reset legacy purge intent markers. Refs #1."""
from alembic import op, context
import sqlalchemy as sa

revision = "phase1_storage_002"
down_revision = "phase1_storage_001"
branch_labels = None
depends_on = None


def upgrade():
    if not context.is_offline_mode():
        count = op.get_bind().scalar(sa.text(
            "SELECT COUNT(*) FROM resume_documents WHERE format='latex' AND (pdf_asset IS NULL OR latex_asset IS NULL)"
        ))
        if count:
            raise RuntimeError(f"{count} incomplete latex documents; reconcile real outputs before upgrade, no records changed")
    op.create_check_constraint("ck_document_outputs", "resume_documents",
        "format <> 'latex' OR (pdf_asset IS NOT NULL AND latex_asset IS NOT NULL)")
    # 001 wrote these before unlink. Recheck tombstones once under new semantics,
    # including retries where 001 committed intent but file deletion failed.
    op.execute(sa.text("UPDATE resume_documents SET files_purged_at=NULL WHERE files_purged_at IS NOT NULL"))


def downgrade():
    op.drop_constraint("ck_document_outputs", "resume_documents", type_="check")
