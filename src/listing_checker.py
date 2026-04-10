from __future__ import annotations
import logging
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

from .config import (
    OPENSEA_API_KEY,
    OPENSEA_BEST_LISTING_URL,
    OPENSEA_NFT_BASE_URL,
    PUDGY_PENGUINS_CONTRACT,
    PUDGY_PENGUINS_SLUG,
    DEFAULT_TIMEOUT,
    DEFAULT_RETRIES,
)
from .models import ListingStatus
from .utils import retry

logger = logging.getLogger(__name__)


class ListingProvider(ABC):
    @abstractmethod
    def get_best_listing(self, token_id: int) -> ListingStatus:
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        ...


class OpenSeaListingProvider(ListingProvider):
    """Query OpenSea's best-listing endpoint for current buyability."""

    name = "opensea"

    def __init__(
        self,
        api_key: str = "",
        slug: str = PUDGY_PENGUINS_SLUG,
        contract: str = PUDGY_PENGUINS_CONTRACT,
        timeout: int = DEFAULT_TIMEOUT,
        retries: int = DEFAULT_RETRIES,
    ) -> None:
        self._api_key = api_key or OPENSEA_API_KEY
        self._slug = slug
        self._contract = contract
        self._timeout = timeout
        self._retries = retries
        self._session = requests.Session()
        self._session.headers.update(
            {
                "User-Agent": "missing-lil-pudgys/1.0",
                "accept": "application/json",
            }
        )
        if self._api_key:
            self._session.headers["x-api-key"] = self._api_key

    def get_best_listing(self, token_id: int) -> ListingStatus:
        if not self._api_key:
            logger.warning(
                "OPENSEA_API_KEY is not set – listing check for ID %d will be skipped",
                token_id,
            )
            return ListingStatus(
                token_id=token_id,
                buyable=None,
                listing_source=self.name,
                error="OPENSEA_API_KEY not configured",
            )

        url = OPENSEA_BEST_LISTING_URL.format(
            slug=self._slug, identifier=token_id
        )

        def _do_request() -> requests.Response:
            resp = self._session.get(url, timeout=self._timeout)
            # Treat 404 as "no listing" (not retriable)
            if resp.status_code == 404:
                return resp
            resp.raise_for_status()
            return resp

        nft_url = OPENSEA_NFT_BASE_URL.format(
            contract=self._contract, token_id=token_id
        )

        try:
            resp = retry(_do_request, retries=self._retries)
        except requests.HTTPError as exc:
            code = exc.response.status_code if exc.response is not None else "?"
            if code in (401, 403):
                msg = f"Auth error (HTTP {code}) – check OPENSEA_API_KEY"
            else:
                msg = f"HTTP {code}"
            logger.warning("Listing check failed for ID %d: %s", token_id, msg)
            return ListingStatus(
                token_id=token_id,
                buyable=None,
                listing_source=self.name,
                error=msg,
            )
        except requests.RequestException as exc:
            msg = str(exc)
            logger.warning("Listing request error for ID %d: %s", token_id, msg)
            return ListingStatus(
                token_id=token_id,
                buyable=None,
                listing_source=self.name,
                error=msg,
            )

        if resp.status_code == 404:
            return ListingStatus(
                token_id=token_id,
                buyable=False,
                listing_source=self.name,
                url=nft_url,
            )

        try:
            data = resp.json()
        except Exception as exc:
            msg = f"Malformed JSON: {exc}"
            logger.warning("Listing response parse error for ID %d: %s", token_id, msg)
            return ListingStatus(
                token_id=token_id,
                buyable=None,
                listing_source=self.name,
                error=msg,
            )

        # The best-listing endpoint returns the listing object directly when
        # one exists.  An empty or missing "listing" key means not buyable.
        listing = data if data else None
        if not listing:
            return ListingStatus(
                token_id=token_id,
                buyable=False,
                listing_source=self.name,
                url=nft_url,
            )

        # Extract price from the canonical OpenSea v2 payload shape.
        price_str: str | None = None
        currency: str | None = None
        try:
            price_info = (
                listing.get("price", {})
                .get("current", {})
            )
            raw_value = price_info.get("value")
            decimals = price_info.get("decimals", 18)
            currency = price_info.get("currency", "ETH")
            if raw_value is not None:
                price_str = str(int(raw_value) / (10 ** int(decimals)))
        except Exception:
            pass

        return ListingStatus(
            token_id=token_id,
            buyable=True,
            price=price_str,
            currency=currency,
            url=nft_url,
            listing_source=self.name,
        )


def check_listings_concurrent(
    token_ids: list[int],
    provider: ListingProvider,
    *,
    concurrency: int = 5,
) -> list[ListingStatus]:
    """Check listing status for all token_ids concurrently."""
    results: list[ListingStatus] = []
    total = len(token_ids)
    done = 0

    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = {
            pool.submit(provider.get_best_listing, tid): tid for tid in token_ids
        }
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            done += 1
            if result.buyable is True:
                flag = f"BUYABLE @ {result.price} {result.currency}"
            elif result.buyable is False:
                flag = "not listed"
            else:
                flag = f"unknown ({result.error})"
            logger.info(
                "[%d/%d] Listing ID %d: %s", done, total, result.token_id, flag
            )

    id_order = {tid: i for i, tid in enumerate(token_ids)}
    results.sort(key=lambda r: id_order[r.token_id])
    return results


def get_provider(name: str, **kwargs) -> ListingProvider:
    if name == "opensea":
        return OpenSeaListingProvider(**kwargs)
    raise ValueError(f"Unknown provider: {name!r}")
