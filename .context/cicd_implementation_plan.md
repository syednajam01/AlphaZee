# AlphaZee CI/CD implementation plan

Status: implemented and live deployment verified on 2026-11-08. See `.context/cicd_deployment_repair.md` for the real backup/restore and successful rollout of `d39e86c`, `.context/cicd_implementation_report.md` for original implementation checks, and `.context/cicd_runbook.md` for operation. The phases below retain the original design rationale.

Owner confirms **alphazee.tech is live on an Azure Linux VM using Docker Compose**. Git remote: `syednajam01/AlphaZee`, branch `main`. No `.github/workflows/` directory currently exists. Existing production setup in source: `compose.prod.yml`, Python 3.13/FastAPI, PostgreSQL 16, Node 22/Vite, Caddy HTTPS. Live VM configuration has not been inspected; attempts to fetch public readiness/capabilities through the research tool were unsuccessful and do not establish an outage.

## 1. Desired everyday workflow

Create a branch → push changes → open a pull request → automated checks pass → merge into protected `main` → check the merged commit → publish immutable images → deploy that release to the existing VM → verify HTTPS/readiness → record success or recover the previous release.

CI means checking changes; CD means delivering checked changes to the live site. You continue reviewing and merging code. Routine successful merges deploy automatically without a second approval. A failed check prevents deployment; branch rules should also prevent merging. No pipeline can prove that every possible bug is absent.

Recommended architecture: **GitHub Actions + GitHub Container Registry (GHCR) + the existing Azure VM/Compose**. Run builds and tests on GitHub-hosted runners, not the production VM. No additional always-on staging VM, Kubernetes or ACR is required for this initial plan. GitHub minutes/storage/package allowances depend on account, repository visibility and usage; inspect them rather than promise zero cost. Backups and image downloads also consume storage/bandwidth.

## 2. Phase C0 — inventory the actual live installation

Before implementing deployment, capture sanitized facts through read-only VM inspection:

- Azure resource group, VM name, CPU architecture, OS, Docker/Compose versions, free disk/RAM and VM agent health.
- Exact deployment directory, Compose files/overrides, **existing Compose project name and volume identities**, current image IDs/digests, migration revision, domain configuration and existing backup jobs.
- Current private environment-file location, runtime flags and storage mounts. Record names/paths only; never copy credentials into documentation, Actions logs or screenshots.
- Whether production contains local server code/configuration changes absent from GitHub. Reconcile these into reviewable source before automating; do not overwrite them.
- Repository visibility, GitHub plan/protection support and package permissions. Confirm which commit is actually running; do not assume current `main` equals production.

Deliverable: `.context/cicd_live_inventory.md`, with sensitive identifiers omitted where appropriate. Freeze VM/project/volume naming in the deployment configuration. Accidentally changing the project name can create empty replacement volumes and make existing data appear lost.

Acceptance: existing website continues running; a recoverable previous release and persistent storage locations are known. C0 is a prerequisite, not a new hosting migration.

## 3. Phase C1 — required pull-request verification

Create `.github/workflows/ci.yml`, triggered by pull requests to `main`, pushes to `main`, and manual runs. If merge queues are enabled later, add `merge_group`. Use fixed, unique required check names and an always-running aggregate `ci-required` job that fails if any required job failed or was cancelled. Avoid path filters that leave required checks pending.

| Job | Required checks |
| --- | --- |
| Frontend | Node 22, `npm ci`, `npm test`, `npm run build` in `frontend/` |
| Backend | Python 3.13, FFmpeg/FFprobe, runtime/dev requirements, PostgreSQL 16 service exposed on runner loopback; full isolated pytest suite |
| Migrations | Fresh disposable database; verify Alembic heads, upgrade to head and supported upgrade paths; exercise reversible migration cycles only on disposable data |
| Packaging | Build production API and production-target frontend images; validate Compose with synthetic configuration; check production preflight guards |
| Browser smoke | Start isolated disposable app, verify home/product routing, admin/vendor login screens and essential cart interactions; use synthetic inventory only |

Reuse `backend/scripts/run_isolated_verification.py`; provision a CI-only bootstrap database/user on `127.0.0.1`, with permission to create its temporary `_test` database. Keep application and test database names distinct. The current fixture creates schema directly, so pytest success alone is **not** migration verification. Existing migration scripts need review/adaptation before becoming CI entrypoints. Use Linux-compatible browser tooling; current local Chrome scripts contain Windows paths and are not ready-made hosted-runner jobs.

