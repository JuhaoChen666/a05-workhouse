"""Four storage tables; legacy tables remain under their existing owners."""
import sqlalchemy as sa
from sqlalchemy.dialects.mysql import DATETIME

TABLE_NAMES = ("experience_items", "resume_templates", "resume_generation_jobs", "resume_documents")


def define_tables(metadata, legacy_resume_type=None, legacy_optimization_type=None):
    identity = lambda n=36: sa.String(n, collation="utf8mb4_bin")
    column = sa.Column
    options = dict(mysql_engine="InnoDB", mysql_charset="utf8mb4", mysql_collate="utf8mb4_unicode_ci")
    def owner():
        return column("user_id", sa.Integer, nullable=False)
    def json_column(name, nullable=False):
        return column(name, sa.JSON(none_as_null=True), nullable=nullable)
    def object_check(name):
        return sa.CheckConstraint(f"JSON_TYPE({name}) = 'OBJECT'", name=f"ck_{name}_object")
    def array_check(name):
        return sa.CheckConstraint(f"JSON_TYPE({name}) = 'ARRAY'", name=f"ck_{name}_array")
    def created():
        return column("created_at", DATETIME(fsp=6), nullable=False)
    experience = sa.Table("experience_items", metadata,
        column("id", identity(), primary_key=True), owner(), column("type", sa.String(32), nullable=False),
        column("title", sa.String(200), nullable=False), column("start_date", sa.String(7)), column("end_date", sa.String(7)),
        json_column("tags"), json_column("attributes"), column("is_archived", sa.Boolean, nullable=False),
        column("sort_order", sa.Integer, nullable=False), column("revision", sa.Integer, nullable=False),
        column("source_type", sa.String(16), nullable=False),
        column("source_resume_id", legacy_resume_type or sa.BigInteger, sa.ForeignKey("resumes.id", ondelete="RESTRICT")),
        json_column("source_locator"), created(), column("updated_at", DATETIME(fsp=6), nullable=False),
        sa.CheckConstraint("user_id > 0 AND revision > 0 AND sort_order >= 0", name="ck_experience_ranges"),
        sa.CheckConstraint("type IN ('CERTIFICATE','COMPETITION_AWARD','PROJECT','WORK','SKILL')", name="ck_experience_type"),
        sa.CheckConstraint("source_type IN ('MANUAL','PDF_IMPORT','MARKDOWN_IMPORT')", name="ck_experience_source"),
        array_check("tags"), object_check("attributes"), object_check("source_locator"),
        sa.Index("ix_experience_owner_list", "user_id", "is_archived", "type", "sort_order", "id"),
        sa.Index("ix_experience_owner_updated", "user_id", "updated_at"), **options)
    template = sa.Table("resume_templates", metadata,
        column("id", identity(100), primary_key=True), column("version", identity(32), primary_key=True),
        column("name", sa.String(200), nullable=False), json_column("metadata_json"),
        json_column("supported_sections"), json_column("supported_pages"), json_column("supported_languages"),
        column("entry_file", sa.String(255), nullable=False), column("main_source", sa.Text, nullable=False),
        json_column("resources"), column("content_digest", sa.String(64), nullable=False),
        column("validation_status", sa.String(16), nullable=False), column("is_enabled", sa.Boolean, nullable=False),
        json_column("validation_details"), created(),
        sa.CheckConstraint("validation_status IN ('UNVALIDATED','VALIDATED','INVALID')", name="ck_template_status"),
        sa.CheckConstraint("is_enabled = 0 OR validation_status = 'VALIDATED'", name="ck_template_enabled"),
        object_check("metadata_json"), object_check("resources"), object_check("validation_details"),
        array_check("supported_sections"), array_check("supported_pages"), array_check("supported_languages"),
        sa.Index("ix_template_available", "is_enabled", "validation_status"), **options)
    job = sa.Table("resume_generation_jobs", metadata,
        column("id", identity(), primary_key=True), owner(),
        column("template_id", identity(100), nullable=False), column("template_version", identity(32), nullable=False),
        column("jd_source_type", sa.String(16), nullable=False), column("job_id", sa.String(64)),
        json_column("jd_snapshot"), json_column("experience_snapshot"), json_column("personal_info_snapshot"),
        json_column("template_snapshot"), json_column("options_snapshot"),
        column("target_pages", sa.Integer, nullable=False), column("language", sa.String(8), nullable=False),
        column("status", sa.String(16), nullable=False), column("stage", sa.String(100), nullable=False),
        column("progress_percentage", sa.Integer, nullable=False), json_column("error", nullable=True),
        json_column("traces"), column("retry_count", sa.Integer, nullable=False),
        json_column("result_metadata", nullable=True), column("run_token", identity()),
        json_column("review_plan", nullable=True), json_column("review_decision", nullable=True),
        created(), column("updated_at", DATETIME(fsp=6), nullable=False), column("started_at", DATETIME(fsp=6)), column("finished_at", DATETIME(fsp=6)),
        sa.UniqueConstraint("id", "user_id", name="uq_job_owner"),
        sa.ForeignKeyConstraint(["template_id", "template_version"], ["resume_templates.id", "resume_templates.version"], ondelete="RESTRICT"),
        sa.CheckConstraint("status IN ('PENDING','PROCESSING','WAITING_REVIEW','COMPILED','FAILED')", name="ck_job_status"),
        sa.CheckConstraint("user_id > 0 AND progress_percentage BETWEEN 0 AND 100 AND retry_count >= 0 AND target_pages IN (1,2)", name="ck_job_ranges"),
        sa.CheckConstraint("jd_source_type IN ('TEXT','JOB_ID') AND language IN ('zh','en')", name="ck_job_options"),
        *[object_check(n) for n in ("jd_snapshot", "personal_info_snapshot", "template_snapshot", "options_snapshot", "error")],
        array_check("experience_snapshot"), array_check("traces"),
        sa.Index("ix_job_owner_created", "user_id", "created_at"), sa.Index("ix_job_status_updated", "status", "updated_at"), **options)
    document = sa.Table("resume_documents", metadata,
        column("id", identity(), primary_key=True), owner(), column("name", sa.String(200), nullable=False),
        column("format", sa.String(16), nullable=False), column("generation_job_id", identity()),
        json_column("snapshot"), json_column("pdf_asset", nullable=True), json_column("latex_asset", nullable=True),
        column("markdown_content", sa.Text),
        column("legacy_optimization_id", legacy_optimization_type or sa.String(36), sa.ForeignKey("resume_optimizations.session_id", ondelete="RESTRICT")),
        column("copied_from_id", identity()), created(), column("updated_at", DATETIME(fsp=6), nullable=False),
        column("deleted_at", DATETIME(fsp=6)), column("purge_after", DATETIME(fsp=6)), column("files_purged_at", DATETIME(fsp=6)),
        sa.UniqueConstraint("id", "user_id", name="uq_document_owner"),
        sa.ForeignKeyConstraint(["generation_job_id", "user_id"], ["resume_generation_jobs.id", "resume_generation_jobs.user_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["copied_from_id", "user_id"], ["resume_documents.id", "resume_documents.user_id"], ondelete="RESTRICT"),
        sa.CheckConstraint("user_id > 0 AND format IN ('latex','markdown')", name="ck_document_format"),
        sa.CheckConstraint("format <> 'latex' OR generation_job_id IS NOT NULL", name="ck_document_job"),
        sa.CheckConstraint("format <> 'latex' OR (pdf_asset IS NOT NULL AND latex_asset IS NOT NULL)", name="ck_document_outputs"),
        sa.CheckConstraint("(deleted_at IS NULL AND purge_after IS NULL AND files_purged_at IS NULL) OR (deleted_at IS NOT NULL AND purge_after >= deleted_at)", name="ck_document_retention"),
        object_check("snapshot"), object_check("pdf_asset"), object_check("latex_asset"),
        sa.Index("ix_document_owner_list", "user_id", "deleted_at", "created_at"),
        sa.Index("ix_document_retention", "files_purged_at", "purge_after"), **options)
    return experience, template, job, document
