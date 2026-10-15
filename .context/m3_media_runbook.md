# M3 managed media and durable accounts

Implemented 2026-10-15. Head: `f27b6d91c083`, after M2's `e15a9c2b7046`. The development migration followed a private, snapshot-consistent backup and a verified restore. Existing rows and the requested owner account were preserved. Production was not deployed and public checkout remains disabled.

## Storage and validation

- JPEG, PNG and static WebP: 10 MiB, 40 megapixels. Decode, validate and re-encode images to strip metadata/appended payloads. Animated images, corrupt/disguised files and unsafe filenames fail.
- H.264 MP4 and VP8/VP9 WebM: 100 MiB, 120 seconds, one video stream and optional audio. Validate container/codec/dimensions/duration with FFprobe, then decode all video frames with FFmpeg. Processing has a 15-second probe and 30-second decode deadline. Docker includes both binaries; native video uploads require them on PATH.
- Multipart bodies are bounded at 101 MiB before spooling, including chunked requests, with one file and no extra fields. Upload concurrency is bounded. Pillow 12.3.0 and python-multipart 0.0.32 were verified against their primary PyPI release metadata and pinned.
- Asset UUIDs and immutable generated filenames replace client paths. `media_assets` stores validated metadata/checksum/state/creator; `product_media` stores role/order/alt text/variant. Collection covers and video posters reference assets explicitly.
- Validation/staging occurs outside `objects`; ready metadata follows atomic rename and filesystem flush. Failed saves compensate files; uncertain commit acknowledgments retain bytes for later confirmed-orphan cleanup. Deletion tombstones first, so an unlink failure cannot expose a deleted file.
- Every mutation uses owner session, trusted Origin and CSRF. A shared transaction lock serializes attachment/deletion. Detach retains bytes; delete refuses product, collection or poster references. Published products must retain a primary image and gallery videos must retain posters.
- Public `/api/v1/media/{id}/content` supports GET/HEAD and byte ranges, fixed content types, `nosniff`, checksum ETags and immutable caching. Missing/deleted files return 404. Catalog files, including uploaded draft files, are public; payment evidence stays in its existing private order flow. Previously cached public files may remain in browser caches after deletion.

## Docker and account persistence

Both development and production APIs mount their project's named `catalog_media` volume at `/var/lib/alphazee/catalog-media`. Images initialize directories for non-root UID 10001. Normal development uses `alphazee_catalog_media` and the existing `alphazee_pgdata`; production gets its own project volumes. Native storage defaults to ignored `.local/catalog-media` and can be set with `CATALOG_MEDIA_ROOT`.

Start from the repository root:

```powershell
docker compose --env-file .env.docker.local up --build --wait -d
docker compose --env-file .env.docker.local ps
docker compose --env-file .env.docker.local exec api python scripts/cleanup_catalog_media.py
```

The cleanup command defaults to a dry run. Add `--apply` to remove only generated, unreferenced/tombstoned files older than 24 hours; active staging uploads hold per-file database locks and are skipped. Unknown files and symlinks are ignored.

The requested **syed123** account exists in the persistent development database. Its password was entered through hidden prompts and stored as a salted PBKDF2 hash; no plaintext password was added to source/configuration/documentation. An explicit `--allow-short-local-password` provisioning option permits this local choice while retaining the normal 12-character policy. These local-only credentials and sessions are rejected in production. Resetting to a normal strong password removes that local-only restriction. Owner accounts survive shutdown/restart; login sessions still expire after eight hours.

Stop with `docker compose --env-file .env.docker.local down`; this preserves volumes. Do not use `down -v` when retaining the account/catalog. Account login and the unchanged password hash were verified after restarting both PostgreSQL and the API; see `m3_owner_persistence_verification.json`.

## Matched database + media backup and restore

Take a maintenance window: stop **all API writers, import/cleanup jobs and other processes** using that database/media root. Keep PostgreSQL running. Save a `pg_dump -Fc --no-owner --no-acl` of the selected database and a tar archive of the selected `catalog_media` volume as one dated backup set. Record the Alembic revision, project/volume names and both checksums, then restart the API. A DB-only dump is insufficient once files exist.

Discover actual volume names from `docker compose ... ps -q api` / `docker compose ... ps -q db`, then `docker inspect CONTAINER_ID` and the `Mounts` entries. Archive with an API-image helper mounting that exact volume read-only, using `tar -cf /backup/media.tar -C /var/lib/alphazee/catalog-media .`; the helper must not start Uvicorn or run migrations. On PowerShell, avoid redirecting binary pg_dump output through text conversion: use `pg_dump -f` in the container and `docker cp`, or a Python subprocess writing directly to a binary file. Keep backups private/off-host.

Restore into a **new empty database and separate new media volume**, with API writers stopped: use `pg_restore --exit-on-error --no-owner --no-acl`, extract the matched archive into that volume, preserve UID 10001 ownership, and configure the API to use this pair. Verify revision/readiness, owner login, asset byte sizes/checksums, associations and video ranges before switching traffic. Never attach restored metadata to an unrelated/empty media volume or downgrade a populated managed-media schema.

Actual isolated proof used `compose.media-check.yml`: separate `alphazee_m3_media_test`, independent DB/media volumes, synthetic fixtures only. Real MP4/VP8/VP9 HTTP uploads, invalid codec/container/duration/truncation rejection, references/publication and ranges passed. All four fixture assets matched after restart, recreation and restoration of the matched database/media archive into `alphazee_m3_restore_media_test` and `alphazee-m3-restored-media`. Reports are collected in `m3_media_runtime_verification.json`; private artifacts stay in ignored `.local/m3-media-check`. This stack is an acceptance fixture, not the M8 checkout lab.

Useful isolated commands:

```powershell
docker compose -f compose.media-check.yml up --build --wait -d
docker compose -f compose.media-check.yml exec -T api python scripts/verify_m3_media_runtime.py --prepare
docker compose -f compose.media-check.yml restart api
docker compose -f compose.media-check.yml exec -T api python scripts/verify_m3_media_runtime.py --check restart
docker compose -f compose.media-check.yml down
```

`--prepare` intentionally refuses reruns after fixture preparation; use `--check` for the retained stack. Normal data never receives sample products/assets.
