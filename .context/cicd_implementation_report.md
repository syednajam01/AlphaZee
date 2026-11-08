# CI/CD implementation report

Initial implementation report, 2026-11-08. **Subsequent activation and live rollout are complete:** see [deployment repair and evidence](cicd_deployment_repair.md). The original local verification and initial handoff below are historical. Follow [the runbook](cicd_runbook.md) for operation.

## Delivered

- `.github/workflows/ci.yml`: PR/main/merge-group/manual checks; frontend tests/build, full backend suite on disposable PostgreSQL, clean migration cycle plus legacy ownership migration test, deployment tests, production packaging/preflight and browser smoke; aggregate `ci-required` gate.
- `release.yml`: reusable workflow called only after successful main-push CI and the explicit enable flag. Builds production images, checks the actual images before publishing, pushes SHA tags to GHCR, and deploys digest references using Azure OIDC/VM Run Command.
- `rollback.yml`: main-only manual recovery to the recorded previous release, sharing the production concurrency lock. Actions are pinned to official commit SHAs; actionlint is digest-pinned. Dependabot covers Actions/npm/pip.
- `ops/deploy.py`: private host config, existing volume-and-mount verification, architecture/space checks, external-volume overrides, immutable release metadata, protected environment snapshots, initial image/config baseline, host lock, stale release rejection, fresh one-off migrations, HTTPS/revision checks and compatible image recovery.
- Consistent DB/media snapshots quiesce the API only during local capture, resume it before Azure uploads, require a private Blob container, validate uploaded content/sizes and publish a completion receipt last. Temporary generated dump/archive files are deleted only after successful off-host upload. Persistent volumes and off-host backups are never deleted by this code. A recent real restore exercise is required before automatic deployment.
- `ops/remote.py`: bounded non-secret release transfer and guest success-marker checking; a successful Azure control-plane request alone is not deployment success.
- Read-only VM inventory, synthetic production preflight checks, Linux-compatible fixture-backed browser tests, settings setup scripts and a host configuration example that refuses deployment while placeholders remain.
- Public `/release.json` and `/api/v1/release` revision markers with no-store caching. Revision arguments sit after dependency layers so each commit does not invalidate Python dependency installation.

Confirmed target names: resource group `alphazee-staging`, VM `alphazee-vm`, deployment directory `/home/azureuser/alphazee`, Compose project `alphazee-prod`. Volume names, private environment/override paths, architecture, credentials and backup account have not been inferred.

## Executed verification

| Check | Actual result |
| --- | --- |
| Frontend suite | 139 passed |
| Full existing backend regression suite | 337 passed, one existing Starlette/AnyIO deprecation warning |
| New release diagnostics test and related focused health checks | 4 passed; run after adding the new endpoint test |
| Deployment/transport failure tests | 22 passed on Windows and in the Linux API image |
| Fresh migration upgrade/downgrade/re-upgrade | Passed on a newly created loopback PostgreSQL database, dropped afterward |
| Seeded legacy ownership upgrade/downgrade/re-upgrade | Passed on a separately created disposable database, dropped afterward |
| Final API and production frontend Docker builds | Passed |
| Production configuration preflight and unsafe configuration rejection | Passed with synthetic credentials |
| Browser smoke | Headless Chrome/Playwright passed at 1440×900 and 390×844: home → product, deep reload, cart, closed checkout, admin/vendor login screens; synthetic API responses, no live writes |
| Workflow/schema/expression/shell validation | Actionlint passed; immutable-action policy passed; Azure setup shell syntax passed |

Local browser smoke used installed headless Chrome; hosted CI installs the pinned Playwright Chromium. Failure tests cover stale workflows, foreign/mutable image rejection, missing backup, migration failure, bad health, failed recovery, incompatible schema, changed runtime configuration, anonymous branch restrictions and missing guest success markers. These are simulated failure tests, not a live Azure rollback demonstration. Local terminal verification used `ops/compose.ci.yml`, a fresh tmpfs PostgreSQL on 15439, plus separate local image/container names.

The initial full-suite attempt used test mode and exposed 15 pre-existing tests intentionally requiring development provisioning. CI now uses **development application mode with distinct disposable databases**, retaining all test-database guards. The corrected full suite passed; production preflight independently rejects debug/test checkout settings. No security restriction was weakened.

## Remaining external activation

Read-only GitHub connector access confirmed this public repository and admin permission. Available connector tools do not support repository protection/environment/secret setup; no Azure CLI login/session is present here. Setup scripts and exact instructions are provided rather than claiming those operations occurred.

Before CD can work: push/review/merge the code; install branch/environment settings; configure Azure OIDC identifiers and VM role; inspect actual VM volumes/config/architecture; configure private GHCR pull access; provide private off-host backup storage and VM identity permission; demonstrate a real matched restore; install root-owned host config/proof; then enable the repository flag and merge a benign release. No passwords/private keys belong in chat.

Automatic rollback never downgrades a database or restores an old backup over new orders. New migration heads require explicit reviewed backward compatibility; changed private runtime configuration blocks automatic restoration of older settings. The single-VM approach has backup-capture/replacement interruptions and does not provide high availability. Off-host backup lifecycle, budget monitoring and cleanup of obsolete images/releases remain deliberate operational tasks.
