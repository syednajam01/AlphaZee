# Live CI/CD inventory

Updated 2026-11-08. Owner-confirmed target, subsequently inspected through authorized SSH:

| Setting | Value |
| --- | --- |
| Domain | `alphazee.tech` |
| Azure resource group | `alphazee-staging` |
| VM | `alphazee-vm` |
| Deployment directory | `/home/azureuser/alphazee` |
| Compose project | `alphazee-prod` |
| GitHub repository | `syednajam01/AlphaZee` |
| Main branch | `main` |

GitHub connector independently confirms the public repository and account access, but write calls return 403. Authorized GitHub changes used the existing local Git login without exposing/storing credentials. Azure CLI 2.92.0 is installed on the VM and authenticates with the VM system-assigned identity.

SSH verification confirmed `/home/azureuser/alphazee/compose.prod.yml`, private `.env.production` path, the four `alphazee-prod_` named-volume mounts, three running production containers, and migration head `a81f92c6d430`. Backup target `alphazeestaging/alphazee-backups` is private and accessible. A real backup restored 42 tables and verified 4 ready assets; genuine restore proof exists. Production serves `d39e86c5d708f907a0431351aeac99979014db5f`; both public release markers and host state match, readiness is connected, and CI/deployment succeeded. Product smoke probe is `ttt`. Checkout is now enabled, test mode false, COD available; temporary confirmed delivery is All Pakistan / PKR 200. CI expectations and the active environment snapshot match. See `.context/live_checkout_activation.md` and `.context/cicd_deployment_repair.md`.

Do not guess volume names from the project name. Do not replace existing host configuration or live source changes before reconciling them. `ops/host-config.example.json` intentionally refuses deployment while volume/storage/product placeholders remain.
