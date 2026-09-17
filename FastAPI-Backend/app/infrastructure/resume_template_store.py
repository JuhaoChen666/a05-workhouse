"""Import complete immutable bundles without executing any template code."""
import base64
import hashlib
import json
import os
import stat
from pathlib import Path, PurePosixPath
from sqlalchemy import select
from app.models.resume_latex_contracts import ResumeTemplateMetadata
from app.models.resume_storage_models import ResumeTemplateModel, utcnow

BUILTIN_ROOT = Path(__file__).resolve().parents[3] / "Springboot-backend/src/main/resources/templates/latex"


class TemplateVersionConflict(ValueError):
    pass


def safe_path(path):
    path = Path(os.path.abspath(path))
    for ancestor in (path, *path.parents):
        try:
            info = ancestor.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise ValueError("links and reparse points are forbidden")
    return path


def relative_name(name):
    if not name or "\\" in name or ":" in name or PurePosixPath(name).is_absolute() or any(p in ("", ".", "..") for p in name.split("/")):
        raise ValueError("unsafe relative resource name")
    return name


def read_bundle(directory):
    directory = safe_path(directory).resolve(strict=True)
    files, pending, total = {}, [directory], 0
    while pending:
        for path in sorted(pending.pop().iterdir()):
            safe_path(path)
            if path.is_dir():
                pending.append(path)
            elif path.is_file():
                if len(files) >= 256 or path.stat().st_size > 16 * 1024 * 1024:
                    raise ValueError("resource limits exceeded")
                content = path.read_bytes()
                total += len(content)
                if total > 32 * 1024 * 1024:
                    raise ValueError("bundle total size exceeded")
                files[relative_name(path.relative_to(directory).as_posix())] = {
                    "content": base64.b64encode(content).decode("ascii"), "encoding": "base64",
                    "sha256": hashlib.sha256(content).hexdigest(), "size_bytes": len(content),
                }
            else:
                raise ValueError("unsupported resource")
    if "template.json" not in files:
        raise ValueError("missing template.json")
    meta = ResumeTemplateMetadata.model_validate(json.loads(base64.b64decode(files["template.json"]["content"])))
    entry = relative_name(meta.entry_file)
    for name in (entry, meta.model_extra.get("cls_file")):
        if name and relative_name(name) not in files:
            raise ValueError("required resource missing")
    metadata = meta.model_dump(mode="json")
    digest = hashlib.sha256(json.dumps({"metadata": metadata, "resources": files}, sort_keys=True, ensure_ascii=False, allow_nan=False).encode("utf8")).hexdigest()
    return dict(id=meta.id, version=meta.version, name=meta.name, metadata_json=metadata,
        supported_sections=meta.supported_sections, supported_pages=meta.recommended_pages,
        supported_languages=meta.supported_languages, entry_file=entry,
        main_source=base64.b64decode(files[entry]["content"]).decode("utf8"), resources=files, content_digest=digest)


async def initialize_templates(session, root=BUILTIN_ROOT):
    if not session.in_transaction():
        raise RuntimeError("caller transaction required")
    root = safe_path(root).resolve(strict=True)
    bundles, identities = [], set()
    for path in sorted(root.iterdir()):
        safe_path(path)
        if not path.is_dir():
            continue
        values = read_bundle(path)
        identity = values["id"], values["version"]
        if identity in identities:
            raise TemplateVersionConflict("duplicate bundle identity")
        identities.add(identity)
        bundles.append(values)
    if not bundles:
        raise ValueError("no bundles found")
    inserted = 0
    for values in bundles:
        existing = (await session.execute(select(ResumeTemplateModel).where(
            ResumeTemplateModel.id == values["id"], ResumeTemplateModel.version == values["version"]
        ).with_for_update())).scalar_one_or_none()
        if existing:
            if any(getattr(existing, k) != v for k, v in values.items()):
                raise TemplateVersionConflict("immutable version content differs")
        else:
            session.add(ResumeTemplateModel(**values, validation_status="UNVALIDATED", is_enabled=False,
                validation_details={}, created_at=utcnow()))
            inserted += 1
    await session.flush()
    return inserted


async def main():
    from sqlalchemy.engine import make_url
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    url = os.environ.get("RESUME_DATABASE_URL")
    if not url or make_url(url).drivername != "mysql+aiomysql":
        raise RuntimeError("explicit RESUME_DATABASE_URL required")
    engine = create_async_engine(url)
    try:
        async with async_sessionmaker(engine)() as session, session.begin():
            count = await initialize_templates(session)
        print(f"Initialized {count} versions, UNVALIDATED and disabled")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