Keep CI credentials synthetic and isolated. Upload JUnit/build diagnostics on failure, with short retention and no secrets/customer data. Add pinned action SHAs, dependency review/update policy and vulnerability checks with an explicit remediation policy; do not silently introduce new lint/type gates across unprepared code.

Protect `main`: require PRs, `ci-required`, current merge-base checks, resolved conversations, no force pushes/deletion and no routine administrator bypass. Confirm protection availability for the repository's GitHub plan. A solo maintainer need not require an impossible second-person review.

Acceptance: an intentionally failing PR cannot merge or deploy; a passing PR can. Fork PRs receive no production credentials. Never run untrusted PR code using `pull_request_target` with deployment secrets.

## 4. Phase C2 — publish the checked release

Create a reusable verification workflow or equivalent dependency chain. The release workflow runs on `push` to `main` and explicitly depends on successful checks for **that exact merged SHA**; PR checks alone are insufficient. Avoid a loosely connected `workflow_run` handler that deploys another checkout.

Build two images: `ghcr.io/syednajam01/alphazee-api` and `ghcr.io/syednajam01/alphazee-web`. API and migrations use the same API image. Build for the confirmed VM architecture. Tag with the full commit SHA, record registry digests and deploy by digest; `latest` is not a release identifier. Reuse the resulting artifacts for deployment rather than rebuild on the VM.

Publish using the job's scoped `GITHUB_TOKEN` with `contents: read` and `packages: write`. Create a release manifest containing commit, image digests, migration head and versioned Compose/config checksums. Include a non-secret release identifier in the app/image so smoke tests can prove the new version is serving.

Add an image-only production Compose deployment layer or deliberately revise production image references. Current `compose.prod.yml` names local images and includes build definitions: deploying GHCR images requires an explicit change. Preserve service names, env semantics and storage identities; use `--no-build` in CD. Database/base-image upgrades are separate reviewed releases, not incidental application deployment.

Acceptance: the release pair can be pulled and started in isolation by digest; tests cover the same source SHA and production build configuration. A failed build never touches production.

## 5. Phase C3 — authenticate and prepare the VM

Preferred deployment control: **GitHub OIDC → narrowly scoped Azure identity → VM Run Command → reviewed host deployment script**. This avoids opening SSH to changing GitHub runner IP ranges or storing an Azure client secret. Scope federation to this repository's `production` environment; permit that environment only for `main`. Grant VM-scoped required Run Command/read permissions, not subscription Owner. Run Command is powerful remote execution and normally elevated; treat workflow changes accordingly.

Confirm the subscription permits identity/federation and the VM agent works. If unsuitable, use a documented SSH fallback with pinned host key, dedicated deployment account and restricted connectivity; never open port 22 to the world. Do not install a persistent PR runner on the live VM.

GitHub configuration: production environment; Azure client/tenant/subscription identifiers in secrets; VM/resource group/domain as variables; minimum `id-token: write` only on deployment. If GHCR images are private, provision read-only package credentials privately on the host (or another supported pull mechanism). The workflow's short-lived publishing token is not a permanent VM credential. Do not make images public merely to bypass authentication.

Keep `.env.production` on the VM, privately readable by the necessary account. Root-controlled deployment bootstrap must receive a validated release manifest and its versioned Compose payload from the trusted job; choose and test a bounded non-secret transport during implementation. Do not execute a mutable arbitrary branch script or interpolate untrusted PR fields into shell commands. Do not print resolved Compose configuration containing secrets.

Acceptance: a harmless authenticated status command succeeds; PRs/other branches cannot reach production. No application change yet.

## 6. Phase C4 — deployment transaction and recovery

Implement `ops/deploy.sh`, `ops/rollback.sh` and a read-only smoke script, tested on a disposable stack first. Workflow concurrency permits one production deployment at a time, with `cancel-in-progress: false`; additionally take a host `flock`. Reject stale releases so a delayed older workflow cannot overwrite a newer deployment. Recheck branch/release identity after taking the lock.

Deployment sequence:

