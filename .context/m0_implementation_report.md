# Phase M0 — baseline, isolation and implementation contracts

Completed 2026-10-14. M1 dashboard implementation is next. This phase establishes
the protected starting point; `/admin` authoring and uploads are future work.

## Executed results

| Check | Actual result |
| --- | --- |
| Local Docker stack | DB/API/web healthy; web 13000, API 18000, PostgreSQL 5433 |
| Runtime | Python 3.13.3; Node v25.2.1; npm 11.6.2; Vite 5.4.21; PostgreSQL 16.15 |
| Current source | `alphazee_dev`; Alembic `c94e31f7d562`; git HEAD `1d46de96006c94b6a0ce247749473e07686942c5` |
| Live direct and web-proxied HTTP | Readiness 200; checkout/test mode false; COD capability only; anonymous owner overview/catalog 401; public order POST 503 |
| Private development backup | Snapshot-consistent custom-format PostgreSQL archive written under Git-ignored `.local/backups` |
| Restore | Fresh `alphazee_m0_restore_1c50de0a3e56_test`; restore completed without `--clean` or source writes |
| Preservation | Every public table's sorted row digest/count matches restored database; development before/after row digests and local configuration hashes match |
| Supplemental schema comparison | Restored columns, constraints, indexes, triggers and sequence settings/current values match source, after normalizing equivalent PostgreSQL varchar-array/text-array cast syntax |
| Backend regression | 209 passed in 120.66 seconds; one existing Starlette/AnyIO deprecation warning |
| Frontend regression | 83 passed, zero failures; Node DOM/mocked API tests, not browser evidence |
| Frontend production build | Passed; 27 modules transformed |
| New migrations/browser | No schema change; migrations not applicable in M0. Browser not executed; future checklist remains pending |

All catalog/commerce tables were empty at this baseline; the full table counts
and digests are in `m0_baseline_verification.json`. Restoring empty commerce
tables verifies the schema and existing rows, not future nonempty catalog/media
migration backfills. M2/M3 require dedicated historical fixtures and media tests.

## Files and contracts established

- `backend/scripts/verify_m0_baseline.py`: repeatable baseline/backup/restore
  verifier; confirms Compose and inspected source share the PostgreSQL system
  identifier; writes only a fresh generated restore database and private archive.
  Keeps credentials/raw rows out of output. All source inspections are read-only.
- `.gitignore`: excludes `.local/`, including private archives. Existing local
  environment files and application data were not edited.
- `m0_catalog_media_contracts.md`: draft/publication rules, exact PKR handling,
  edit versions/conflicts, proposed protected endpoints, media roles/limits,
  public/private serializers and readable owner stock holds.
- `owner_catalog_phase_status.json`: M0 completed and later phases pending.
- `owner_catalog_migration_verification.json`: explicitly no M0 schema changes;
  required M2 migration evidence remains unexecuted.
- `owner_catalog_browser_checklist.md`: future isolated dashboard/product/media
  and commerce scenarios, all pending.
- Main milestone plan updated with M0 evidence and current status. Earlier repair
  verification documents remain historical evidence for that earlier milestone.

## Commands executed

From `F:\AlphaZee`:

```powershell
docker compose --env-file .env.docker.local ps
backend\.venv\Scripts\python.exe backend/scripts/verify_m0_baseline.py
backend\.venv\Scripts\python.exe -m pytest backend/tests -q -p no:cacheprovider --tb=short
```

From `F:\AlphaZee\frontend`:

```powershell
npm.cmd test
npm.cmd run build
```

The final schema/sequence check was a supplemental read-only comparison of the
retained source and restore using the verifier's schema fingerprint function;
that comparison is now also included in future full verifier runs. Equivalent
array-cast normalization is narrow: other SQL definition details are retained.
Diff/format checks passed. Docker access for the Python backup command required
and received sandbox escalation; no failed sandbox call was recorded as a pass.

## Private backup and isolation

Archive: `.local/backups/alphazee_m0_restore_1c50de0a3e56_test.dump`.
Restore database: `alphazee_m0_restore_1c50de0a3e56_test` on the existing local
PostgreSQL instance. Both are retained for inspection. Do not commit/share the
archive or use this clone for browser checkout: it is a private development
backup, potentially containing owner/customer data on future runs. No API or
checkout service was started against the restored database.

The portable archive intentionally omits ownership/ACL restoration; restoring
to a new host also requires separately provisioned database roles/configuration.
This milestone's managed media storage does not exist yet. M3 will require
consistent DB-plus-media backups; this database-only backup cannot prove future
file durability. Regression tests use their existing guarded `alphazee_test`,
not the development or restore database.

The verifier leaves failed/partial private backups or generated destinations
for explicit inspection rather than automatically deleting them. On any failed
rerun, do not treat an older success JSON as fresh evidence. Successful runs
include their own UTC timestamp, revision, archive checksum and destination name.

**Acceptance:** M0 is complete: baseline protections passed, source/config
preservation was checked, a backup was restored in isolation, and implementation
contracts/evidence registers are recorded. No public orders or production launch
were enabled. M1 is the direct owner dashboard entry and shell.
