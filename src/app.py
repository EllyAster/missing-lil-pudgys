"""
missing-lil-pudgys – one-shot CLI entry point.

Simplest usage (just run this):
    python run.py

With options:
    python run.py --check-buyable          # also check OpenSea listings
    python run.py --input my_ids.txt       # use a different ID list
    python -m src.app --help               # full flag reference
"""
from __future__ import annotations
import argparse
import logging
import sys
from pathlib import Path

from .utils import setup_logging

logger = logging.getLogger(__name__)

# Path to the bundled ID list, relative to the repo root.
_DEFAULT_INPUT = Path(__file__).parent.parent / "sample_data" / "missing_ids.txt"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="missing-lil-pudgys",
        description=(
            "Download missing Lil Pudgy images and check Pudgy Penguins buyability.\n\n"
            "Just run:  python run.py"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--input", "-i",
        default=str(_DEFAULT_INPUT),
        metavar="PATH",
        help=f"Token ID list (default: {_DEFAULT_INPUT}).",
    )
    parser.add_argument(
        "--output", "-o",
        default="output",
        metavar="DIR",
        help="Directory for all output files (default: output).",
    )
    parser.add_argument(
        "--download-images",
        action="store_true",
        default=True,
        help="Download preview images — on by default.",
    )
    parser.add_argument(
        "--no-download-images",
        dest="download_images",
        action="store_false",
        help="Skip image downloads.",
    )
    parser.add_argument(
        "--check-buyable",
        action="store_true",
        default=False,
        help="Check Pudgy Penguins listing status via the marketplace API.",
    )
    parser.add_argument(
        "--skip-mint-check",
        action="store_true",
        default=False,
        help=(
            "Skip the pre-flight mint check that removes already-minted IDs. "
            "Use when you trust the input list is already current."
        ),
    )
    parser.add_argument(
        "--provider",
        default="opensea",
        choices=["opensea"],
        help="Marketplace listing provider (default: opensea).",
    )
    parser.add_argument(
        "--slug",
        default="pudgypenguins",
        help="OpenSea collection slug (default: pudgypenguins).",
    )
    parser.add_argument(
        "--contract",
        default="0xBd3531dA5CF5857e7CfAA92426877b022e612cf8",
        help="Pudgy Penguins contract address.",
    )
    parser.add_argument(
        "--concurrency", "-c",
        type=int,
        default=5,
        metavar="N",
        help="Number of concurrent HTTP workers (default: 5).",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        metavar="SECONDS",
        help="HTTP request timeout in seconds (default: 30).",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=3,
        metavar="N",
        help="Number of retries for transient errors (default: 3).",
    )
    parser.add_argument(
        "--no-contact-sheet",
        action="store_true",
        default=False,
        help="Skip contact sheet generation.",
    )
    parser.add_argument(
        "--no-pdf",
        action="store_true",
        default=False,
        help="Skip PDF export of contact sheet.",
    )
    parser.add_argument(
        "--image-no-ext",
        action="store_true",
        default=False,
        help="Save images without a file extension.",
    )
    parser.add_argument(
        "--columns",
        type=int,
        default=10,
        metavar="N",
        help="Number of columns in the contact sheet grid (default: 10).",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        default=False,
        help="Enable debug logging.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    setup_logging(args.verbose)

    # --- 1. Load IDs ---
    from .input_loader import load_ids
    try:
        token_ids = load_ids(args.input)
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        return 1

    if not token_ids:
        logger.error("No valid token IDs found in %s – exiting.", args.input)
        return 1

    print(f"Loaded {len(token_ids)} ID(s) from {args.input}")

    # --- 2. Pre-flight mint check — remove IDs that have since been minted ---
    if not args.skip_mint_check:
        from .mint_checker import filter_unminted
        print(
            f"Checking which of the {len(token_ids)} listed IDs are still unminted…"
            " (pass --skip-mint-check to skip)"
        )
        token_ids, now_minted = filter_unminted(
            token_ids,
            concurrency=args.concurrency,
        )
        if now_minted:
            print(
                f"  Removed {len(now_minted)} ID(s) that have been minted since the list was built: "
                + ", ".join(str(i) for i in now_minted[:10])
                + (" …" if len(now_minted) > 10 else "")
            )
        else:
            print("  All listed IDs are still unminted.")
        print(f"  Proceeding with {len(token_ids)} still-unminted ID(s).")

        if not token_ids:
            print("Nothing left to process – all IDs have been minted. Exiting.")
            return 0
    else:
        print("Skipping mint check (--skip-mint-check).")

    out_dir = Path(args.output)
    image_dir = out_dir / "missing"

    # --- 3. Download images ---
    from .models import ImageFetchResult, ListingStatus
    image_results: list[ImageFetchResult] = []

    if args.download_images:
        from .image_fetcher import fetch_images_concurrent
        print(f"Downloading {len(token_ids)} image(s)…")
        image_results = fetch_images_concurrent(
            token_ids,
            image_dir,
            concurrency=args.concurrency,
            timeout=args.timeout,
            retries=args.retries,
            extensionless=args.image_no_ext,
        )
        downloaded = sum(1 for r in image_results if r.downloaded)
        print(f"Downloaded {downloaded}/{len(token_ids)} images.")
    else:
        image_results = [
            ImageFetchResult(
                token_id=tid,
                downloaded=False,
                error="skipped (--download-images not set)",
            )
            for tid in token_ids
        ]

    # --- 4. Check listing status ---
    listing_results: list[ListingStatus] = []

    if args.check_buyable:
        from .listing_checker import get_provider, check_listings_concurrent
        provider = get_provider(
            args.provider,
            slug=args.slug,
            contract=args.contract,
            timeout=args.timeout,
            retries=args.retries,
        )
        print(f"Checking listing status for {len(token_ids)} IDs via {provider.name}…")
        listing_results = check_listings_concurrent(
            token_ids,
            provider,
            concurrency=args.concurrency,
        )
    else:
        listing_results = [
            ListingStatus(
                token_id=tid,
                buyable=None,
                error="skipped (--check-buyable not set)",
            )
            for tid in token_ids
        ]

    # --- 5. Build reports ---
    from .report_builder import merge_results, write_reports, print_summary
    results = merge_results(image_results, listing_results)
    write_reports(results, out_dir, provider=args.provider)

    # --- 6. Build contact sheet ---
    if not args.no_contact_sheet and args.download_images:
        from .contact_sheet_builder import build_contact_sheet
        downloaded_ids = [r.token_id for r in image_results if r.downloaded]
        if downloaded_ids:
            print("Building contact sheet…")
            build_contact_sheet(
                image_dir,
                downloaded_ids,
                out_dir,
                include_pdf=not args.no_pdf,
                columns=args.columns,
            )
        else:
            logger.warning("No images downloaded – skipping contact sheet.")

    # --- 7. Summary ---
    print_summary(results)
    print(f"Outputs written to {out_dir.resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
