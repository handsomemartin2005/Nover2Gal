from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sys
import time
from urllib.parse import urlparse
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "frontend" / "assets" / "procurement_catalog.json"
ALLOWED_HOSTS = {
    "booth": {"booth.pm"},
    "otologic": {"otologic.jp"},
    "kenney": {"kenney.nl"},
    "freesound": {"freesound.org"},
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Novel2Gal's curated asset procurement catalog.")
    parser.add_argument("--network", action="store_true", help="Fetch every source URL and check platform license markers.")
    args = parser.parse_args()

    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    minimum = int(catalog.get("minimum_items_per_group", 12))
    errors: list[str] = []
    entries: list[tuple[str, str, str, str]] = []
    seen: set[tuple[str, str, str]] = set()

    for platform in catalog.get("platforms", []):
        platform_id = str(platform.get("id") or "")
        if platform_id not in ALLOWED_HOSTS:
            errors.append(f"unsupported platform: {platform_id!r}")
        for group in platform.get("groups", []):
            group_id = str(group.get("id") or "")
            items = group.get("items") or []
            if len(items) < minimum:
                errors.append(f"{platform_id}/{group_id}: expected at least {minimum} items, found {len(items)}")
            for item in items:
                title = str(item.get("title") or "").strip()
                url = str(item.get("url") or "").strip()
                key = (platform_id, group_id, title.casefold())
                if not title:
                    errors.append(f"{platform_id}/{group_id}: item title is empty")
                if key in seen:
                    errors.append(f"{platform_id}/{group_id}: duplicate title {title!r}")
                seen.add(key)
                parsed = urlparse(url)
                if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS.get(platform_id, set()):
                    errors.append(f"{platform_id}/{group_id}/{title}: invalid source URL {url!r}")
                entries.append((platform_id, group_id, title, url))

    if args.network:
        with ThreadPoolExecutor(max_workers=12) as pool:
            for error in pool.map(check_source, entries):
                if error:
                    errors.append(error)

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(f"Catalog OK: {len(entries)} items across {sum(len(p.get('groups', [])) for p in catalog['platforms'])} groups.")
    return 0


def check_source(entry: tuple[str, str, str, str]) -> str | None:
    platform_id, group_id, title, url = entry
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            request = Request(url, headers={"User-Agent": "Mozilla/5.0 Novel2Gal catalog verifier"})
            with urlopen(request, timeout=25) as response:
                status = response.status
                body = response.read(500_000).decode("utf-8", "ignore").lower()
            break
        except Exception as exc:  # transient TLS/rate-limit failures are retried before reporting
            last_error = exc
            if attempt < 2:
                time.sleep(0.5 * (attempt + 1))
    else:
        return f"{platform_id}/{group_id}/{title}: {type(last_error).__name__}: {last_error}"
    if status != 200:
        return f"{platform_id}/{group_id}/{title}: HTTP {status}"
    if platform_id == "freesound" and not any(marker in body for marker in ("creative commons 0", "/publicdomain/zero/", "cc0")):
        return f"{platform_id}/{group_id}/{title}: CC0 marker not found"
    if platform_id == "kenney" and "cc0" not in body:
        return f"{platform_id}/{group_id}/{title}: CC0 marker not found"
    if platform_id == "otologic" and not any(marker in body for marker in ("cc by 4.0", "creativecommons.org/licenses/by/4.0")):
        return f"{platform_id}/{group_id}/{title}: CC BY 4.0 marker not found"
    return None


if __name__ == "__main__":
    raise SystemExit(main())
