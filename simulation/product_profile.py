from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class ProductProfile:
    """
    High-mix “product profile” metadata for the currently loaded board.

    This is intentionally lightweight but structured, so we can propagate it into:
    - the AI prompt payload
    - the UI overlay
    - the mTrac CSV logs
    """

    profile_id: int
    sku: str
    revision: str
    board_serial: str
    seed: int
    created_utc: str

    @staticmethod
    def now_utc_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

