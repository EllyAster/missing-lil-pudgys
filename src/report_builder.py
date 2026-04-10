from __future__ import annotations
import csv
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .models import ImageFetchResult, ListingStatus, TokenResult

logger = logging.getLogger(__name__)

_CSV_FIELDS = [
    "token_id",
    "image_downloaded",
    "image_path",
    "buyable",
    "price",
    "currency",
    "listing_source",
    "listing_url",
    "status",
    "error",
]


def merge_results(
    image_results: list[ImageFetchResult],
    listing_results: list[ListingStatus],
) -> list[TokenResult]:
    """Merge image fetch and listing results into unified TokenResult objects."""
    listing_map: dict[int, ListingStatus] = {r.token_id: r for r in listing_results}

    merged: list[TokenResult] = []
    for img in image_results:
        ls = listing_map.get(img.token_id)
        merged.append(
            TokenResult(
                token_id=img.token_id,
                image_downloaded=img.downloaded,
                image_path=img.path,
                image_error=img.error,
                buyable=ls.buyable if ls else None,
                price=ls.price if ls else None,
                currency=ls.currency if ls else None,
                listing_source=ls.listing_source if ls else None,
                listing_url=ls.url if ls else None,
                listing_error=ls.error if ls else None,
            )
        )
    return merged


def _result_to_row(r: TokenResult) -> dict:
    return {
        "token_id": r.token_id,
        "image_downloaded": r.image_downloaded,
        "image_path": r.image_path or "",
        "buyable": "" if r.buyable is None else r.buyable,
        "price": r.price or "",
        "currency": r.currency or "",
        "listing_source": r.listing_source or "",
        "listing_url": r.listing_url or "",
        "status": r.status,
        "error": r.error or "",
    }


def write_reports(
    results: list[TokenResult],
    out_dir: Path,
    provider: str = "opensea",
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    # --- report.json ---
    report = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "input_count": len(results),
        "provider": provider,
        "results": [
            {
                "token_id": r.token_id,
                "image_path": r.image_path,
                "image_downloaded": r.image_downloaded,
                "buyable": r.buyable,
                "listing_source": r.listing_source,
                "listing_url": r.listing_url,
                "price": r.price,
                "currency": r.currency,
                "status": r.status,
                "error": r.error,
            }
            for r in results
        ],
    }
    json_path = out_dir / "report.json"
    json_path.write_text(json.dumps(report, indent=2))
    logger.info("Wrote %s", json_path)

    # --- report.csv ---
    csv_path = out_dir / "report.csv"
    _write_csv(csv_path, results)
    logger.info("Wrote %s", csv_path)

    # --- buyable_only.csv / buyable_only.json ---
    buyable = [r for r in results if r.buyable is True]
    buyable_csv = out_dir / "buyable_only.csv"
    _write_csv(buyable_csv, buyable)
    logger.info("Wrote %s (%d buyable)", buyable_csv, len(buyable))

    buyable_report = {
        "generated_at": report["generated_at"],
        "provider": provider,
        "buyable_count": len(buyable),
        "results": [
            {
                "token_id": r.token_id,
                "price": r.price,
                "currency": r.currency,
                "listing_url": r.listing_url,
            }
            for r in buyable
        ],
    }
    buyable_json = out_dir / "buyable_only.json"
    buyable_json.write_text(json.dumps(buyable_report, indent=2))
    logger.info("Wrote %s", buyable_json)


def _write_csv(path: Path, results: list[TokenResult]) -> None:
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=_CSV_FIELDS)
        writer.writeheader()
        for r in results:
            writer.writerow(_result_to_row(r))


def print_summary(results: list[TokenResult]) -> None:
    total = len(results)
    downloaded = sum(1 for r in results if r.image_downloaded)
    buyable = sum(1 for r in results if r.buyable is True)
    unknown = sum(1 for r in results if r.buyable is None)

    print()
    print("=" * 50)
    print(f"  Total IDs processed : {total}")
    print(f"  Images downloaded   : {downloaded}/{total}")
    print(f"  Buyable now         : {buyable}")
    print(f"  Unknown (API/auth)  : {unknown}")
    print("=" * 50)
