# CI/CD setup and operation

Updated 2026-11-08. Repository implementation is present; **production automation has not been activated or tested against Azure**. Existing alphazee.tech containers/data were not changed. Start with `.context/cicd_live_inventory.md`.

## What is implemented

PRs, main pushes, merge groups and manual CI runs check frontend, backend, disposable migrations, operational failure cases, production image configuration and browser smoke. `ci-required` is the aggregate gate. Only a successful **main push**, with repository variable `PRODUCTION_DEPLOY_ENABLED=true`, calls the release workflow. A manual CI run does not deploy.

Release builds production images, checks those exact images before pushing to GHCR, and transfers only source configuration/scripts and digest references to the VM. Azure uses GitHub OIDC, not a stored Azure password. There is one deployment at a time, plus a host filesystem lock and stale-workflow checks. Successful releases record metadata in `/var/lib/alphazee-cicd`.

The VM validates existing storage identities, pulls images, takes a matched DB/media backup, runs a fresh migration container, replaces API/web and checks HTTPS/readiness/capabilities/product/revision. It never rebuilds on the VM or recreates PostgreSQL. Backup snapshots briefly stop API writes; uploads happen after the old API resumes. This and container replacement cause interruptions: this is not zero-downtime deployment.

## One-time setup, in order

1. **Review/push these files in a branch and open a PR.** Leave CD disabled. The workflow runs from the PR branch; verify every check on GitHub, not just the local report. Merge only after checks pass. This change does not itself push code or create a PR.

2. **Inspect the VM.** In its deployment checkout, using the actual private environment file/Compose paths:

   ```sh
   cd /home/azureuser/alphazee
   python3 ops/inventory.py --project alphazee-prod --env-file .env.production --compose-file compose.prod.yml
   uname -m
   df -h
   ```

   Pass repeated `--compose-file` arguments if production uses overrides. Record the actual volume names, image IDs and source differences privately. Current release building supports `x86_64` → `linux/amd64`; ARM needs a deliberate build/test runner extension. Require Docker Compose with `up --wait`, Python 3.10+, GNU tar/du and Azure CLI on the VM. Confirm no external jobs also write DB/media. Do not paste `.env` or full `docker inspect` output into chat.

3. **Configure GitHub protection and the production environment.** In a trusted terminal run `python ops/configure_github.py` after the first CI check exists. It prompts secretly for a temporary fine-grained setup token with repository Administration, Environments and Variables write permissions. Alternatively enter the same settings manually in GitHub. It requires PRs and `ci-required`, prevents admin bypass/force push/deletion, allows production deployments from `main` only, sets the VM/group variables, and keeps CD **false**. Zero additional approving reviewers supports the solo owner. Revoke the setup token afterward. Do not reuse it as the runtime registry token.

4. **Configure Azure federation.** In authenticated Azure Cloud Shell, on the right subscription, with this code available, run `bash ops/setup_azure.sh`. It creates/reuses the `alphazee-github-deploy` user-assigned identity, trusts the confirmed immutable subject `repo:syednajam01@195332109/AlphaZee@1407763091:environment:production`, and grants a narrowly scoped VM Run Command role on `alphazee-vm`. Preserve the existing corrected federation. The script prints three identifiers. Add them under GitHub Settings → Environments → production → Secrets:

   - `AZURE_CLIENT_ID`
   - `AZURE_TENANT_ID`
   - `AZURE_SUBSCRIPTION_ID`

   These identifiers are not passwords. The deployment identity can execute root commands on this VM, so protect changes to workflows/ops. Keep SSH limited to the owner's IP. The VM agent needs outbound HTTPS connectivity; no new public CI SSH rule is required. The VM's own managed identity is separate and must also be enabled for Blob access.

5. **Configure private off-host backups.** Select an existing private Azure Blob container, or create one deliberately after checking storage cost/retention. In Cloud Shell set `BACKUP_STORAGE_ACCOUNT`, `BACKUP_RESOURCE_GROUP`, `BACKUP_CONTAINER`, then run `bash ops/setup_backup_access.sh`. This grants the **VM's system-assigned identity** access to that container. It is separate from the GitHub deployment identity. The invoking owner must be able to read the container and assign roles. On the VM install Azure CLI if missing; `sudo az login --identity` should work after RBAC propagates. No storage account keys are needed. Never make the container public.

6. **Install host prerequisites and configuration.** Run `sudo bash ops/install_vm_prerequisites.sh` on the VM to install Azure CLI if absent, without restarting app containers. Copy `ops/host-config.example.json` to `/etc/alphazee-cicd.json`, fill the exact inspected Compose/env paths, four existing volume names, private storage account/container, current checkout-enabled boolean and one active product slug. Preserve existing bank credentials and flags in `.env.production`. Then:

   ```sh
   sudo chown root:root /etc/alphazee-cicd.json
   sudo chmod 600 /etc/alphazee-cicd.json
   sudo install -d -o root -g root -m 700 /var/lib/alphazee-cicd
   sudo python3 ops/deploy.py inventory
   ```

   Root release state also contains private environment snapshots; do not publish/upload this directory as an Actions artifact. Existing volumes must match container mounts, not just exist. Missing/wrong settings fail before replacement.

