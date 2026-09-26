"""Durable capacity remains occupied until the previous execution is cleaned."""
import sqlalchemy as sa
from sqlalchemy.dialects.mysql import DATETIME
from app.models.session_models import Base
from app.models.resume_storage_models import ResumeGenerationJobModel  # registers FK target


class ResumeExecutionSlot(Base):
    __tablename__ = "resume_execution_slots"
    slot = sa.Column(sa.Integer, primary_key=True, autoincrement=False)
    token = sa.Column(sa.String(36, collation="utf8mb4_bin"), unique=True)
    job_id = sa.Column(sa.String(36, collation="utf8mb4_bin"), sa.ForeignKey("resume_generation_jobs.id"))
    host_key = sa.Column(sa.String(64))
    task_id = sa.Column(sa.String(32))
    container_name = sa.Column(sa.String(100))
    worker_pid = sa.Column(sa.Integer)
    worker_identity = sa.Column(sa.String(100))
    work_dir = sa.Column(sa.String(1024))
    state = sa.Column(sa.String(32), nullable=False)
    updated_at = sa.Column(DATETIME(fsp=6), nullable=False)
    __table_args__ = (sa.CheckConstraint("state IN ('FREE','ACTIVE','CLEANUP_REQUIRED')", name="ck_execution_state"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"})
