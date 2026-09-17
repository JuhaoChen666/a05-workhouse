# Phase 1 storage handoff — Refs #1

## Fresh baseline and scope

Project: `H:\Code\program\2026外包\a05_plus`.
Branch: `feat/resume-phase1-storage-v2`, created 2026-09-17T19:10:03+08:00.
Start exactly equals fetched `origin/master` at `b7bf53ff27748db720b28c40c0c6409e1ef33d5c`.
This master already contains merged P0 and all six bundles. Original P1 branch is retained but abandoned;
new implementation is independently written, with no copied old source, cherry-pick or branch merge.
No push, PR, production migration or deployment. No merges before user review.

Only Phase 1 storage: four tables, migration, transactional internal repository, frozen inputs/template resources,
private files, retention cleanup and tests. No HTTP CRUD/UI/PDF parsing/AI/rendering/compiler/authentication rewrite.
Inherited six `.tex.j2`/`.cls`/`template.json` files and legacy routes/models remain unchanged.
Necessary P0 input corrections and rationale are in [storage contracts](resume_phase1_storage_contracts.md).

## Files and tables

| Entry | Purpose |
| --- | --- |
| FastAPI-Backend/app/models/resume_latex_contracts.py | P0 input category/date/managed-field constraints and full template metadata |
| frontend/src/types/resumeLatexContracts.ts | Unused wire types aligned to snake_case, server response separate |
| FastAPI-Backend/app/models/resume_storage_contracts.py | Five-type adapter, pinned version, file/document inputs, trusted owner validation |
| FastAPI-Backend/app/models/resume_storage_schema.py | Four table definitions |
| FastAPI-Backend/app/models/resume_storage_models.py | Existing Base mappings and immutable historical field guards |
| FastAPI-Backend/alembic/ | Isolated async configuration and frozen initial migration |
| FastAPI-Backend/app/infrastructure/mapper/resume_storage_mapper.py | Owner-scoped experiences, jobs, documents and old Markdown access |
| FastAPI-Backend/app/infrastructure/resume_template_store.py | Exact full-resource snapshot, immutable initialization and explicit-env CLI |
| FastAPI-Backend/app/infrastructure/private_resume_assets.py | Private files, compensation, advisory lock, dry-run cleanup |
| FastAPI-Backend/tests/, requirements-storage-test.txt | Fresh independent boundary/MySQL tests and pinned storage-only dependencies |

Reuse `session_models.Base`; InnoDB, utf8mb4, MySQL JSON and UTC-naive DATETIME(6). Nullable JSON uses SQL NULL,
not JSON null, so JSON shape CHECKs remain enforced. UUID/template identities use binary collation.

| Table | Contents | Indexes/constraints |
| --- | --- | --- |
| experience_items | owner, five types/common attributes, tags, dates, revision, sorting/archive, provenance/locator, timestamps | owner+archive+type+order+id; owner+updated; positive owner/revision/order; type/source and JSON checks |
| resume_templates | composite (id,version), full metadata/resources/base64/sha/size, main source/digest, modules/pages/languages, validation/enable | available state index; enabled requires VALIDATED; object/array JSON checks |
| resume_generation_jobs | owner, pinned template, actual JD/full experience revision/content/personal/options/template snapshots, status/stage/progress/error/traces/retry/time | owner+created; status+updated; unique(id,owner); status/ranges/language/JSON checks |
| resume_documents | owner, name/format, job/full snapshot, file metadata, copy source, optional legacy Markdown/optimization, soft-delete/retention/purge times | owner+deleted+created; purge markers/deadline; unique(id,owner); format/job/retention/JSON checks |

RESTRICT FKs: experience.source_resume_id→legacy resumes.id; job.template identity→template;
document(job_id,owner)→job(id,owner); document(copy_id,owner)→document(id,owner);
document.legacy_optimization_id→legacy optimization key. Repository additionally validates old-record owner.
No assumed Spring user/JD FK. No old ALTER/DROP, data conversion or application-start create_all.
Initial migration reflects actual legacy BIGINT signedness and VARCHAR(36) collation before new business DDL.

## Migration

Run in `FastAPI-Backend`, with credentials provided securely by local environment:
`RESUME_DATABASE_URL=mysql+aiomysql://...` must explicitly name an authorized database.
No .env/application.properties/legacy default fallback; never include credentials in logs/commits.

