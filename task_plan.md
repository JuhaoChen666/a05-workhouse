# Phase 1 restart — Refs #1

Project/writable scope: H:\Code\program\2026外包\a05_plus; task-related files only.
Fresh branch: feat/resume-phase1-storage-v2, created 2026-09-17T19:10:03+08:00.
Baseline: origin/master b7bf53ff27748db720b28c40c0c6409e1ef33d5c; HEAD equality verified.
Old P1 branch retained for reference only. No copying old code, cherry-pick, merge, push, PR or deployment.

1. Reinspect current Issue and master contracts/legacy storage/templates — complete.
2. Define storage contracts and implement four tables — complete, locally committed.
3. Implement scoped migrations and transactional owner repository/snapshots — complete, offline and live MySQL passed.
4. Implement six-template immutable initialization and private files/retention — complete, fresh MySQL and boundary tests passed.
5. Execute fresh real MySQL and boundary tests — complete: 60 passed, zero skips, 9.06s; compileall/offline upgrade+downgrade/diff checks passed.
6. Document handoff and make staged local commits — complete through ab20ac5.

## Errors
See progress.md: offline constraint copying, nullable JSON SQL NULL, UTC microsecond retention rounding corrected. Original pyproject metadata mistakenly replaced in uncommitted worktree, reported/restored with diff verification; only two pytest settings remain changed. Existing ignored local test artifacts preserved and ignored, never reuse old test results.

## Review verification
Completed code inspection and empirical reproduction of 4 business defects plus name inconsistency. The historical70-test run asserted faulty behavior and was not fix acceptance. Subsequent authorized fixes are recorded below. Details:docs/specs/resume_phase1_review_verification.md.

## Review fixes (authorized)
1. Preserve old PDF for FK/commit errors; successful delete plus retryable file backlog — implemented and verified.
2. Require complete outputs/consistent names, add incremental migration with invalid-row preflight — implemented and verified.
3. Cursor cleanup, actual-completion markers/retries and all experience source protection — implemented and verified.
4. Convert characterization tests, complete real MySQL regression and docs/local commits — complete:78 passed, zero skips; fixes95e4ed9,a4ef94b,6a3e6be and regressionf90f740 locally committed; handoff/docs updated. No merge/push.
