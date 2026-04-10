from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ImageFetchResult:
    token_id: int
    downloaded: bool
    path: Optional[str] = None      # relative path inside output dir, e.g. "missing/5.png"
    error: Optional[str] = None


@dataclass
class ListingStatus:
    token_id: int
    buyable: Optional[bool] = None  # None means unknown
    price: Optional[str] = None
    currency: Optional[str] = None
    url: Optional[str] = None
    listing_source: Optional[str] = None
    error: Optional[str] = None


@dataclass
class TokenResult:
    token_id: int
    image_downloaded: bool = False
    image_path: Optional[str] = None
    image_error: Optional[str] = None
    buyable: Optional[bool] = None
    price: Optional[str] = None
    currency: Optional[str] = None
    listing_source: Optional[str] = None
    listing_url: Optional[str] = None
    listing_error: Optional[str] = None

    @property
    def status(self) -> str:
        if self.image_error or self.listing_error:
            return "error"
        if self.buyable is None:
            return "unknown"
        return "ok"

    @property
    def error(self) -> Optional[str]:
        parts = []
        if self.image_error:
            parts.append(f"image: {self.image_error}")
        if self.listing_error:
            parts.append(f"listing: {self.listing_error}")
        return "; ".join(parts) if parts else None