```powershell
python -m alembic -c alembic.ini upgrade head --sql
python -m alembic -c alembic.ini upgrade head
python -m alembic -c alembic.ini current
```

Revision `phase1_storage_001`, separate version table `resume_phase1_alembic_version`.
Upgrade creates only four business tables plus version table. Autogenerate filters to these four tables.
Revision embeds a frozen snapshot of the newly authored schema, never imports mutable application ORM definitions.
Online preflight requires MySQL 8.0.16+ with enforced CHECK and compatible existing legacy primary keys/owner.
Offline SQL cannot reflect real legacy definitions; manually verify signedness/collation before using it.

```powershell
python -m alembic -c alembic.ini downgrade phase1_storage_001:base --sql
# Destructive: only execute against disposable test DB, or after separately authorized verified backup:
python -m alembic -c alembic.ini downgrade base
```

Downgrade deletes all data in the four new tables. It never deletes old tables/files. MySQL DDL implicitly commits;
partial upgrade failure needs state inspection/manual recovery, not automatic DROP/retry. No production rollback executed
and no backup made or asserted. Old P1 databases are not an upgrade target for this fresh initial migration.

## Repository integration

Trusted owner must originate from verified server identity. Spring uses authenticated SecurityContext;
future FastAPI routes need verified authentication or a trusted service identity adapter, never body/query/header user_id.
Cross-owner and missing assets produce the same `AssetNotFound`. Templates are system resources, with future privileged
validation/management separate from user assets; initialization always disabled/unvalidated.

```python
async with factory() as session, session.begin():
    storage = ResumeStorageMapper(session, authenticated_user.id)
    item = await storage.create_experience({
        "type": "SKILL", "title": "Backend", "category": "Backend", "skills": ["Python"]
    })
```

Repository uses caller AsyncSession and flush only, never own commits. Propagate failures to transaction boundary.
Update complete validated input with expected_revision; atomic owner+id+revision UPDATE increments revision.
Archive also increments revision; category is immutable. Future PATCH must merge old values before full validation.
Provenance is optional tracing, not proof; source legacy resume owner is checked.

`create_job` pins VALIDATED/enabled template/version and validates declared pages/language/avatar support.
Null selected IDs freezes all active user experiences, [] selects none. No selection AI runs.
JOB_ID requires trusted `resolved_job={"id": ..., "jobContent": ...}` from actual Spring Job, not positions classification.
Deep-copy JD/full experience id+revision/content, personal information, request options, full template resources at creation.
PENDING→PROCESSING→COMPILED/FAILED; PENDING may also fail. Compiled requires100 progress; failed requires error object.
Retry FAILED→PENDING increments retry count and preserves immutable inputs while rechecking referenced files.
There is no generation executor or real compiler validation in fixtures.

COMPILED same-owner job can create latex document; rename/copy/list/soft delete are internal APIs.
`read_legacy_markdown` owner-scopes old optimization; `save_legacy_markdown` creates one explicit compatible document.
No bulk conversion/old optimization writes. Default retention30 days; repeated deletion keeps initial deadline.
Historical identity/template content/snapshots/files are guarded against ORM replacement; direct SQL can bypass ORM guards.
Do not expose low-level row helpers/arbitrary SQL as routes. Mutable JSON in-place editing is not a persistence interface.

## Private assets and retention

Default `FastAPI-Backend/data/private_resume_assets` is Git-ignored and has no StaticFiles mount.
Root cannot overlap real old `data/resumes` or `data/optimizations`, backend/project/drive root. Check ancestors with lstat;
symlinks/junctions/reparse points are forbidden at import and each filesystem operation.
File key owner/randomUUID.pdf|tex|bin; metadata key/sha256/size/media only, no client absolute path accepted.
Exclusive create prevents overwrite; integrity/owner/size/media checked on read/attach/delete.

```python
store = PrivateAssets()
async with factory() as session:
    async with private_asset_transaction(session, store, authenticated_user.id) as files:
        storage = ResumeStorageMapper(session, authenticated_user.id)
        pdf = files.write(compiled_pdf_bytes, "pdf")
        source = files.write(rendered_latex_bytes, "tex")
        doc = await storage.create_document(
            {"name": "Role resume", "generation_job_id": compiled_job_id},
            pdf_asset=pdf, latex_asset=source,
        )
```

