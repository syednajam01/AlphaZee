# Live CI/CD inventory

Updated 2026-11-08. Owner-confirmed, not independently inspected on the VM:

| Setting | Value |
| --- | --- |
| Domain | `alphazee.tech` |
| Azure resource group | `alphazee-staging` |
| VM | `alphazee-vm` |
| Deployment directory | `/home/azureuser/alphazee` |
| Compose project | `alphazee-prod` |
| GitHub repository | `syednajam01/AlphaZee` |
| Main branch | `main` |

GitHub connector independently confirms the repository is public and the connected account has administrative access. Its available tools do not expose branch protection, Actions variables/secrets or Azure configuration operations. No Azure CLI/session is available here. No live deployment command has been issued.

Still required: VM architecture/OS, exact Compose files, private environment path, four actual volume names/mounts, running image IDs, database migration head, Azure subscription/tenant/identity IDs, private backup account/container and restore proof. Use `ops/inventory.py` following the runbook; it emits no container environment variables or credentials. Inspect additional writers/cron jobs and quiesce them during matched backups if they exist.

Do not guess volume names from the project name. Do not replace existing host configuration or live source changes before reconciling them. `ops/host-config.example.json` intentionally refuses deployment while volume/storage/product placeholders remain.
