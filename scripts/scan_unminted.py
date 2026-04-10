"""
Scan every Lil Pudgy ID (0–22221) and record the ones whose metadata
endpoint returns 404 (i.e. not yet minted).

Writes results to:
  sample_data/missing_ids.txt   (one ID per line, sorted)

Usage:
  python3 scripts/scan_unminted.py [--concurrency N] [--output PATH]
"""
from __future__ import annotations
import argparse
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import urllib.request
import urllib.error

TOTAL = 22_222          # IDs 0 .. 22_221
BASE_URL = "https://api.pudgypenguins.io/lil/{id}"
DEFAULT_CONCURRENCY = 30
DEFAULT_OUTPUT = Path(__file__).parent.parent / "sample_data" / "missing_ids.txt"


def check_id(token_id: int, timeout: int = 15) -> bool:
    """Return True if the token is unminted (404), False if it exists (200)."""
    url = BASE_URL.format(id=token_id)
    req = urllib.request.Request(url, headers={"User-Agent": "missing-lil-pudgys-scanner/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout):
            return False        # minted
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return True         # unminted
        # Any other HTTP error: treat as unknown / skip
        print(f"  WARNING: ID {token_id} returned HTTP {exc.code}", flush=True)
        return False
    except Exception as exc:
        print(f"  WARNING: ID {token_id} error: {exc}", flush=True)
        return False


def scan(concurrency: int) -> list[int]:
    missing: list[int] = []
    done = 0
    start = time.time()

    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = {pool.submit(check_id, tid): tid for tid in range(TOTAL)}
        for future in as_completed(futures):
            tid = futures[future]
            if future.result():
                missing.append(tid)
            done += 1
            if done % 500 == 0 or done == TOTAL:
                elapsed = time.time() - start
                rate = done / elapsed
                remaining = (TOTAL - done) / rate if rate > 0 else 0
                print(
                    f"  {done}/{TOTAL} checked | {len(missing)} missing so far"
                    f" | {elapsed:.0f}s elapsed | ~{remaining:.0f}s remaining",
                    flush=True,
                )

    missing.sort()
    return missing


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan unminted Lil Pudgy IDs")
    parser.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY)
    parser.add_argument("--output", type=str, default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()

    print(f"Scanning {TOTAL} Lil Pudgy IDs with {args.concurrency} workers…")
    missing = scan(args.concurrency)

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(str(i) for i in missing) + "\n")

    elapsed = 0  # already printed during scan
    print(f"\nFound {len(missing)} unminted IDs.")
    print(f"Written to {out.resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
