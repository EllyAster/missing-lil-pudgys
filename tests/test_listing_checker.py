from unittest.mock import MagicMock, patch

import pytest
import requests

from src.listing_checker import OpenSeaListingProvider
from src.models import ListingStatus


def _provider(api_key="test-key") -> OpenSeaListingProvider:
    return OpenSeaListingProvider(api_key=api_key, slug="pudgypenguins")


def _make_response(status_code: int, json_body=None) -> MagicMock:
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status_code
    resp.json.return_value = json_body or {}
    http_err = requests.HTTPError(response=resp)
    if status_code >= 400 and status_code != 404:
        resp.raise_for_status.side_effect = http_err
    else:
        resp.raise_for_status.return_value = None
    return resp


class TestOpenSeaListingProvider:
    def test_no_api_key_returns_unknown(self):
        provider = OpenSeaListingProvider(api_key="")
        result = provider.get_best_listing(42)
        assert result.buyable is None
        assert result.error is not None
        assert "OPENSEA_API_KEY" in result.error

    def test_404_means_not_buyable(self):
        provider = _provider()
        resp = _make_response(404)
        with patch.object(provider._session, "get", return_value=resp):
            result = provider.get_best_listing(42)
        assert result.buyable is False
        assert result.error is None

    def test_valid_listing_with_price(self):
        provider = _provider()
        payload = {
            "price": {
                "current": {
                    "value": 12_500_000_000_000_000_000,  # 12.5 ETH in wei
                    "decimals": 18,
                    "currency": "ETH",
                }
            }
        }
        resp = _make_response(200, json_body=payload)
        with patch.object(provider._session, "get", return_value=resp):
            result = provider.get_best_listing(5)
        assert result.buyable is True
        assert result.price == "12.5"
        assert result.currency == "ETH"
        assert result.token_id == 5

    def test_empty_response_body_means_not_buyable(self):
        provider = _provider()
        resp = _make_response(200, json_body=None)
        with patch.object(provider._session, "get", return_value=resp):
            result = provider.get_best_listing(5)
        assert result.buyable is False

    def test_auth_error_returns_unknown(self):
        provider = _provider()
        resp = _make_response(401)
        with patch.object(provider._session, "get", return_value=resp):
            result = provider.get_best_listing(5)
        assert result.buyable is None
        assert "Auth error" in (result.error or "")

    def test_403_returns_unknown(self):
        provider = _provider()
        resp = _make_response(403)
        with patch.object(provider._session, "get", return_value=resp):
            result = provider.get_best_listing(5)
        assert result.buyable is None
        assert "Auth error" in (result.error or "")

    def test_malformed_json_returns_unknown(self):
        provider = _provider()
        resp = _make_response(200)
        resp.json.side_effect = ValueError("bad json")
        resp.raise_for_status.return_value = None
        with patch.object(provider._session, "get", return_value=resp):
            result = provider.get_best_listing(5)
        assert result.buyable is None
        assert result.error is not None

    def test_listing_source_is_opensea(self):
        provider = _provider()
        resp = _make_response(404)
        with patch.object(provider._session, "get", return_value=resp):
            result = provider.get_best_listing(1)
        assert result.listing_source == "opensea"
