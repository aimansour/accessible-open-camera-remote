"""Small privacy-preserving event log for local troubleshooting."""

import json
import re
from datetime import datetime, timezone
from pathlib import Path


EVENT_CODES = frozenset({
    "adb_ok", "adb_failure", "adb_timeout", "adb_start_failure",
    "camera_verified", "camera_uncertain", "copy_verified", "copy_failed",
    "move_verified", "move_uncertain", "rename_verified", "rename_uncertain",
    "delete_verified", "delete_uncertain", "service_started", "service_stopped",
})


class DiagnosticLog:
    def __init__(self, path: Path, device_model: str):
        self.path = Path(path)
        self.device_model = (device_model[:64] if re.fullmatch(r"[A-Za-z0-9_. -]{1,64}", device_model)
                             else "unknown")

    def record(self, event: str, *, elapsed_ms: int | None = None,
               adb_status: int | None = None, **_private_context) -> None:
        data = {
            "time_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "event": event if event in EVENT_CODES else "unknown",
            "elapsed_ms": elapsed_ms if type(elapsed_ms) is int and 0 <= elapsed_ms <= 86400000 else None,
            "adb_status": adb_status if type(adb_status) is int and -1 <= adb_status <= 255 else None,
            "device_model": self.device_model,
        }
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as output:
                output.write(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n")
        except OSError:
            # Diagnostics must not prevent a camera command from completing.
            pass
