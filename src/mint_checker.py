"""
mint_checker.py — pre-flight filter for the known-missing ID list.

On first run (or any run), call `filter_unminted()` to remove IDs that have
since been minted.  An ID is considered still-unminted when the Lil Pudgys
metadata endpoint returns 404.  Any response other than a clean 200 (network
error, timeout, 5xx) is treated conservatively: the ID is kept so we don't
silently drop something we couldn't verify.
"""
from __future__ import annotations
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

from .config import LIL_IMAGE_URL, DEFAULT_CONCURRENCY

logger = logging.getLogger(__name__)

# Separate, shorter timeout for the mint-existence check.
# The metadata endpoint is fast when a token exists; slow responses almost
# always indicate the token is absent or the request is stale.
_METADATA_URL = "https://api.pudgypenguins.io/lil/{id}"
_MINT_CHECK_TIMEOUT = 10   # seconds — tight enough to avoid hanging workers
_MINT_CHECK_RETRIES = 2    # quick retry on transient errors before giving up


def _is_still_unminted(token_id: int, session: requests.Session) -> bool | None:
    """
    Return:
      True  — token returns 404 (still unminted, keep it)
      False — token returns 200 (now minted, remove it)
      None  — request failed / timed out (keep it conservatively)
    """
    url = _METADATA_URL.format(id=token_id)
    for attempt in range(_MINT_CHECK_RETRIES + 1):
        try:
            resp = session.get(url, timeout=_MINT_CHECK_TIMEOUT)
            if resp.status_code == 404:
                return True   # still unminted
            if resp.status_code == 200:
                return False  # now minted
            # Unexpected status — retry once, then keep conservatively
            logger.debug(
                "Mint check ID %d: unexpected HTTP %d (attempt %d)",
                token_id, resp.status_code, attempt + 1,
            )
        except requests.Timeout:
            logger.debug("Mint check ID %d: timeout (attempt %d)", token_id, attempt + 1)
        except requests.ConnectionError as exc:
            logger.debug("Mint check ID %d: connection error: %s", token_id, exc)
        except requests.RequestException as exc:
            logger.debug("Mint check ID %d: request error: %s", token_id, exc)

    logger.warning(
        "Mint check ID %d: could not verify after %d attempts — keeping conservatively",
        token_id, _MINT_CHECK_RETRIES + 1,
    )
    return None  # keep


def filter_unminted(
    token_ids: list[int],
    *,
    concurrency: int = DEFAULT_CONCURRENCY,
) -> tuple[list[int], list[int]]:
    """
    Check every ID in token_ids against the Lil Pudgys metadata API.

    Returns:
      (still_unminted, now_minted)
        still_unminted — IDs that are confirmed 404 or unverifiable (kept)
        now_minted     — IDs that returned 200 (remove from working set)
    """
    session = requests.Session()
    session.headers["User-Agent"] = "missing-lil-pudgys/1.0"

    # Keep connections alive across the pool; the default adapter handles this.
    session.mount("https://", requests.adapters.HTTPAdapter(
        max_retries=0,          # we handle retries ourselves
        pool_connections=concurrency,
        pool_maxsize=concurrency + 4,
        pool_block=False,
    ))

    still_unminted: list[int] = []
    now_minted: list[int] = []
    total = len(token_ids)
    done = 0

    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = {
            pool.submit(_is_still_unminted, tid, session): tid
            for tid in token_ids
        }
        for future in as_completed(futures):
            tid = futures[future]
            result = future.result()
            if result is False:
                now_minted.append(tid)
            else:
                still_unminted.append(tid)   # True or None → keep
            done += 1
            if done % 50 == 0 or done == total:
                logger.info(
                    "Mint check: %d/%d checked | %d now minted | %d still missing",
                    done, total, len(now_minted), len(still_unminted),
                )

    session.close()

    # Restore original order
    id_order = {tid: i for i, tid in enumerate(token_ids)}
    still_unminted.sort(key=lambda x: id_order[x])
    now_minted.sort(key=lambda x: id_order[x])
    return still_unminted, now_minted
