import textwrap
from pathlib import Path

import pytest

from src.input_loader import load_ids


def _write(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "ids.txt"
    p.write_text(textwrap.dedent(content))
    return str(p)


def test_basic(tmp_path):
    p = _write(tmp_path, """\
        5
        6
        11
    """)
    assert load_ids(p) == [5, 6, 11]


def test_blank_lines_ignored(tmp_path):
    p = _write(tmp_path, """\

        5

        6

    """)
    assert load_ids(p) == [5, 6]


def test_duplicates_removed_order_preserved(tmp_path):
    p = _write(tmp_path, """\
        10
        5
        10
        3
        5
    """)
    assert load_ids(p) == [10, 5, 3]


def test_non_numeric_skipped(tmp_path):
    p = _write(tmp_path, """\
        5
        abc
        7
    """)
    assert load_ids(p) == [5, 7]


def test_negative_skipped(tmp_path):
    p = _write(tmp_path, """\
        -1
        5
    """)
    assert load_ids(p) == [5]


def test_zero_valid(tmp_path):
    p = _write(tmp_path, "0\n")
    assert load_ids(p) == [0]


def test_file_not_found():
    with pytest.raises(FileNotFoundError):
        load_ids("/nonexistent/path/ids.txt")


def test_empty_file(tmp_path):
    p = _write(tmp_path, "")
    assert load_ids(p) == []