7. **Set up private registry pulling.** GHCR packages may be private even though the source repository is public. Log root's Docker client into GHCR once using a dedicated classic PAT with **read:packages** only, entered privately with `docker login ghcr.io --username YOUR_GITHUB_USER` (password prompt). Workflow publication uses ephemeral `GITHUB_TOKEN`; no publishing PAT is stored on the VM. Do not make images public to avoid configuring authentication.

8. **Prove restore before enabling deployment.** First run `sudo python3 ops/deploy.py backup` during a suitable short maintenance window. This stops API writers for dump/archive capture, restarts the existing API, uploads both files with content validation, verifies sizes, and uploads `receipt.json` last. Temporary local dump/archive copies are removed only after successful upload; source volumes are untouched. Incomplete uploads are not valid recovery sets. Failed copies remain private for inspection.

   For small databases on a sufficiently sized VM, run `sudo python3 ops/verify_restore.py --backup-reference ACCOUNT/CONTAINER/ACTUAL_COMPLETED_PREFIX --write-proof`. It restores the backup to a resource-bounded scratch PostgreSQL with no network/ports, checks its schema revision and every ready asset's size/SHA-256, then writes proof only on success. Larger databases require a separately sized host; follow `.context/m3_media_runbook.md`. Never restore over live data. Proof has this shape:

   ```json
   {"verified_at":"ACTUAL_UTC_ISO_TIMESTAMP", "restored_database_and_media":true, "backup_reference":"ACTUAL_PRIVATE_COMPLETED_SET_REFERENCE"}
   ```

   Do not manually fill placeholders and mark a restore successful without performing it. Proof expires after 30 days. Run `sudo python3 ops/deploy.py preflight` to check prerequisites, storage access, schema and inventory without stopping the API. Backup sizing checks reserve DB/media capture space plus a safety margin. Set Blob retention/lifecycle and budget monitoring deliberately; no automatic off-host deletion is implemented. Protect the private environment file separately in your secret recovery process.

9. **Enable only after rehearsal.** Run the failure/rollback tests on GitHub and verify host inventory, registry access, completed off-host backup and restore proof. Set repository variables:

   ```text
   AZURE_RESOURCE_GROUP=alphazee-staging
   AZURE_VM_NAME=alphazee-vm
   PRODUCTION_PLATFORM=linux/amd64
   PRODUCTION_DEPLOY_ENABLED=true
   ```

   Then merge a benign visible change. This is the first live acceptance test. Verify the Actions result, live site and `/release.json` plus `/api/v1/release` both showing that merged SHA. If the VM architecture is not x86-64, stop before enabling.

## Normal operation and recovery

Develop on a branch, open a PR, wait for CI, review and merge. A newer main commit can supersede an older release before VM invocation. Deployments are serialized and cannot overwrite a successfully deployed higher workflow sequence. No live orders or stock are created by smoke tests.

`/var/lib/alphazee-cicd/current.json` records the last successful release; `previous.json` records the rollback target. Bootstrap snapshots preserve the originally running images and Compose files. Keep those images available; do not prune active/rollback images or any persistent volumes. The VM working checkout is not overwritten by CD; candidate Compose/scripts live in versioned private release directories.

If new health checks fail, image recovery is attempted only when schema compatibility is established and private runtime configuration has not changed. An automatic recovery still makes the workflow fail so the bad release is visible. Otherwise deployment stops for a reviewed forward fix. A failed migration never causes a database downgrade or old backup restoration. Notifications follow GitHub's workflow notification settings; no third-party messaging was enabled.

For manual image recovery, run GitHub Actions → **Production rollback** → Run workflow on `main`. It selects only the recorded previous successful release, not arbitrary untested commits. If Azure cannot invoke the guest script, inspect VM agent/identity privately; do not repeatedly retry a partially completed migration blindly. The emergency local command is `sudo python3 ops/deploy.py rollback` with the same root config. Rollback itself must pass health checks.

Adding migrations requires testing upgrade paths and explicitly listing the reviewed **backward-compatible target head** in `ops/migration-policy.json`. Review every newly applied revision, including partial-failure compatibility. Incompatible schema changes need a separate maintenance/expand-contract plan. Changes to `.env.production` require deliberate operational review; rollback refuses to silently restore older checkout/bank settings. Keep project/domain/volume identities fixed.

To suspend automatic updates, set `PRODUCTION_DEPLOY_ENABLED=false`; this does not cancel an already-running deployment. To stop new orders use the separate checkout release runbook, not CI/CD flags. Never run `down -v`, volume prune, test seeding, owner resets or a DB downgrade on production.

## What remains outside local verification

Actual branch protection/settings installation, OIDC/RBAC, private GHCR pulling, VM inventory, Azure Blob uploads, real backup restoration, first live deployment and first live recovery require your Azure/GitHub setup. Local tests simulate deployment failures; they do not certify these external operations. No live website was updated in this implementation session.

References: [GitHub protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches), [GHCR authentication](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry), [Azure OIDC](https://learn.microsoft.com/en-us/azure/developer/github/connect-from-azure-openid-connect), [VM Run Command](https://learn.microsoft.com/en-us/azure/virtual-machines/linux/run-command), [Blob content validation](https://learn.microsoft.com/en-us/cli/azure/storage/blob).
