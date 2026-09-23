"""Bounded phone video listing and safe names."""

import math
import shlex
from dataclasses import dataclass
from pathlib import Path


DEFAULT_PHONE_FOLDER = "/sdcard/DCIM/OpenCamera"
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".3gp"}


class InvalidListing(ValueError):
    pass


class InvalidVideoName(ValueError):
    pass


@dataclass(frozen=True)
class VideoEntry:
    name: str
    size: int
    modified: float
    duration_ms: int | None = None


def validate_name(name: str) -> str:
    if (not name or name in (".", "..") or "/" in name or "\\" in name
            or "\0" in name or Path(name).suffix.lower() not in VIDEO_EXTENSIONS
            or not Path(name).stem):
        raise InvalidVideoName(name)
    return name


def validate_folder(folder: str) -> str:
    if not isinstance(folder, str) or any(ch in folder for ch in "\0\r\n"):
        raise ValueError("Choose a folder in shared phone storage")
    roots = ("/sdcard/", "/storage/emulated/0/")
    if not folder.startswith(roots):
        raise ValueError("Choose a folder in shared phone storage")
    tail = folder.split("/", 3)[3] if folder.startswith("/storage/emulated/0/") else folder[len("/sdcard/"):]
    if not tail or any(part in ("", ".", "..") for part in tail.split("/")):
        raise ValueError("Phone folder must not contain traversal")
    return folder


def parse_listing(raw: bytes) -> list[VideoEntry]:
    if raw == b"":
        return []
    if not raw.endswith(b"\0"):
        raise InvalidListing("Incomplete phone listing")
    fields = raw[:-1].split(b"\0")
    if len(fields) % 3:
        raise InvalidListing("Malformed phone listing")
    entries = []
    try:
        for i in range(0, len(fields), 3):
            name = fields[i].decode("utf-8", errors="strict")
            if not name or "/" in name or "\\" in name:
                raise InvalidListing("A listed name is not a basename")
            size = int(fields[i + 1].decode("ascii"))
            modified = float(fields[i + 2].decode("ascii"))
            if size < 0 or not math.isfinite(modified) or modified < 0:
                raise InvalidListing("Invalid file metadata")
            if Path(name).suffix.lower() in VIDEO_EXTENSIONS:
                validate_name(name)
                entries.append(VideoEntry(name, size, modified))
    except (UnicodeError, ValueError) as exc:
        raise InvalidListing("Malformed phone listing") from exc
    return sorted(entries, key=lambda item: (item.modified, item.name), reverse=True)


async def list_videos(adb, folder: str) -> list[VideoEntry]:
    folder = validate_folder(folder)
    raw = await adb.run(
        "shell", "toybox", "find", shlex.quote(folder), "-maxdepth", "1", "-type", "f",
        "-printf", shlex.quote(r"%f\0%s\0%T@\0"), timeout=15,
    )
    return parse_listing(raw)
