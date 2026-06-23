from datetime import UTC, datetime

import pytest

from app.cursor import InvalidCursorError, decode_cursor, encode_cursor


def test_cursor_round_trip():
    snapshot_at = datetime(2026, 6, 22, 10, 0, tzinfo=UTC)
    last_created_at = datetime(2026, 6, 20, 8, 30, tzinfo=UTC)

    cursor = encode_cursor(snapshot_at, last_created_at, 123, "books")
    decoded = decode_cursor(cursor)

    assert decoded["snapshot_at"] == snapshot_at
    assert decoded["last_created_at"] == last_created_at
    assert decoded["last_id"] == 123
    assert decoded["category"] == "books"


def test_invalid_cursor():
    with pytest.raises(InvalidCursorError):
        decode_cursor("not-a-valid-cursor")
