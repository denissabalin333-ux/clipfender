# ClipFender — automatic character portrait discovery

ClipFender can now grow the character catalog from explicit character requests without putting unverified placeholders into the public catalog.

## Flow

1. Existing `CHARACTER_PROFILES` entries are returned immediately.
2. A new character request is atomically marked `pending` in SQLite so concurrent requests cannot trigger duplicate paid generations.
3. If Bing Image Search is configured, ClipFender evaluates large photo results first. Downloads are allowed only from hosts explicitly listed in `CHARACTER_IMAGE_SEARCH_ALLOWED_HOSTS`.
4. Every downloaded/generated image is validated with Pillow: image type, minimum dimensions, byte size and a basic edge-detail quality check are evaluated before the asset is saved.
5. If no acceptable web image is found, OpenAI image generation is used when enabled and `OPENAI_API_KEY` is configured.
6. The final WebP is saved under `CHARACTER_STORAGE_DIR/<slug>-hq.webp` and the profile is persisted in SQLite.
7. Until a real asset passes validation, the character remains hidden from the public catalog.

## Recommended production configuration

Set `OPENAI_API_KEY` for the automatic generation fallback and keep `CHARACTER_IMAGE_SEARCH_ENABLED=0`. The active production path uses the OpenAI Images API and a persistent character storage directory.

## Cost and abuse guardrails

- `CHARACTER_DISCOVERY_RATE_LIMIT` limits automatic discovery per IP.
- `CHARACTER_GENERATION_DAILY_GUARD` limits paid image-generation calls per UTC day.
- Failed/low-quality images are never added to the public catalog.
- Duplicate concurrent requests for the same slug are coalesced by the SQLite `pending` state.

For Render, the Blueprint mounts a persistent disk at `/var/lib/clipfender`; SQLite and generated portrait assets are stored under that mount so the growing catalog survives restarts/redeploys. Render documents that persistent disks require a paid service and only preserve data written under the mount path.
