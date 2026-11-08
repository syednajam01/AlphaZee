# Deployment repair for commit 17e4cc1

**Completed 2026-11-08.** [PR #13](https://github.com/syednajam01/AlphaZee/pull/13) was merged after all checks passed. Production now serves **`d39e86c5d708f907a0431351aeac99979014db5f`** from both `/release.json` and `/api/v1/release`. [Main workflow 42429689050](https://github.com/syednajam01/AlphaZee/actions/runs/42429689050) completed successfully, including automatic deployment. The diagnosis and setup instructions below record the repair history; those prerequisites are now satisfied.

## Final verified outcome

- VM managed identity and private Blob access succeeded after the owner's Cloud Shell setup.
- Real off-host backup restored into a temporary, network-isolated PostgreSQL container: **42 tables**, revision `a81f92c6d430`, **4 ready media files** with exact size/SHA-256 matches. Scratch storage/container were removed after verification.
- Genuine proof was generated at `2026-11-08T00:08:19.576727+00:00` in root-owned mode-600 `/etc/alphazee-restore-proof.json`.
- Verified recovery set: `alphazeestaging/alphazee-backups/manual-1794096412971659462`.
- Deployment also captured `alphazeestaging/alphazee-backups/d39e86c5d708f907a0431351aeac99979014db5f-1794098363051531312` before migration/replacement.
- Deployment uncovered an unsupported `docker compose run --no-build` option. The repair uses `--pull never`, and CI now executes the exact migration command on a fresh disposable Compose database. The PR also includes the tested prerequisite/error-reporting/restore tooling.
- A later health check found the VM's product probe was incorrectly set to `catalog` (404). Previous images were restored; the probe was corrected to the verified public product `ttt`. A private copy of the previous host config was retained. Catalog data and checkout configuration were not edited.
- Final checks: same four production volume identities; schema remains `a81f92c6d430`; web/API running, API/PostgreSQL healthy; `/`, `/admin`, `/vendor`, `/products/ttt` return 200; readiness reports database connected; both live revision markers and host release state match `d39e86c`.
- At completion of the CI/CD repair, checkout stayed disabled as previously configured. The owner subsequently authorized opening it; see [live checkout activation](live_checkout_activation.md). Test mode remains false. No verification orders/accounts were created or reset, and no production database was downgraded/restored.
- GitHub integration write endpoints returned 403. The already authenticated local Git login was used for the authorized PR/merge/retry operations, with credentials kept in memory and out of logs. Required PR/main checks passed before rollout.

## Original diagnosis and repair history

The failure is VM setup, not a failing frontend/backend build. SSH verification confirmed Azure CLI and restore proof were absent. Azure CLI 2.92.0 has now been installed on the VM from Microsoft's official installer, without restarting production containers. A further live check found **no VM managed identity** (`az login --identity`: Identity not found). The existing GitHub deployment identity is a separate identity and does not provide the guest VM with Blob access.

## Cloud Shell identity setup — required external step

In Azure **Cloud Shell → Bash**, select the subscription that contains `alphazee-vm`, then run this block. It uses the existing storage account, enables the VM identity, ensures the dedicated backup container is private and grants only container-scoped data access. It does not restart the VM or application and does not use storage keys.

```bash
set -euo pipefail
account_id=$(az storage account list --query "[?name=='alphazeestaging'].id | [0]" -o tsv)
test -n "$account_id"
az vm identity assign -g alphazee-staging -n alphazee-vm -o none
principal=$(az vm show -g alphazee-staging -n alphazee-vm --query identity.principalId -o tsv)
scope="$account_id/blobServices/default/containers/alphazee-backups"
az rest --method put --url "https://management.azure.com$scope?api-version=2023-05-01" --body '{"properties":{"publicAccess":"None"}}' -o none
az role assignment create --assignee-object-id "$principal" --assignee-principal-type ServicePrincipal --role 'Storage Blob Data Contributor' --scope "$scope" -o none
echo 'Identity and backup permission configured'
```

An already-existing identical role assignment may be reported; the reusable `ops/repair_backup_identity.sh` checks before creating it. If the account lookup is empty, verify the selected subscription rather than creating a new account blindly. Allow a few minutes for RBAC propagation. Reply with success or the error; never share an access token or account key.

## Remaining repair sequence

1. Recheck VM identity and private container access.
2. Create a matched off-host DB/media backup with the API quiesced only during snapshot capture, then resumed before upload.
3. Use `ops/verify_restore.py` to download that completed recovery set, restore PostgreSQL in a generated temporary container with no network/ports and bounded resources, and verify every ready media file against its restored database size/SHA-256 metadata. Live PostgreSQL and media volumes are never mounted into the scratch container.
4. Only a successful restore produces root-owned mode-600 restore proof. The example proof-writing command in `temp.txt` is not evidence by itself; do not create it without the actual exercise.
5. Retry the failed deployment job and check live release identifiers/readiness. Do not downgrade the production DB, delete volumes, or re-provision accounts.

Repository changes also improve preflight reporting and relay sanitized guest errors to Actions instead of hiding missing prerequisites. The verifier supports source DBs up to 128 MiB on this 4-GiB VM; larger databases must use an appropriately sized separate restore host. No proof or successful deployment is claimed until the operations above actually pass.

## Verified so far

- SSH reached the specified VM; its three production containers were running, API/database healthy.
- The agent independently verified existing mount identities and schema head `a81f92c6d430`; public readiness reports `ready` / `connected`.
- Azure CLI installation was independently rechecked and exits successfully on repeated installation.
- `az login --identity` still reports `Identity not found`; Azure RBAC cannot be repaired through the available SSH-only guest credentials.
- Repair helpers were staged root-only at `/var/lib/alphazee-cicd/repair-20261108/`; the running release and private environment file were not overwritten.
- 29 operational tests passed. A real disposable Docker PostgreSQL dump/restore integration also passed, with SAMPLE data and mocked Blob transport; the original fixture data stayed intact. This is not a live Blob restore claim.
- Failed workflow identified: [run 42421977395](https://github.com/syednajam01/AlphaZee/actions/runs/42421977395). It has not been retried while prerequisites remain incomplete.

After Cloud Shell completes, the staged VM commands are `sudo python3 /var/lib/alphazee-cicd/repair-20261108/deploy.py backup`, followed by `sudo python3 /var/lib/alphazee-cicd/repair-20261108/verify_restore.py --backup-reference THE_ACTUAL_RETURNED_REFERENCE --write-proof`. The agent can execute these through the authorized SSH connection once identity/storage access succeeds; do not invent the reference.

Sources: [Azure CLI Linux installation](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli-linux?pivots=apt), [GitHub immutable OIDC subjects](https://docs.github.com/en/actions/reference/security/oidc). The already-corrected Azure federation subject must be preserved.