1. Validate manifest, expected architecture, disk space, private configuration and volume identities. Pull both exact images while the existing site runs. Save the previous successful manifest and usable image digests.
2. Take a database backup and verify it is readable. Require a recent matched off-host DB/media recovery set and demonstrated restore procedure. If capturing a new matched set, quiesce all relevant writers: DB dump plus a changing media directory is not automatically consistent. Backup failure stops deployment. Backups must never become public Actions artifacts.
3. Review pending migrations for compatibility with the running old API. Prefer additive expand/contract changes. Run a **fresh one-off** migration container from the new API digest; do not trust an old exited `migrate` container as proof this release migrated. Failure blocks API/web replacement.
4. Recreate only API/web using the validated release files and `--no-build`; preserve DB, media and Caddy volumes. Keep web running until API readiness where possible. Explicit orchestration must respect successful migrations and health checks rather than blindly repeating `up --build`.
5. Retry HTTPS readiness with a bounded timeout, check the release identifier and public routes, then record the successful manifest atomically. Alert on failures/recovery and retain sanitized logs.

One VM and a single API replica can have a brief interruption during replacement; this plan does **not** promise zero downtime. Incompatible migrations require an explicitly planned maintenance release rather than an unsafe automatic update. A web container restart can also interrupt in-flight uploads/requests.

Recovery: pull/start the last successful API/web digests and their compatible configuration when safe. **Image rollback never undoes database changes.** Automatic image rollback is allowed only when the new schema remains backward compatible. Otherwise stop, alert and use the reviewed forward-fix/recovery procedure. Never automatically downgrade a live database or restore an old backup over new customer orders. If migration failure is partially committed, investigate before continuing. Verify rollback health and report if recovery also fails.

Never run `down -v`, volume pruning, owner provisioning, catalog seeding or test checkout on production. Preserve the current checkout switch; CI/CD does not open/close commerce as a side effect.

## 7. Phase C5 — safe release acceptance and handoff

First rehearse failed build, failed migration, bad image health, stale deployment and rollback on a disposable stack. Then make one benign, owner-visible production release; do not place real orders automatically.

Live smoke checks: HTTPS `/`, `/admin`, `/vendor`, a known active `/products/<slug>`, `/api/v1/ready`, and `/api/v1/storefront/capabilities`. Parse expected content, not just HTTP 200: the SPA fallback can return 200 for a wrong path. Confirm `test_mode` is false, no lab banner, expected checkout state, valid assets/media and correct release SHA. Browser login/cart/checkout mutation tests belong in isolated CI, not routine live smoke tests.

Record deployment SHA/digests, time, migration revision, backup reference, smoke results and previous release. Set up deployment failure notifications in GitHub; external messaging integration is optional. Add a manual rollback workflow restricted to previously successful compatible releases and a runbook for credential rotation, backup restoration and failed recovery. Retain several known-good releases and backups; cleanup must exclude active/rollback assets and all persistent volumes.

Acceptance: a merged benign change appears at alphazee.tech automatically; deliberately failing changes are stopped before deployment; recovery was demonstrated; existing accounts/orders/media survive. No deployment-time tests modify live stock or finances.

## 8. Deliverables and owner setup

Proposed files: `.github/workflows/ci.yml`, reusable verification workflow, `release.yml`, `rollback.yml`; production image-reference configuration; `ops/` deploy/rollback/smoke scripts; `.context/cicd_live_inventory.md` and `.context/cicd_runbook.md`.

Implementation order: **C0 → C1 → C2 → C3 → C4 → C5**. Build and test the repository automation before enabling production deployment. Owner-side setup requires GitHub repository settings and Azure identity/VM access. Exact VM names, paths, existing project name, repository plan and permissions remain to be discovered; no passwords or private keys should be pasted into chat. This document does not alter the VM, workflows, repository settings or live site.

## Official references

- [GitHub protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches): required checks and plan availability.
- [Publishing Docker images](https://docs.github.com/en/actions/tutorials/publish-packages/publish-docker-images) and [GHCR authentication](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry): workflow publishing and host pull permissions.
- [Azure GitHub OIDC](https://learn.microsoft.com/en-us/azure/developer/github/connect-from-azure-openid-connect): federated identity setup.
- [Azure Linux VM Run Command](https://learn.microsoft.com/en-us/azure/virtual-machines/linux/run-command): VM-agent execution, permissions and operational restrictions.
