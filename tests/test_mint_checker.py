from unittest.mock import MagicMock, patch

import pytest
import requests

from src.mint_checker import filter_unminted, _is_still_unminted


def _session() -> MagicMock:
    return MagicMock(spec=requests.Session)


def _resp(status_code: int) -> MagicMock:
    r = MagicMock(spec=requests.Response)
    r.status_code = status_code
    return r


class TestIsStillUnminted:
    def test_404_means_still_unminted(self):
        session = _session()
        session.get.return_value = _resp(404)
        assert _is_still_unminted(5, session) is True

    def test_200_means_now_minted(self):
        session = _session()
        session.get.return_value = _resp(200)
        assert _is_still_unminted(5, session) is False

    def test_timeout_keeps_conservatively(self):
        session = _session()
        session.get.side_effect = requests.Timeout
        result = _is_still_unminted(5, session)
        assert result is None   # keep conservatively

    def test_connection_error_keeps_conservatively(self):
        session = _session()
        session.get.side_effect = requests.ConnectionError("unreachable")
        result = _is_still_unminted(5, session)
        assert result is None

    def test_unexpected_status_keeps_conservatively(self):
        session = _session()
        session.get.return_value = _resp(503)
        result = _is_still_unminted(5, session)
        assert result is None


class TestFilterUnminted:
    def test_splits_correctly(self):
        # 5 → still unminted, 6 → now minted, 11 → still unminted
        results = {5: True, 6: False, 11: True}
        with patch("src.mint_checker._is_still_unminted", side_effect=lambda tid, _s: results[tid]):
            still, minted = filter_unminted([5, 6, 11])
        assert set(still) == {5, 11}
        assert set(minted) == {6}

    def test_timeout_keeps_id(self):
        # None (unverifiable) → kept conservatively
        with patch("src.mint_checker._is_still_unminted", return_value=None):
            still, minted = filter_unminted([42])
        assert 42 in still
        assert minted == []

    def test_empty_input(self):
        still, minted = filter_unminted([])
        assert still == []
        assert minted == []

    def test_order_preserved(self):
        with patch("src.mint_checker._is_still_unminted", return_value=True):
            still, _ = filter_unminted([3, 1, 2])
        assert still == [3, 1, 2]
