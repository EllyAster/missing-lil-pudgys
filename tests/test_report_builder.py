import csv
import json
from pathlib import Path

import pytest

from src.models import ImageFetchResult, ListingStatus, TokenResult
from src.report_builder import merge_results, write_reports


def _img(tid: int, ok: bool = True) -> ImageFetchResult:
    if ok:
        return ImageFetchResult(token_id=tid, downloaded=True, path=f"missing/{tid}.png")
    return ImageFetchResult(token_id=tid, downloaded=False, error="HTTP 404")


def _listing(tid: int, buyable: bool | None = True, price: str = "1.0") -> ListingStatus:
    return ListingStatus(
        token_id=tid,
        buyable=buyable,
        price=price if buyable else None,
        currency="ETH" if buyable else None,
        url=f"https://opensea.io/assets/ethereum/0xBd3531dA5CF5857e7CfAA92426877b022e612cf8/{tid}",
        listing_source="opensea",
    )


class TestMergeResults:
    def test_basic_merge(self):
        imgs = [_img(1), _img(2, ok=False)]
        listings = [_listing(1), _listing(2, buyable=False)]
        results = merge_results(imgs, listings)
        assert len(results) == 2
        assert results[0].token_id == 1
        assert results[0].image_downloaded is True
        assert results[0].buyable is True
        assert results[1].token_id == 2
        assert results[1].image_downloaded is False
        assert results[1].buyable is False

    def test_missing_listing_gives_none(self):
        imgs = [_img(5)]
        results = merge_results(imgs, [])
        assert results[0].buyable is None

    def test_status_ok(self):
        r = merge_results([_img(1)], [_listing(1)])[0]
        assert r.status == "ok"

    def test_status_error_on_image_fail(self):
        r = merge_results([_img(1, ok=False)], [_listing(1)])[0]
        assert r.status == "error"

    def test_status_unknown_when_buyable_none(self):
        r = merge_results([_img(1)], [_listing(1, buyable=None)])[0]
        assert r.status == "unknown"


class TestWriteReports:
    def test_writes_expected_files(self, tmp_path):
        imgs = [_img(1), _img(2)]
        listings = [_listing(1), _listing(2, buyable=False)]
        results = merge_results(imgs, listings)
        write_reports(results, tmp_path)

        assert (tmp_path / "report.json").exists()
        assert (tmp_path / "report.csv").exists()
        assert (tmp_path / "buyable_only.csv").exists()
        assert (tmp_path / "buyable_only.json").exists()

    def test_report_json_structure(self, tmp_path):
        imgs = [_img(5)]
        listings = [_listing(5, price="2.5")]
        results = merge_results(imgs, listings)
        write_reports(results, tmp_path)

        data = json.loads((tmp_path / "report.json").read_text())
        assert data["input_count"] == 1
        assert data["results"][0]["token_id"] == 5
        assert data["results"][0]["buyable"] is True
        assert data["results"][0]["price"] == "2.5"

    def test_buyable_only_csv_filters_correctly(self, tmp_path):
        imgs = [_img(1), _img(2), _img(3)]
        listings = [_listing(1), _listing(2, buyable=False), _listing(3, buyable=None)]
        results = merge_results(imgs, listings)
        write_reports(results, tmp_path)

        rows = list(csv.DictReader((tmp_path / "buyable_only.csv").open()))
        assert len(rows) == 1
        assert rows[0]["token_id"] == "1"

    def test_report_csv_has_all_ids(self, tmp_path):
        ids = [10, 20, 30]
        imgs = [_img(i) for i in ids]
        listings = [_listing(i) for i in ids]
        results = merge_results(imgs, listings)
        write_reports(results, tmp_path)

        rows = list(csv.DictReader((tmp_path / "report.csv").open()))
        assert [int(r["token_id"]) for r in rows] == ids
