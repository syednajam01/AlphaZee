# Temporary media preview — 2026-11-05

The owner requested temporary use of files from `F:\ai videos` and `F:\Trend\img` on the running local site. This explicitly authorizes this preview in development; it is not a general permission to seed development with test fixtures.

Open http://localhost:13000 or http://localhost:13000/products/temporary-media-preview-20261105.

- Three photos and `smiling.mp4` were imported through the existing validated media service into durable media storage. Source files were not edited or moved.
- Created one **Temporary Media Preview** collection/product, with primary/hover photos, a third photo and a video with poster. Price zero is explicitly a placeholder; variant is unavailable, physical stock stays zero, and checkout stays closed.
- Added a two-slide hero playlist: muted video followed by a photo. Previous hero slides were disabled, preserved and snapshotted. Existing products, accounts and orders were not modified.
- HTTP checks passed for public product data, distinct hover image, all four media checksums/content types, video byte ranges and product route. Visual playback was not browser-tested.

Private working copies, original hero snapshot, created IDs, import/restore helpers and evidence: `.local/temporary-media-preview/`. Keep the manifest until restoration. Do not commit the personal media files.

To restore, copy that directory to the current API container, ensure its application user owns the temporary folder, then run the helper:

```powershell
docker compose --env-file .env.docker.local cp .local/temporary-media-preview api:/tmp/temporary-media-preview
docker compose --env-file .env.docker.local exec -T --user root api chown -R app:app /tmp/temporary-media-preview
docker compose --env-file .env.docker.local exec -T api python /tmp/temporary-media-preview/restore_preview.py
docker compose --env-file .env.docker.local cp api:/tmp/temporary-media-preview/manifest.json .local/temporary-media-preview/manifest.json
```

Restore archives the preview product, hides its collection, disables its hero slides and re-enables the former playlist. It refuses to overwrite subsequent edits. Uploaded assets remain in the admin media library; originals remain in the owner's folders. Restore has been prepared, not executed, so the preview is currently visible.
