#!/usr/bin/env python3
"""Pre-compress static assets with Brotli and gzip."""
from __future__ import annotations

import argparse
import gzip
import os
from pathlib import Path
import sys
import time
from typing import Iterable, Tuple

import brotli

COMPRESSIBLE_EXTENSIONS = {
    ".css",
    ".csv",
    ".eot",
    ".htm",
    ".html",
    ".ics",
    ".js",
    ".json",
    ".mjs",
    ".otf",
    ".rdf",
    ".sitemap",
    ".svg",
    ".ttf",
    ".txt",
    ".webmanifest",
    ".woff",
    ".woff2",
    ".xml",
}

BINARY_EXTENSIONS = {
    ".avif",
    ".gif",
    ".heic",
    ".heif",
    ".ico",
    ".jpeg",
    ".jpg",
    ".mp3",
    ".mp4",
    ".ogg",
    ".pdf",
    ".png",
    ".webp",
    ".zip",
}

DEFAULT_GZIP_LEVEL = 5
DEFAULT_BROTLI_LEVEL = 5


def iter_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*"):
        if path.is_file():
            yield path


def should_compress(path: Path, include_binary: bool = False) -> bool:
    suffix = path.suffix.lower()
    if suffix in {".gz", ".br"}:
        return False
    if suffix in BINARY_EXTENSIONS and not include_binary:
        return False
    if suffix in COMPRESSIBLE_EXTENSIONS:
        return True
    # Assume small JSON-like files inside directories without extension shouldn't be compressed.
    return False


def needs_regeneration(source: Path, target: Path) -> bool:
    if not target.exists():
        return True
    return source.stat().st_mtime > target.stat().st_mtime


def compress_gzip(source: Path, target: Path, level: int) -> None:
    with source.open("rb") as src, gzip.open(target, "wb", compresslevel=level) as dst:
        while True:
            chunk = src.read(1024 * 64)
            if not chunk:
                break
            dst.write(chunk)


def compress_brotli(source: Path, target: Path, level: int) -> None:
    compressor = brotli.Compressor(quality=level, mode=brotli.MODE_GENERIC)
    with source.open("rb") as src, target.open("wb") as dst:
        while True:
            chunk = src.read(1024 * 64)
            if not chunk:
                dst.write(compressor.finish())
                break
            dst.write(compressor.process(chunk))


def human_size(num_bytes: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if num_bytes < 1024.0:
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.1f} TB"


def process_file(path: Path, brotli_level: int, gzip_level: int, dry_run: bool) -> Tuple[int, int]:
    brotli_target = path.with_suffix(path.suffix + ".br")
    gzip_target = path.with_suffix(path.suffix + ".gz")
    brotli_saving = gzip_saving = 0

    if needs_regeneration(path, brotli_target):
        if dry_run:
            pass
        else:
            compress_brotli(path, brotli_target, brotli_level)
        brotli_saving = max(path.stat().st_size - brotli_target.stat().st_size, 0) if brotli_target.exists() else 0

    if needs_regeneration(path, gzip_target):
        if dry_run:
            pass
        else:
            compress_gzip(path, gzip_target, gzip_level)
        gzip_saving = max(path.stat().st_size - gzip_target.stat().st_size, 0) if gzip_target.exists() else 0

    return brotli_saving, gzip_saving


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "root",
        nargs="?",
        default=os.environ.get("STATIC_ROOT", "staticfiles"),
        help="Path to the directory containing collected static files (default: STATIC_ROOT or ./staticfiles)",
    )
    parser.add_argument("--brotli-level", type=int, default=DEFAULT_BROTLI_LEVEL, help="Brotli compression level (default: 5)")
    parser.add_argument("--gzip-level", type=int, default=DEFAULT_GZIP_LEVEL, help="Gzip compression level (default: 5)")
    parser.add_argument("--dry-run", action="store_true", help="Report what would be compressed without writing files")
    parser.add_argument(
        "--include-binary",
        action="store_true",
        help="Compress binary formats as well (disabled by default)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_argument_parser()
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()

    if not root.exists():
        parser.error(f"Static root '{root}' does not exist. Run collectstatic before compressing.")

    brotli_total = gzip_total = files_processed = 0
    start = time.perf_counter()

    for path in iter_files(root):
        if not should_compress(path, include_binary=args.include_binary):
            continue
        files_processed += 1
        before_size = path.stat().st_size
        brotli_saving, gzip_saving = process_file(path, args.brotli_level, args.gzip_level, args.dry_run)
        brotli_total += brotli_saving
        gzip_total += gzip_saving
        if args.dry_run:
            sys.stdout.write(f"Would compress {path} ({human_size(before_size)})\n")

    duration = time.perf_counter() - start
    sys.stdout.write(
        "Processed {files} files in {duration:.2f}s | Brotli saved {brotli} | gzip saved {gzip}\n".format(
            files=files_processed,
            duration=duration,
            brotli=human_size(brotli_total),
            gzip=human_size(gzip_total),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
