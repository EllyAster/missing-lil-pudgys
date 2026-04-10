import pytest
from src.utils import content_type_to_ext


@pytest.mark.parametrize("ct,expected", [
    ("image/png", ".png"),
    ("image/jpeg", ".jpg"),
    ("image/jpg", ".jpg"),
    ("image/webp", ".webp"),
    ("image/gif", ".gif"),
    ("image/svg+xml", ".svg"),
    ("image/png; charset=utf-8", ".png"),
    ("IMAGE/PNG", ".png"),
    ("application/octet-stream", ".bin"),
    ("", ".bin"),
])
def test_content_type_to_ext(ct, expected):
    assert content_type_to_ext(ct) == expected