Do not nest session.begin(); coordinator owns transaction. Future stages provide compiled bytes/status.
Any structured FileAsset in source locator/job inputs/traces/documents/copies must be verified under this boundary.
MySQL GET_LOCK on canonical private root uses a separate AsyncEngine connection and persists through commit/unlink.
Pool needs at least two connections, and all instances must agree on same canonical root.
Confirmed body rollback compensates only fresh files; old files never replaced. Commit/rollback uncertainty retains files
and private `.pending` metadata for manual DB-reference reconciliation. Crash before manifest can leave unknown orphan;
unknown files are deliberately retained. No automatic orphan recovery or public download/delete route.

```python
# Fresh session; dry-run is default, bounded selection is owner-scoped:
report = await cleanup_documents(session, store, authenticated_user.id)
# Authorized retention-maintenance entry only:
report = await cleanup_documents(session, store, authenticated_user.id, dry_run=False)
```

Cleaner selects expired tombstones, verifies candidate output paths/digests, protects living/unexpired documents including
copies and their snapshots plus PENDING/PROCESSING job input/traces. It does not discover orphan files by directory scanning.
Only expired document PDF/LaTeX outputs are candidates; input-only avatars are not cleanup targets.
Commit purge markers before unlink under same mutex. Failed unlink is retryable using retained metadata/tombstones.
Do not remove old files, unknown files or uncertain `.pending` references. No timer/production cleanup is started.

## Validation and remaining scope

Final fresh run on MySQL9.6.0: **60 passed, 0 skipped, 9.06s**, including14 real database integration scenarios.
Verified five category persistence/owner reads+writes, CAS revisions, multi-table rollback, actual JD selection/frozen inputs,
six-template initialization/idempotency/content+duplicate conflicts, state/retry rules, JSON_EXTRACT/3819 CHECK/FK enforcement,
ORM immutable replacements, legacy Markdown/soft delete, fresh-file rollback and commit/copy/shared retention/dry run,
active job and two-session stale-trace file protection, snapshot asset transaction boundary, uncertain commit preservation,
online upgrade→downgrade→upgrade retaining old sentinel schemas/data, file paths/integrity/collision/links/size limits.
Offline MySQL upgrade/downgrade SQL, targeted Python compileall and git diff --check passed.
No previous branch's tests/results were counted. Tests always CREATE a random
`resume_p1_restart_test_<16hex>` schema independently of supplied URL database; teardown DROP only that self-created name.
Existing DB is never migrated/cleared. Fixtures prepare legacy sentinel rows and intentionally UNSIGNED BIGINT/unicode_ci FK types.
Credentials use masked interactive input and transient process environment only, no secret files.

Install storage-only wheels into project venv, then run from root with explicit RESUME_TEST_MYSQL_URL:

```powershell
$env:PYTHONPATH = Join-Path (Get-Location) 'FastAPI-Backend'
.\.venv\Scripts\python.exe -m pytest FastAPI-Backend/tests --basetemp=.phase1-local/pytest-restart -q
```

Basetemp is this task's generated dedicated directory; pytest recreates it, never point to user data/project root.
Full frontend/TypeScript build, legacy AI end-to-end, actual template compilation are not run; no compatibility claim for those.
Deploy-time MySQL version/legacy schema need verification. Future Phase 2 routes provide verified identity,
Phase 3 privileged compiler validation controls availability, Phase 4 JD adapter/generator uses frozen inputs,
Phase 6 downloads check owner then private asset integrity. User review required before branch integration.

## Local commits

| Commit | Content |
| --- | --- |
| d730649 | Fresh master baseline and storage contracts |
| 5f08473 | Four-table definitions/mappings and owner associations |
| acce7f6 | SQL NULL JSON semantics and UTC microseconds |
| 100137b | Frozen independent four-table migration |
| 90b1b76 | Six-template initialization and private asset retention |
| d0849d2 | Owner repository and immutable job/document snapshots |
| 9fdc8d2 | Fresh real MySQL/boundary regression suite |

Final docs commit is the following local `docs(resume)` entry in the log.
Use `git log --reverse b7bf53ff27748db720b28c40c0c6409e1ef33d5c..HEAD --oneline` for fresh local commits.
No old P1 commits are ancestors of this branch. Every new commit references Issue1, never closes Phase0–7.
