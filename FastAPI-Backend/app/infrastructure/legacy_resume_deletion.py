"""Keep old PDF deletion compatible with new references and commit failures."""
import json
import re
from pathlib import Path
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.models.session_models import ResumeModel
from app.infrastructure.resume_template_store import safe_path

PENDING_ROOT = Path(__file__).resolve().parents[2] / "data/resume_delete_pending"


class LegacyResumeNotFound(LookupError):
    pass


class LegacyResumeInUse(ValueError):
    pass


def pending_directory(root):
    root = safe_path(root).resolve()
    if root == Path(root.anchor) or root in (PENDING_ROOT.parents[1], PENDING_ROOT.parents[2]):
        raise ValueError("dedicated deletion journal directory required")
    for public in (PENDING_ROOT.parent / "resumes", PENDING_ROOT.parent / "optimizations"):
        if root == public or public in root.parents or root in public.parents:
            raise ValueError("journal overlaps legacy files")
    root.mkdir(parents=True, exist_ok=True)
    return root


async def delete_legacy_resume(session, id_, user_id, filename, *, pending_root=PENDING_ROOT):
    record = (await session.execute(select(ResumeModel).where(
        ResumeModel.id == id_, ResumeModel.user_id == user_id, ResumeModel.filename == filename,
    ).with_for_update())).scalar_one_or_none()
    if record is None:
        raise LegacyResumeNotFound("resume unavailable")
    root = pending_directory(pending_root)
    path = safe_path(record.local_path) if record.local_path else None
    task = root / f"{uuid4().hex}.pending.json"
    with task.open("x", encoding="utf8") as stream:
        json.dump({"resume_id": record.id, "user_id": record.user_id,
            "local_path": str(path) if path else None}, stream)
    try:
        await session.delete(record)
        await session.commit()
    except IntegrityError as error:
        await session.rollback()
        if error.orig.args[0] == 1451:
            safe_path(task).unlink()
            raise LegacyResumeInUse("简历被经历来源引用，请先解除引用后再删除") from error
        # Other commit errors may be uncertain; retain PDF+journal for reconciliation.
        raise
    # Only delete PDF after the DB deletion succeeded. An unlink failure must not
    # turn a committed record deletion into an unrecoverable generic failure.
    try:
        if path:
            safe_path(path).unlink(missing_ok=True)
        safe_path(task).unlink()
    except OSError:
        return {"file_cleanup_pending": True, "cleanup_task_id": task.stem.split(".")[0]}
    return {"file_cleanup_pending": False}


async def retry_legacy_file_deletions(session, *, pending_root=PENDING_ROOT, limit=100):
    if session.in_transaction() or not 1 <= limit <= 1000:
        raise ValueError("fresh session and bounded limit required")
    completed, retained, failed = [], [], []
    root = pending_directory(pending_root)
    tasks = [p for p in sorted(root.iterdir()) if re.fullmatch(r"[0-9a-f]{32}\.pending\.json", p.name)][:limit]
    for task in tasks:
        safe_path(task)
        values = json.loads(task.read_text(encoding="utf8"))
        if type(values.get("resume_id")) is not int or values["resume_id"] <= 0:
            raise ValueError("invalid deletion journal")
        async with session.begin():
            exists = await session.scalar(select(ResumeModel.id).where(ResumeModel.id == values["resume_id"]).with_for_update())
            if exists is not None:
                retained.append(task.name)
                continue
            try:
                if values["local_path"]:
                    safe_path(values["local_path"]).unlink(missing_ok=True)
                safe_path(task).unlink()
                completed.append(task.name)
            except OSError:
                failed.append(task.name)
    return {"completed": completed, "retained": retained, "failed": failed}
