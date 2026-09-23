"""Integrity-checked copies from a selected phone folder to Windows."""

import asyncio
import hashlib
import re
import shlex
import shutil
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from .adb import AdbFailure
from .catalog import VideoEntry, validate_folder, validate_name


class SourceChanged(RuntimeError):
    pass


class IntegrityFailure(RuntimeError):
    pass


@dataclass(frozen=True)
class TransferResult:
    name: str
    outcome: str
    destination: str | None
    message: str


def publish_without_overwrite(partial_path: Path, destination: Path) -> None:
    if destination.exists():
        raise FileExistsError(destination)
    partial_path.rename(destination)


async def stat_remote(adb, remote_path: str) -> tuple[int, float]:
    raw = await adb.run(
        "shell", "toybox", "find", shlex.quote(remote_path), "-maxdepth", "0", "-type", "f",
        "-printf", shlex.quote(r"%s\0%T@\0"), timeout=10,
    )
    fields = raw.split(b"\0")
    if len(fields) != 3 or fields[-1] != b"":
        raise SourceChanged("The selected phone file is no longer available")
    try:
        size, modified = int(fields[0]), float(fields[1])
    except ValueError as exc:
        raise SourceChanged("The phone file metadata changed") from exc
    if size < 0 or modified < 0:
        raise SourceChanged("The phone file metadata changed")
    return size, modified


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


async def copy_one(adb, entry: VideoEntry, phone_folder: str, pc_folder: Path,
                   progress=None) -> TransferResult:
    partial = None

    def stage(value):
        if progress is not None:
            progress(entry.name, value)

    stage("waiting")
    try:
        folder = validate_folder(phone_folder)
        name = validate_name(entry.name)
        remote_path = f"{folder}/{name}"
        pc_folder = Path(pc_folder).expanduser()
        pc_folder.mkdir(parents=True, exist_ok=True)
        destination = pc_folder / name
        if destination.exists():
            raise FileExistsError("A PC file with this name already exists")
        if shutil.disk_usage(pc_folder).free < entry.size:
            raise OSError("Not enough free space in the PC destination")

        before = await stat_remote(adb, remote_path)
        if before != (entry.size, entry.modified):
            raise SourceChanged("The phone file changed since it was selected")
        partial = pc_folder / f".{uuid4().hex}.partial"
        stage("copying")
        await adb.pull(remote_path, partial)
        stage("hashing")
        local_size = partial.stat().st_size
        local_hash = await asyncio.to_thread(_hash_file, partial)
        remote_hash_raw = await adb.run("shell", "toybox", "sha256sum", "-b",
                                        shlex.quote(remote_path), timeout=300)
        remote_hash = remote_hash_raw.strip().decode("ascii", errors="strict")
        if not re.fullmatch(r"[0-9a-f]{64}", remote_hash):
            raise IntegrityFailure("The phone did not return a valid SHA-256 digest")
        after = await stat_remote(adb, remote_path)
        if before != after:
            raise SourceChanged("The phone file changed during copying")
        if local_size != after[0] or local_hash != remote_hash:
            raise IntegrityFailure("The PC copy differs from the phone file")
        publish_without_overwrite(partial, destination)
        stage("verified")
        return TransferResult(name, "verified", str(destination), "Size and SHA-256 verified")
    except (AdbFailure, OSError, ValueError, SourceChanged, IntegrityFailure) as exc:
        stage("failed")
        return TransferResult(entry.name, "failed", None, str(exc))
    finally:
        if partial is not None:
            partial.unlink(missing_ok=True)


async def copy_many(adb, entries: list[VideoEntry], phone_folder: str, pc_folder: Path,
                    progress=None, on_result=None) -> list[TransferResult]:
    results: list[TransferResult | None] = [None] * len(entries)
    remaining = iter(enumerate(entries))

    async def worker():
        for index, entry in remaining:
            result = await copy_one(adb, entry, phone_folder, pc_folder, progress=progress)
            results[index] = result
            if on_result is not None:
                on_result(result)

    await asyncio.gather(*(worker() for _ in range(min(2, len(entries)))))
    return [result for result in results if result is not None]
