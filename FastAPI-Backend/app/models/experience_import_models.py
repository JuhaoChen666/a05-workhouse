"""P2 models share the existing SQLAlchemy Base."""
from app.models.session_models import Base
from app.models import resume_storage_models  # Register referenced P1 tables.
from app.models.experience_import_schema import define_import_tables

_tables = define_import_tables(Base.metadata)


class ExperienceImportBatch(Base):
    __table__ = _tables[0]


class ExperienceImportDraft(Base):
    __table__ = _tables[1]
