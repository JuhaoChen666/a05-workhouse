"""Reviewable tailoring and recoverable compile capacity; Refs #1."""
from alembic import op, context
import sqlalchemy as sa
from sqlalchemy.dialects.mysql import DATETIME

revision = "resume_review_002"
down_revision = "resume_runtime_001"
branch_labels = depends_on = None


def upgrade():
    for name in ("review_plan", "review_decision"):
        op.add_column("resume_generation_jobs", sa.Column(name, sa.JSON(none_as_null=True)))
    op.drop_constraint("ck_job_status", "resume_generation_jobs", type_="check")
    op.create_check_constraint("ck_job_status", "resume_generation_jobs", "status IN ('PENDING','PROCESSING','WAITING_REVIEW','COMPILED','FAILED')")
    identity = lambda: sa.String(36, collation="utf8mb4_bin")
    op.create_table("resume_execution_slots", sa.Column("slot", sa.Integer, primary_key=True, autoincrement=False),
        sa.Column("token", identity(), unique=True), sa.Column("job_id", identity(), sa.ForeignKey("resume_generation_jobs.id")),
        sa.Column("host_key", sa.String(64)), sa.Column("task_id", sa.String(32)), sa.Column("container_name", sa.String(100)), sa.Column("work_dir", sa.String(1024)),
        sa.Column("worker_pid", sa.Integer), sa.Column("worker_identity", sa.String(100)),
        sa.Column("state", sa.String(32), nullable=False), sa.Column("updated_at", DATETIME(fsp=6), nullable=False),
        sa.CheckConstraint("state IN ('FREE','ACTIVE','CLEANUP_REQUIRED')", name="ck_execution_state"),
        mysql_engine="InnoDB", mysql_charset="utf8mb4", mysql_collate="utf8mb4_unicode_ci")


def downgrade():
    if context.is_offline_mode():
        raise RuntimeError("online review/resource preflight required")
    db = op.get_bind()
    if db.execute(sa.text("SELECT 1 FROM resume_generation_jobs WHERE review_plan IS NOT NULL OR review_decision IS NOT NULL OR status='WAITING_REVIEW' LIMIT 1")).first() or db.execute(sa.text("SELECT 1 FROM resume_execution_slots WHERE state <> 'FREE' LIMIT 1")).first():
        raise RuntimeError("review or execution resources exist; retain additive migration")
    op.drop_table("resume_execution_slots")
    op.drop_constraint("ck_job_status", "resume_generation_jobs", type_="check")
    op.create_check_constraint("ck_job_status", "resume_generation_jobs", "status IN ('PENDING','PROCESSING','COMPILED','FAILED')")
    op.drop_column("resume_generation_jobs", "review_decision")
    op.drop_column("resume_generation_jobs", "review_plan")
