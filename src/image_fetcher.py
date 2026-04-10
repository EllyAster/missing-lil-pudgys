from __future__ import annotations
import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

from .config import LIL_IMAGE_URL, DEFAULT_TIMEOUT, DEFAULT_RETRIES
from .models import ImageFetchResult
from .utils import content_type_to_ext, retry

logger = logging.getLogger(__name__)

_SESSION: requests.Session | None = None


def _session() -> requests.Session:
    global _SESSION
    if _SESSION is None:
        _SESSION = requests.Session()
        _SESSION.headers["User-Agent"] = "missing-lil-pudgys/1.0"
    return _SESSION


def fetch_image(
    token_id: int,
    out_dir: Path,
    *,
    timeout: int = DEFAULT_TIMEOUT,
    retries: int = DEFAULT_RETRIES,
    extensionless: bool = False,
) -> ImageFetchResult:
    """Download the Lil Pudgy preview image for token_id and save it to out_dir."""
    url = LIL_IMAGE_URL.format(id=token_id)

    def _do_request() -> requests.Response:
        resp = _session().get(url, timeout=timeout)
        resp.raise_for_status()
        return resp

    try:
        resp = retry(_do_request, retries=retries)
    except requests.HTTPError as exc:
        code = exc.response.status_code if exc.response is not None else "?"
        msg = f"HTTP {code}"
        logger.warning("Image fetch failed for ID %d: %s", token_id, msg)
        return ImageFetchResult(token_id=token_id, downloaded=False, error=msg)
    except requests.RequestException as exc:
        msg = str(exc)
        logger.warning("Image fetch error for ID %d: %s", token_id, msg)
        return ImageFetchResult(token_id=token_id, downloaded=False, error=msg)

    ct = resp.headers.get("Content-Type", "")
    ext = "" if extensionless else content_type_to_ext(ct)
    filename = f"{token_id}{ext}"
    dest = out_dir / filename
    dest.write_bytes(resp.content)
    rel_path = str(Path("missing") / filename)
    logger.debug("Saved image for ID %d → %s", token_id, dest)
    return ImageFetchResult(token_id=token_id, downloaded=True, path=rel_path)


def fetch_images_concurrent(
    token_ids: list[int],
    out_dir: Path,
    *,
    concurrency: int = 5,
    timeout: int = DEFAULT_TIMEOUT,
    retries: int = DEFAULT_RETRIES,
    extensionless: bool = False,
) -> list[ImageFetchResult]:
    """Download images for all token_ids concurrently."""
    out_dir.mkdir(parents=True, exist_ok=True)
    results: list[ImageFetchResult] = []
    total = len(token_ids)
    done = 0

    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = {
            pool.submit(
                fetch_image, tid, out_dir,
                timeout=timeout, retries=retries, extensionless=extensionless
            ): tid
            for tid in token_ids
        }
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            done += 1
            status = "OK" if result.downloaded else f"FAIL ({result.error})"
            logger.info("[%d/%d] Image ID %d: %s", done, total, result.token_id, status)

    # Return in original ID order
    id_order = {tid: i for i, tid in enumerate(token_ids)}
    results.sort(key=lambda r: id_order[r.token_id])
    return results
