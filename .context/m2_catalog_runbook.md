# Phase M2 — catalog lifecycle and owner APIs

Implemented 2026-10-14. Development revision: `e15a9c2b7046`.
Normal dashboard: **http://localhost:13000/admin**. No default owner was created.

## `/admin` correction

The running Docker Vite process returned an old transformed `main.js` that always
loaded the storefront, despite the updated file on disk. Restarting web restored
the current module. `VITE_USE_POLLING=true` is now set in development Compose;
Vite polls the Windows bind-mounted source every 250ms so subsequent edits are
detected. The normal source module and actual login screen were rechecked.
Fresh anonymous access shows login without falsely reporting a session expiry.

Start/recreate the normal stack using:

```powershell
docker compose --env-file .env.docker.local up --build --wait -d
```

For an account you have not provisioned yet, choose your own username/password:

```powershell
docker compose --env-file .env.docker.local exec api python scripts/provision_owner.py YOUR_USERNAME
```

Add `--reset-password` only when intentionally resetting an existing account.
Open `/admin` again after the updated web service starts; ordinary page reload
loads the repaired entry point. No environment file or database was reset.

## Delivered catalog behavior

- Empty drafts support missing title, slug, collection, media and variants.
  Description, short description, material/care/sizing and hero placement are
  editable through authenticated owner APIs. IDs remain stable on rename.
- Variant editing uses IDs and retains omitted rows; new variants require unique
  SKU/options. Inactive variants may have null price; activation requires price.
  Currency writes are strict integer paisas. `parseCatalogPkr` converts decimal
  PKR text exactly for future editor inputs, bounded by the existing INTEGER.
- Product/collection edits carry `expected_version`. Locked version checks reject
  stale/concurrent edits with 409. Duplicate slug/SKU/options return actionable
  conflict fields; failed edits roll back together.
- Products can publish/unpublish/archive/restore. Archived products are read-only
  until restored to draft. Publication returns all missing requirements; new
  products cannot bypass the media guard by submitting a URL/legacy flag.
- Existing products preserve active/inactive visibility and legacy image URLs.
  Publication state is authoritative in public queries and new-order validation;
  stale carts/direct service calls cannot order hidden products. Existing pending
  orders, allocation history, prices/cost snapshots, returns and reports remain
  intact. Product/variant cascade deletion and collection orphaning are blocked.
- Collections support create/edit, activation/deactivation and versioned full-list
  reordering. Public responses exclude owner editing/version/stock-cost data.
- Owner inventory/supplier mapping lists handle untitled drafts without failing.
  No product edit writes inventory balances or alters reservations.
- Frontend owner API helpers are ready for M4; structured API error messages are
  retained instead of displaying `[object Object]`.

**Boundary:** this phase delivers APIs, not the M4 product/collection editor.
Those dashboard sections remain honest placeholders. Media upload/ready-asset
validation belongs to **M3**. Newly created products therefore cannot publish
until a ready primary image exists; no temporary URL bypass was introduced.

## Owner endpoints

All are under `/api/v1/admin`, require the existing owner session, and require
trusted Origin/CSRF on writes. No hard-delete catalog endpoint exists.

| Endpoint | Use |
| --- | --- |
| `GET/POST /products` | Search/filter/paginate all owner statuses; create draft |
| `GET/POST /products/{id}` | Read detail or versioned partial edit; variants update by ID |
| `POST /products/{id}/publish`, `/unpublish`, `/archive`, `/restore` | Explicit lifecycle command with expected version |
| `GET/POST /collections` | List/create collections |
| `POST /collections/{id}` | Versioned edit and active-state management |
| `POST /collections/reorder` | Complete unique ID/version list in desired order |

A new variant example is `{"sku":"YOUR-SKU","size":"M","color":"Black",
"price_minor":345050,"is_active":true}`: PKR 3,450.50. No price means null,
not zero. On product edit, omitted fields/variants are preserved. These contracts
are wired into the API client; normal dashboard authoring arrives in M4.

## Executed verification and data preservation

| Check | Result |
| --- | --- |
| Full backend suite | 218 passed; one existing Starlette/AnyIO warning |
| Final focused catalog checks | 17 passed after untitled-draft display and loaded-collection deletion refinements |
| Frontend suite/build | 88 passed; production bundle passed |
| PostgreSQL edit contention | Separate sessions with expected version 1: one saved, one conflict; test fixture cleaned its committed rows |
| Historical migration fixtures | Upgrade/backfill/downgrade/re-upgrade passed; active/inactive states, legacy image and order snapshots retained; referenced product deletion rejected; incomplete-draft downgrade refused; Alembic check passed |
| Development rollout | Fresh private backup restored and compared first; forward upgrade only; table counts and noncatalog row digests preserved; Alembic check passed; no SAMPLE data inserted |
| Browser | 15 Chrome checks passed: isolated auth/navigation plus draft API creation/exact price/publication guard, and the actual normal `/admin` login separately; evidence in `m2_browser_verification.json` |
| Docker | API/migration images rebuilt; full development stack reached healthy; production API/migration/web images built successfully without deployment |

Evidence: `owner_catalog_migration_verification.json`,
`m2_pre_migration_backup.json`, `m2_development_verification.json`,
`m2_browser_verification.json`. The private archive is under `.local/backups`;
the retained restore is `alphazee_m2_restore_949d78efca08_test`. Never use that
private clone for browser fixtures. Browser fixtures are generated separately.

Final browser database: `alphazee_m2_browser_60a191b51e_test`.
Inspected login screenshot: `.local/m2-browser/89a4776e36/normal-admin-login.png`.

Verification commands from the repository root:

```powershell
backend\.venv\Scripts\python.exe backend/scripts/verify_m2_migration.py
backend\.venv\Scripts\python.exe -m pytest backend/tests -q -p no:cacheprovider --tb=short
backend\.venv\Scripts\python.exe backend/scripts/verify_m1_browser.py --phase-m2
```

Run frontend tests/build in `frontend`. `apply_m2_development.py` is a guarded,
forward-only rollout tool for the prior revision; do not rerun it on an already
upgraded database. It reuses the baseline backup verifier with separate M2
evidence filenames, preserving M0 reports. Downgrade is only verified on a
disposable target and refuses incomplete drafts rather than inventing values.
Public checkout and production deployment remain disabled/out of scope.
