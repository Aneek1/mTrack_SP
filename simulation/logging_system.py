from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal, Optional


PassFail = Literal["PASS", "FAIL", "UNKNOWN"]
ControlMode = Literal["AI", "MANUAL", "SAFE_RETURN"]
AIStatus = Literal["inspecting", "moving", "idle", "error", "unknown"]


@dataclass
class MTracRecord:
    timestamp_utc: str
    component_id: str
    pass_fail: PassFail
    profile_id: Optional[int] = None
    sku: Optional[str] = None
    revision: Optional[str] = None
    board_serial: Optional[str] = None
    gantry_x: Optional[float] = None
    gantry_y: Optional[float] = None
    control_mode: Optional[ControlMode] = None
    ai_status: Optional[AIStatus] = None
    ai_log: Optional[str] = None


class MTracLogger:
    """Simple mTrac-style CSV logger for each inspection/move."""

    FIELDNAMES: list[str] = [
        "timestamp_utc",
        "component_id",
        "pass_fail",
        "profile_id",
        "sku",
        "revision",
        "board_serial",
        "gantry_x",
        "gantry_y",
        "control_mode",
        "ai_status",
        "ai_log",
    ]

    def __init__(self, csv_path: str = "mtrac_log.csv") -> None:
        self.csv_path: str = self._ensure_header(csv_path)

    def _ensure_header(self, desired_path: str) -> str:
        """
        Ensure a CSV header exists and matches our current schema.

        If a legacy file exists with a different header, we will not overwrite it;
        instead we write to a side-by-side v2 file.
        """
        if not os.path.exists(desired_path):
            with open(desired_path, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=self.FIELDNAMES)
                writer.writeheader()
            return desired_path

        # File exists: check header compatibility.
        try:
            with open(desired_path, mode="r", newline="", encoding="utf-8") as f:
                reader = csv.reader(f)
                existing = next(reader, [])
        except Exception:
            existing = []

        if existing == self.FIELDNAMES:
            return desired_path

        # Legacy or mismatched header: write to a new v2 file.
        base, ext = os.path.splitext(desired_path)
        v2_path = f"{base}.v2{ext or '.csv'}"
        if not os.path.exists(v2_path):
            with open(v2_path, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=self.FIELDNAMES)
                writer.writeheader()
        return v2_path

    def log(
        self,
        component_id: str,
        pass_fail: PassFail,
        *,
        profile_id: int | None = None,
        sku: str | None = None,
        revision: str | None = None,
        board_serial: str | None = None,
        gantry_x: float | None = None,
        gantry_y: float | None = None,
        control_mode: ControlMode | None = None,
        ai_status: AIStatus | None = None,
        ai_log: str | None = None,
    ) -> None:
        record = MTracRecord(
            timestamp_utc=datetime.now(timezone.utc).isoformat(),
            component_id=component_id,
            pass_fail=pass_fail,
            profile_id=profile_id,
            sku=sku,
            revision=revision,
            board_serial=board_serial,
            gantry_x=gantry_x,
            gantry_y=gantry_y,
            control_mode=control_mode,
            ai_status=ai_status,
            ai_log=ai_log,
        )
        with open(self.csv_path, mode="a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=self.FIELDNAMES)
            writer.writerow(
                {
                    "timestamp_utc": record.timestamp_utc,
                    "component_id": record.component_id,
                    "pass_fail": record.pass_fail,
                    "profile_id": record.profile_id,
                    "sku": record.sku,
                    "revision": record.revision,
                    "board_serial": record.board_serial,
                    "gantry_x": record.gantry_x,
                    "gantry_y": record.gantry_y,
                    "control_mode": record.control_mode,
                    "ai_status": record.ai_status,
                    "ai_log": record.ai_log,
                }
            )

