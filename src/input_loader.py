from __future__ import annotations
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def load_ids(path: str) -> list[int]:
    """
    Read token IDs from a plain text file (one per line).

    Rules:
      - Blank lines are ignored.
      - Lines that are not valid non-negative integers emit a warning and are skipped.
      - Duplicates are removed while preserving first-seen order.
    """
    ids: list[int] = []
    seen: set[int] = set()
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Input file not found: {path}")

    with p.open() as fh:
        for lineno, raw in enumerate(fh, start=1):
            line = raw.strip()
            if not line:
                continue
            try:
                token_id = int(line)
            except ValueError:
                logger.warning("Line %d: %r is not a valid integer – skipping", lineno, line)
                continue
            if token_id < 0:
                logger.warning("Line %d: %d is negative – skipping", lineno, token_id)
                continue
            if token_id in seen:
                logger.debug("Line %d: duplicate ID %d – skipping", lineno, token_id)
                continue
            seen.add(token_id)
            ids.append(token_id)

    logger.info("Loaded %d unique ID(s) from %s", len(ids), path)
    return ids
