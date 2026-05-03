"""Tests for utils.parsing.safe_int — defensive callback_data parser."""
from __future__ import annotations

import pytest

from utils.parsing import safe_int


@pytest.mark.parametrize("raw,expected", [
    ("42", 42),
    ("0", 0),
    ("  7  ", 7),
    ("+5", 5),
    # garbage
    ("-1", None),
    ("abc", None),
    ("3.14", None),
    ("1e3", None),
    ("99999999999999999999", None),  # over the cap
    ("", None),
    ("   ", None),
    (None, None),
])
def test_safe_int_handles_arbitrary_input(raw, expected):
    assert safe_int(raw) == expected
