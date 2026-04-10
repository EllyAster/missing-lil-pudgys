from __future__ import annotations
import logging
import time
from typing import Callable, TypeVar

T = TypeVar("T")

logger = logging.getLogger(__name__)

CONTENT_TYPE_TO_EXT: dict[str, str] = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "image/svg+xml": ".svg",
}


def content_type_to_ext(content_type: str) -> str:
    """Return a file extension (with dot) for the given Content-Type header value."""
    # strip parameters like "; charset=utf-8"
    base = content_type.split(";")[0].strip().lower()
    return CONTENT_TYPE_TO_EXT.get(base, ".bin")


def retry(
    fn: Callable[[], T],
    retries: int = 3,
    backoff: float = 1.0,
    retriable_statuses: tuple[int, ...] = (500, 502, 503, 504, 429),
) -> T:
    """
    Call fn() up to retries+1 times, sleeping with exponential backoff on
    retriable HTTP errors.  fn() should raise requests.HTTPError on failure.
    """
    import requests

    last_exc: Exception | None = None
    for attempt in range(retries + 1):
        try:
            return fn()
        except requests.HTTPError as exc:
            code = exc.response.status_code if exc.response is not None else None
            if code in retriable_statuses and attempt < retries:
                wait = backoff * (2 ** attempt)
                logger.warning("HTTP %s – retrying in %.1fs (attempt %d/%d)",
                               code, wait, attempt + 1, retries)
                time.sleep(wait)
                last_exc = exc
            else:
                raise
        except requests.RequestException as exc:
            if attempt < retries:
                wait = backoff * (2 ** attempt)
                logger.warning("Request error – retrying in %.1fs: %s", wait, exc)
                time.sleep(wait)
                last_exc = exc
            else:
                raise
    raise last_exc  # type: ignore[misc]


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        level=level,
    )
