# What went wrong with CI/CD? A simple explanation

CI/CD is our automatic delivery system for code changes. **CI checks the code. CD sends the checked version to the live server.** A website can pass its code tests and still fail to update if the server is missing something it needs.

Think of it like delivering a parcel: checking the parcel is useful, but the delivery also needs the correct address, a working vehicle and permission to enter the building.

## What happened

Your changes passed the frontend tests, backend tests and image builds. That meant the code was ready to attempt deployment. The failure happened later, when the deployment reached the Azure VM.

We found several separate problems, one after another:

| Problem | Simple meaning | What fixed it |
| --- | --- | --- |
| Azure login initially failed | Azure did not recognize GitHub's exact identity. The identity now includes permanent account/repository numbers. | You corrected the Azure trust setting. We also updated the setup script so it uses the confirmed identity. |
| Azure CLI was missing on the VM | The server did not have the `az` program needed to upload backups. Installing it on GitHub's runner does not install it on the VM. They are separate machines. | I installed Azure CLI on the VM. |
| The VM had no managed identity | The VM had no Azure identity of its own to access the backup container. GitHub's deployment identity is a different identity. | You enabled the VM identity and gave it access to the private backup container. |
| Restore proof was missing | We had no recorded evidence that a real backup could be restored. The deployment refused to continue. | We created a real backup, restored it in isolation, verified 42 tables and 4 media files, and only then generated proof. |
| A deployment command used an invalid option | `docker compose run --no-build` is not a supported command. This was a bug in our deployment script. | I changed it to the supported `--pull never` command. |
| The product health check used the wrong slug | The server tried to open a product called `catalog`, but that product did not exist. A slug is the final identifying part of a product URL. | I changed the probe to the real available product `ttt`. |

## Why did this happen after CI/CD was already set up?

The first implementation provided the workflows and scripts. The live server still needed its own configuration: programs, identities, permissions and real backup evidence. Writing the automation and preparing the actual server are both necessary.

Some earlier tests checked the deployment logic using simulated command results. Those tests were useful for checking things such as “do not deploy if backup fails.” But a simulated Docker command cannot prove that the installed Docker CLI accepts every option. **That gap allowed the invalid command to pass. It was our testing gap, not something you did wrong when committing.**

The wrong product slug was another server-configuration problem. Good application code cannot make a nonexistent product URL return a real product.

## How I investigated it

1. Read your error report and checked the relevant deployment code.
2. Connected to the actual VM through the SSH access you provided. I did not change its database records or reset accounts.
3. Checked which programs and permissions existed on the VM, rather than assuming the setup instructions had all been completed.
4. Installed the missing program and verified the identity/storage access after your Cloud Shell changes.
5. Made an off-host backup of the database and media from the same paused moment, then resumed the API.
6. Restored that backup into a temporary PostgreSQL container with no network access. Checked the database revision and every ready media file's size and SHA-256 checksum. A checksum is a file fingerprint: matching fingerprints confirm matching file content.
7. Retried deployment, found the invalid Docker option, and corrected it.
8. Added a test that actually runs the production migration command against a new disposable database. Added a real restore test too.
9. Sent the repair through PR #13. Waited for checks to pass, merged it, and monitored the automatic deployment.
10. Corrected the bad product probe after the health check rejected it. The system restored the previous images during that failed attempt.
11. Verified the successful rollout independently: frontend and API both reported `d39e86c`, the database was connected, and the main public routes responded correctly.

## What is better now?

- Missing programs and proof files produce clearer errors instead of an unhelpful generic message.
- CI executes the real migration command, so this invalid-option bug is caught before a live rollout.
- Backup restore tests check actual PostgreSQL restoration and media fingerprints.
- Deployment uses the exact published image versions, so we can identify what is running.
- Failed health checks prevent a release being recorded as successful. Compatible previous images can be restored without undoing customer orders or rolling back the database.

These checks reduce mistakes; they cannot guarantee that no future bug will ever occur. Future server changes, expired permissions, deleted probe products or incompatible database migrations still need attention.

## Why was checkout still disabled?

**Updating code and allowing orders are separate decisions.** CI/CD updates the software. The production checkout switch controls whether the shop accepts orders. Leaving that switch off helped prevent accidental orders while hosting and deployment were being checked.

Turning it on uses the existing production checkout code; it does not require changing the whole app or putting production into test mode. Checkout on the live website creates real order records and can reserve real stock. Sharing the link only with friends does not make the site invite-only.

**Now enabled, at your request:** production checkout is open with Cash on Delivery. You confirmed All Pakistan delivery at PKR 200, with no free-shipping threshold for now. The live checkout form and a real shipping quote were verified without placing an order. See [the activation record and how to change courier rates](live_checkout_activation.md).

Detailed repair evidence: [deployment repair report](cicd_deployment_repair.md). Successful workflow: [GitHub Actions run](https://github.com/syednajam01/AlphaZee/actions/runs/42429689050).
