#!/usr/bin/env python3
"""Analyse the deployment topology and document the compression setup."""
from __future__ import annotations

import argparse
import re
from pathlib import Path
from textwrap import dedent

REQUIRED_FILES = [
    Path("docker-compose.yml"),
    Path("nginx/nginx.conf"),
    Path("docker-entrypoint.sh"),
]


def detect_reverse_proxy(compose_text: str) -> str | None:
    match = re.search(r"^\s*nginx:\s*$", compose_text, flags=re.MULTILINE)
    return "nginx" if match else None


def detect_app_server(entrypoint_text: str) -> str | None:
    if "daphne" in entrypoint_text:
        return "daphne"
    if "gunicorn" in entrypoint_text:
        return "gunicorn"
    if "uvicorn" in entrypoint_text:
        return "uvicorn"
    return None


def extract_level(config: str, directive: str, default: str) -> str:
    pattern = rf"{directive}\s+(\d+);"
    match = re.search(pattern, config)
    if match:
        return match.group(1)
    return default


def extract_types(config: str, directive: str) -> list[str]:
    lines = config.splitlines()
    collecting = False
    values: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not collecting:
            if stripped.startswith(directive):
                remainder = stripped[len(directive):].strip()
                if remainder.endswith(";"):
                    remainder = remainder[:-1].strip()
                if remainder:
                    values.extend(remainder.split())
                collecting = True
            continue
        if stripped.endswith(";"):
            stripped = stripped[:-1].strip()
            if stripped:
                values.append(stripped)
            break
        if stripped:
            values.append(stripped)
    return values


def has_vary_header(config: str) -> bool:
    return "add_header Vary Accept-Encoding" in config


def render_report(data: dict[str, object]) -> str:
    gzip_types = "\n".join(f"  - {mime}" for mime in data["gzip_types"]) or "  - (none detected)"
    brotli_types = "\n".join(f"  - {mime}" for mime in data["brotli_types"]) or "  - (none detected)"

    report = f"""# HTTP Compression Report

## Environment Detection
- Reverse proxy: {data['reverse_proxy'] or 'not detected'}
- Application server: {data['app_server'] or 'not detected'}
- Static pre-compression script: {data['precompress_script']}

## Implementation Decisions
- Dynamic responses are compressed at the reverse proxy using **gzip** at level {data['gzip_level']}.
- Static assets are pre-compressed during the build/entrypoint phase using `scripts/precompress_static.py` with Brotli level {data['brotli_level']} and gzip level {data['gzip_level']}.
- Pre-compressed assets are served directly by Nginx via `gzip_static on` and `brotli_static on`.
- The backend is shielded from `Accept-Encoding` to avoid double compression.

## MIME Types Included
### gzip_types
{gzip_types}

### brotli_types
{brotli_types}

Binary asset families (images, audio, video, archives, PDFs) are intentionally excluded from both runtime and pre-compression to avoid redundant CPU work and incompatibly compressed payloads.

## Cache & Header Policy
- Static assets: `expires 7d` plus `Vary: Accept-Encoding` for correct caching (detected: {"enabled" if data['vary_header'] else "missing"}).
- SPA frontend: served with `Vary: Accept-Encoding` to ensure CDN/browser caches differentiate encoding.
- API responses inherit `Vary: Accept-Encoding` from the proxy and disable upstream compression via `proxy_set_header Accept-Encoding ""`.

## Validation Steps
1. Deploy the stack and run `docker compose logs nginx` to ensure the Brotli modules load without errors.
2. Request a static asset: `curl -I -H 'Accept-Encoding: br' https://<host>/static/<asset>` and confirm `Content-Encoding: br`.
3. Request an API endpoint: `curl -I -H 'Accept-Encoding: gzip' https://<host>/api/...` and confirm `Content-Encoding: gzip` with reduced `Content-Length` compared to `curl -H 'Accept-Encoding: identity'`.
4. Monitor application metrics to ensure TTFB remains stable (CPU utilisation should remain within baseline).

## Rollback Plan
- Disable compression in Nginx by setting `gzip off;` and `brotli off;` followed by a container reload (`docker compose restart nginx`).
- Skip static pre-compression by exporting `SKIP_STATIC_PRECOMPRESS=1` before running the entrypoint (or comment the call) and redeploy.
- If issues persist, revert this commit and redeploy the previous Docker images.
"""
    return dedent(report)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        default=Path("docs/compression_report.md"),
        type=Path,
        help="Where to write the Markdown report.",
    )
    args = parser.parse_args()

    for path in REQUIRED_FILES:
        if not path.exists():
            raise SystemExit(f"Required file '{path}' not found; run from repository root.")

    compose_text = Path("docker-compose.yml").read_text(encoding="utf-8")
    nginx_config = Path("nginx/nginx.conf").read_text(encoding="utf-8")
    entrypoint_text = Path("docker-entrypoint.sh").read_text(encoding="utf-8")

    data = {
        "reverse_proxy": detect_reverse_proxy(compose_text),
        "app_server": detect_app_server(entrypoint_text),
        "gzip_level": extract_level(nginx_config, "gzip_comp_level", "unknown"),
        "brotli_level": extract_level(nginx_config, "brotli_comp_level", "unknown"),
        "gzip_types": extract_types(nginx_config, "gzip_types"),
        "brotli_types": extract_types(nginx_config, "brotli_types"),
        "vary_header": has_vary_header(nginx_config),
        "precompress_script": Path("scripts/precompress_static.py").exists(),
    }

    report = render_report(data)
    output_path: Path = args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    print(f"Compression report written to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
