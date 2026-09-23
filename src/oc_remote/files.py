"""Guarded phone video mutations with MediaStore verification."""

import re
import shlex
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

from .adb import AdbFailure
from .catalog import DEFAULT_PHONE_FOLDER, VideoEntry, list_videos, validate_folder, validate_name
from .transfer import SourceChanged, TransferResult, copy_one, stat_remote


class MediaIndexError(RuntimeError):
    pass


class UncertainMutation(RuntimeError):
    pass


@dataclass(frozen=True)
class MediaRow:
    row_id: int
    duration_ms: int | None


def media_path(folder: str, name: str) -> str:
    folder = validate_folder(folder)
    name = validate_name(name)
    if folder.startswith("/sdcard/"):
        folder = "/storage/emulated/0/" + folder[len("/sdcard/"):]
    return f"{folder}/{name}"


async def query_media_row(adb, folder: str, name: str) -> MediaRow | None:
    path = media_path(folder, name)
    sql_path = path.replace("'", "''")
    where = f"_data='{sql_path}'"
    raw = await adb.run(
        "shell", "content", "query", "--uri", "content://media/external/video/media",
        "--projection", "_id:_data:duration", "--where", shlex.quote(where), timeout=10,
    )
    output = raw.decode("utf-8", errors="strict").strip()
    if output == "No result found.":
        return None
    match = re.fullmatch(r"Row: 0 _id=(\d+), _data=(.*), duration=(\d+|null)", output, re.S)
    if not match or match.group(2) != path:
        raise MediaIndexError("MediaStore did not return one exact video identity")
    duration = None if match.group(3) == "null" else int(match.group(3))
    return MediaRow(int(match.group(1)), duration)


async def verify_media_index(adb, old_name: str | None, new_name: str | None,
                             folder: str = DEFAULT_PHONE_FOLDER) -> bool:
    if old_name is not None and await query_media_row(adb, folder, old_name) is not None:
        return False
    if new_name is not None and await query_media_row(adb, folder, new_name) is None:
        return False
    return True


async def assert_source_unchanged(adb, entry: VideoEntry, folder: str) -> None:
    path = f"{validate_folder(folder)}/{validate_name(entry.name)}"
    try:
        current = await stat_remote(adb, path)
    except (AdbFailure, SourceChanged) as exc:
        raise UncertainMutation("Could not confirm the selected phone file") from exc
    if current != (entry.size, entry.modified):
        raise UncertainMutation("The selected phone file changed")


async def _scan(adb, folder: str, name: str) -> None:
    uri = "file://" + quote(media_path(folder, name), safe="/")
    await adb.run("shell", "am", "broadcast", "-a", "android.intent.action.MEDIA_SCANNER_SCAN_FILE",
                  "-d", shlex.quote(uri), timeout=10)


async def rename_one(adb, entry: VideoEntry, phone_folder: str, new_stem: str) -> VideoEntry:
    folder = validate_folder(phone_folder)
    old_name = validate_name(entry.name)
    if (not new_stem or new_stem in (".", "..") or any(ch in new_stem for ch in "/\\\0\r\n")):
        raise ValueError("Choose a single new video name")
    new_name = validate_name(new_stem + Path(old_name).suffix)
    if new_name == old_name:
        raise ValueError("Choose a different video name")
    await assert_source_unchanged(adb, entry, folder)
    listing = await list_videos(adb, folder)
    if any(item.name == new_name for item in listing):
        raise FileExistsError("A phone video with the new name already exists")
    row = await query_media_row(adb, folder, old_name)
    try:
        if row is not None:
            await adb.run(
                "shell", "content", "update", "--uri",
                f"content://media/external/video/media/{row.row_id}",
                "--bind", shlex.quote(f"_display_name:s:{new_name}"), timeout=10,
            )
        else:
            await adb.run("shell", "mv", shlex.quote(f"{folder}/{old_name}"),
                          shlex.quote(f"{folder}/{new_name}"), timeout=10)
            await _scan(adb, folder, old_name)
            await _scan(adb, folder, new_name)
        listing = await list_videos(adb, folder)
        new_entry = next((item for item in listing if item.name == new_name), None)
        if new_entry is None or any(item.name == old_name for item in listing):
            raise UncertainMutation("Could not verify the renamed phone file")
        if not await verify_media_index(adb, old_name, new_name, folder):
            raise UncertainMutation("Android's media index does not match the rename")
        return new_entry
    except AdbFailure as exc:
        raise UncertainMutation("Rename result is uncertain; inspect the phone") from exc


async def delete_one(adb, entry: VideoEntry, phone_folder: str, confirmed_name: str) -> None:
    folder = validate_folder(phone_folder)
    name = validate_name(entry.name)
    if confirmed_name != name:
        raise ValueError("The exact video name must be confirmed before deletion")
    await assert_source_unchanged(adb, entry, folder)
    row = await query_media_row(adb, folder, name)
    try:
        if row is not None:
            await adb.run("shell", "content", "delete", "--uri",
                          f"content://media/external/video/media/{row.row_id}", timeout=10)
        else:
            await adb.run("shell", "rm", "-f", shlex.quote(f"{folder}/{name}"), timeout=10)
            await _scan(adb, folder, name)
        if any(item.name == name for item in await list_videos(adb, folder)):
            raise UncertainMutation("The phone file still exists after deletion")
        if not await verify_media_index(adb, old_name=name, new_name=None, folder=folder):
            raise UncertainMutation("Android's media index still contains the deleted video")
    except AdbFailure as exc:
        raise UncertainMutation("Deletion result is uncertain; inspect the phone") from exc


async def move_one(adb, entry: VideoEntry, phone_folder: str, pc_folder: Path) -> TransferResult:
    copied = await copy_one(adb, entry, phone_folder, pc_folder)
    if copied.outcome != "verified":
        return copied
    try:
        await delete_one(adb, entry, phone_folder, entry.name)
    except (AdbFailure, UncertainMutation, MediaIndexError, OSError) as exc:
        return TransferResult(entry.name, "uncertain", copied.destination,
                              "PC copy verified; phone source deletion is uncertain")
    return TransferResult(entry.name, "verified", copied.destination,
                          "PC copy and phone source removal verified")
