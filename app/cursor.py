import base64
import binascii
import json
from datetime import datetime
from typing import Any


class InvalidCursorError(ValueError):
    """Raised when a pagination cursor cannot be decoded or validated."""


def encode_cursor(
    snapshot_at: datetime,
    last_created_at: datetime,
    last_id: int,
    category: str | None,
) -> str:
    """Convert pagination values into a URL-safe cursor string."""
    data = {
        "snapshot_at": snapshot_at.isoformat(),
        "last_created_at": last_created_at.isoformat(),
        "last_id": last_id,
        "category": category,
    }
    raw = json.dumps(data, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("utf-8")


def decode_cursor(cursor: str) -> dict[str, Any]:
    """Decode and validate a cursor received from the client."""
    try:
        raw = base64.urlsafe_b64decode(cursor.encode("utf-8"))
        data = json.loads(raw.decode("utf-8"))

        snapshot_at = datetime.fromisoformat(data["snapshot_at"])
        last_created_at = datetime.fromisoformat(data["last_created_at"])
        last_id = int(data["last_id"])
        category = data.get("category")

        if last_id <= 0:
            raise ValueError("last_id must be positive")
        if category is not None and not isinstance(category, str):
            raise ValueError("category must be text or null")

        return {
            "snapshot_at": snapshot_at,
            "last_created_at": last_created_at,
            "last_id": last_id,
            "category": category,
        }
    except (KeyError, TypeError, ValueError, json.JSONDecodeError, binascii.Error) as exc:
        raise InvalidCursorError("Invalid pagination cursor") from exc
