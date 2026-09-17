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
Inherited six `.tex.j2`/`.cls`/`template.json` files and legacy models remain unchanged.
Review fixes update the existing PDF delete route to preserve files on database errors and provide retryable file cleanup.
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
| FastAPI-Backend/app/infrastructure/legacy_resume_deletion.py | Database-first legacy delete and pending-file retry journal |
| FastAPI-Backend/tests/, requirements-storage-test.txt | Fresh independent boundary/MySQL tests and pinned storage-only dependencies |

Reuse `session_models.Base`; InnoDB, utf8mb4, MySQL JSON and UTC-naive DATETIME(6). Nullable JSON uses SQL NULL,
not JSON null, so JSON shape CHECKs remain enforced. UUID/template identities use binary collation.

| Table | Contents | Indexes/constraints |
| --- | --- | --- |
| experience_items | owner, five types/common attributes, tags, dates, revision, sorting/archive, provenance/locator, timestamps | owner+archive+type+order+id; owner+updated; positive owner/revision/order; type/source and JSON checks |
| resume_templates | composite (id,version), full metadata/resources/base64/sha/size, main source/digest, modules/pages/languages, validation/enable | available state index; enabled requires VALIDATED; object/array JSON checks |
| resume_generation_jobs | owner, pinned template, actual JD/full experience revision/content/personal/options/template snapshots, status/stage/progress/error/traces/retry/time | owner+created; status+updated; unique(id,owner); status/ranges/language/JSON checks |
| resume_documents | owner, name/format, job/full snapshot, file metadata, copy source, optional legacy Markdown/optimization, soft-delete/retention/purge times | owner+deleted+created; purge markers/deadline; unique(id,owner); format/job/retention/JSON checks; latex requires both outputs |

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

Current head is `phase1_storage_002`, separate version table `resume_phase1_alembic_version`.
001 creates only four business tables plus version table. Autogenerate filters to these four tables.
001 embeds a frozen schema snapshot, never imports mutable application ORM definitions; it remains unchanged by these fixes.
002 adds `ck_document_outputs` and resets existing purge markers once, because 001's cleaner recorded intent before unlink.
Its online preflight refuses to proceed when any existing latex document lacks a PDF or LaTeX asset. Reconcile such rows
using genuine outputs and a separately reviewed data repair before upgrading; no fake files or automatic record deletion.
Offline SQL cannot perform this preflight: check for these rows before executing it. 002 modifies only resume_documents.
Online preflight requires MySQL 8.0.16+ with enforced CHECK and compatible existing legacy primary keys/owner.
Offline SQL cannot reflect real legacy definitions; manually verify signedness/collation before using it.

```powershell
python -m alembic -c alembic.ini downgrade phase1_storage_002:base --sql
# Destructive: only execute against disposable test DB, or after separately authorized verified backup:
python -m alembic -c alembic.ini downgrade base
```

Downgrading 002 to 001 only removes its output CHECK; it does not restore previous purge marker values.
Downgrade to base deletes all data in the four new tables. It never deletes old tables/files. MySQL DDL implicitly commits;
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

COMPILED same-owner job can create latex document only with both verified PDF and LaTeX assets.
Create/rename/copy/save-legacy use the same trimmed, nonblank, at-most-200-character name contract.
Rename/copy/list/soft delete are internal APIs.
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
# Advance even when a protected tombstone occupies the first batch:
while report["has_more"]:
    report = await cleanup_documents(
        session, store, authenticated_user.id, dry_run=False, after=report["next_cursor"]
    )
```

Cleaner selects expired, not-yet-completed tombstones ordered by (purge_after,id), verifies candidate output paths/digests,
and protects living/unexpired documents including copies/snapshots, PENDING/PROCESSING job input/traces, and all
experience source_locator assets, including archived experiences. It does not discover orphan files by directory scanning.
Only expired document PDF/LaTeX outputs are candidates; input-only avatars are not cleanup targets.
Unlink eligible files under the same mutex before committing completion markers. Failed unlink or commit leaves
uncompleted tombstones retryable; already missing files are tolerated. A protected output prevents row completion.
`has_more`/`next_cursor` support dry-run and real cleanup; finish a round by following the cursor, then begin a later
round with after=None to recheck protected rows whose references may have changed. There is no stored scheduler cursor.
Do not remove old files, unknown files or uncertain `.pending` references. No timer/production cleanup is started.

## Legacy PDF delete compatibility

The existing delete route locks the matching owner/id/filename row, records a pending cleanup journal, and commits
database deletion before unlinking the PDF. MySQL FK1451 produces HTTP409 and preserves PDF plus source records;
other commit failures preserve PDF/journal. A successful commit followed by unlink failure returns success with
`file_cleanup_pending=True` and a cleanup task ID, instead of claiming the record deletion failed.
Journals are Git-ignored at `FastAPI-Backend/data/resume_delete_pending` and must be retained with the legacy files.
Internal `retry_legacy_file_deletions` requires a fresh session: it checks that the resume row is absent before unlinking,
retains journals when a row still exists, and retries file failures. This also reconciles lost commit acknowledgements.
No background retry service is started. Pending journals and returned status need integration with future maintenance.

## Validation and remaining scope

Original fresh run: 60 passed, 0 skipped, 9.06s, including14 real database integration scenarios.
Review-fix full regression on MySQL9.6.0: **78 passed, 0 skipped, 21.33s**, including31 real database cases and47 unit cases.
The previous 70-test characterization run proved defects; its new tests now assert corrected business behavior.
Added coverage includes FK-rejected/normal legacy deletion, commit failure/lost acknowledgement, pending unlink retry,
completed/protected cleanup heads with limit=1, active/archived experience source protection, partial unlink failures,
three incomplete-output variants, direct-SQL output CHECKs, consistent names, 002 invalid-row preflight and marker reset.
Legacy route tests load its actual business body through AST with a framework exception stand-in; no HTTP/ASGI test
or full FastAPI dependency installation is claimed. See [review verification and fixes](resume_phase1_review_verification.md).
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
| ab20ac5 | Original storage handoff |
| 95e4ed9 | Legacy PDF preservation and pending deletion reconciliation |
| a4ef94b | Complete outputs, unified names and migration002 |
| 6a3e6be | Cleanup cursor, provenance protection and actual completion |
| f90f740 | Correct-behavior regression and failure/migration recovery tests |

Review fixes and their regression/docs commits follow these entries in the local log.
Use `git log --reverse b7bf53ff27748db720b28c40c0c6409e1ef33d5c..HEAD --oneline` for fresh local commits.
No old P1 commits are ancestors of this branch. Every new commit references Issue1, never closes Phase0–7.
