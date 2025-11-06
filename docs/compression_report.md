# HTTP Compression Report

## Environment Detection
- Reverse proxy: nginx
- Application server: daphne
- Static pre-compression script: True

## Implementation Decisions
- Dynamic responses are compressed at the reverse proxy using **gzip** at level 5.
- Static assets are pre-compressed during the build/entrypoint phase using `scripts/precompress_static.py` with gzip level 5. Brotli output is temporarily disabled until the upstream Nginx module is upgraded.
- Pre-compressed assets are served directly by Nginx via `gzip_static on` inside the static and SPA locations. Brotli lookup is commented out everywhere to avoid loading the broken module.
- The backend is shielded from `Accept-Encoding` to avoid double compression.

## MIME Types Included
### gzip_types
  - text/plain
  - text/css
  - text/csv
  - application/json
  - application/javascript
  - application/xml
  - application/rss+xml
  - application/ld+json
  - application/vnd.ms-fontobject
  - application/x-font-ttf
  - font/opentype
  - image/svg+xml

Binary asset families (images, audio, video, archives, PDFs) are intentionally excluded from both runtime and pre-compression to avoid redundant CPU work and incompatibly compressed payloads.

## Cache & Header Policy
- Static assets: `expires 7d` plus `Vary: Accept-Encoding` for correct caching (detected: enabled).
- SPA frontend: served with `Vary: Accept-Encoding` to ensure CDN/browser caches differentiate encoding.
- API responses inherit `Vary: Accept-Encoding` from the proxy and disable upstream compression via `proxy_set_header Accept-Encoding ""`.

## Validation Steps
1. Deploy the stack and run `docker compose logs nginx` to ensure gzip loads without errors. (Brotli is disabled, so related warnings can be ignored.)
2. Request a static asset: `curl -I -H 'Accept-Encoding: gzip' https://<host>/static/<asset>` and confirm `Content-Encoding: gzip`.
3. Request an API endpoint: `curl -I -H 'Accept-Encoding: gzip' https://<host>/api/...` and confirm `Content-Encoding: gzip` with reduced `Content-Length` compared to `curl -H 'Accept-Encoding: identity'`.
4. Monitor application metrics to ensure TTFB remains stable (CPU utilisation should remain within baseline).

## Rollback Plan
- Disable compression in Nginx by setting `gzip off;` followed by a container reload (`docker compose restart nginx`).
- Skip static pre-compression by exporting `SKIP_STATIC_PRECOMPRESS=1` before running the entrypoint (or comment the call) and redeploy.
- If issues persist, revert this commit and redeploy the previous Docker images.
