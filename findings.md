# Restart findings

- Fresh branch HEAD equals fetched origin/master b7bf53ff27748db720b28c40c0c6409e1ef33d5c.
- Old tracked Phase 1 implementation disappeared by normal clean branch switch, remains on old branch.
- Master has six LaTeX bundles; no Phase 1 ORM/migration implementation visible.
- Project-only venv and prior local artifacts retained; dependencies may be reused, source code/results may not.
- Fresh public Issue fetched into ignored .phase1-local/issue1-restart.md; Phase 1 still four-table storage only.
- Master P0 input types allow server fields and wrong category, have unvalidated dates, string owner and TS camelCase; minimal storage-dependent fixes documented.
- Legacy resume PK BIGINT and optimization PK VARCHAR(36) require online reflection of signedness/collation; neither legacy table is changed.
- New immutable snapshots use ORM guards; private file attachment and cleanup share MySQL advisory mutex held through DB commit/file handling. Unknown/legacy files are never scanned for deletion.
- Final independently authored suite: 60 passed, no skips (9.06s), including14 real MySQL9.6 scenarios. Random-schema teardown succeeded; no existing DB modified. Online migration verifies real UNSIGNED/collation legacy differences.
- JSON nullable fields must use SQL NULL; MySQL DATETIME(6) preserves UTC retention microseconds. Locked reads refresh identity-map values to protect traces added by another session. Document snapshot input files require the same private boundary as output attachments.
- Inherited template resources and legacy main/routes/models have no diff against fresh master. Frontend/TypeScript full build, old AI end-to-end and real template compilation remain unexecuted/outside storage verification.
