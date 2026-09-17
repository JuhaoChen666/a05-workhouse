# Phase 1 persistence — Refs #1

Fresh implementation on origin/master b7bf53ff27748db720b28c40c0c6409e1ef33d5c, branch feat/resume-phase1-storage-v2.
Original Phase 1 branch is abandoned; no old source code copied or old commits cherry-picked.

Owner is the trusted positive Integer matching Spring User.userID and existing ORM, never client user_id.
Experience creation forbids server-managed ID/timestamps/revision. Five discriminated categories retain P0 fields;
common fields include sorting, archive, tags and MANUAL/PDF_IMPORT provenance. PDF sources are optional and do not verify facts.
YYYY-MM is validated; null means unspecified, only end_date=present means ongoing. End cannot precede start.
Updates replace the complete validated input, keep type fixed and atomically compare/increment revision.

Template identity is (template.json id, version); retain every file byte including classes, metadata, main source and digests.
Seed all six current master bundles UNVALIDATED/disabled. Existing identity with any changed content raises a conflict.
Generation requires explicitly pinned VALIDATED/enabled template. Freeze full template/JD/experience revision/content,
personal information and options. JOB_ID resolves actual Job.jobContent via trusted adapter, not positions classification.
Null selection freezes all active experiences; [] freezes none. Phase 1 does not perform AI recommendation.
Keep P0 statuses PENDING/PROCESSING/COMPILED/FAILED; store progress/error/retries/traces without running generation.

Documents own immutable job snapshots/files, support rename/copy and soft deletion with default 30-day retention.
Creating a LaTeX document requires both verified PDF and LaTeX output assets; a database CHECK also rejects missing outputs.
Create/rename/copy/save-legacy share one name validator: trim whitespace, reject empty, maximum 200 characters after trimming.
Old optimization Markdown is read owner-scoped and optionally saved explicitly, never bulk converted.
Four tables use shared session_models.Base, MySQL JSON/InnoDB/utf8mb4, RESTRICT foreign keys and owner indexes.
Caller owns AsyncSession/transaction; repository flushes but never commits. Historical content is guarded at ORM layer;
arbitrary direct SQL is not an approved business interface and can bypass ORM immutability.

Necessary P0 corrections: reject managed creation fields, fix category/date validation, align owner Integer,
preserve full metadata extras, and align currently unused Python/TypeScript names to snake_case.
The existing resume delete route now commits record deletion before touching its PDF, returns 409 for source references,
and journals failed/uncertain cleanup for internal retry. No new business routes/UI/authentication rewrite or changes to
inherited template resources/legacy table definitions. Cleanup protects active and archived experience provenance,
skips completed tombstones, and returns a keyset cursor to advance past protected records.
