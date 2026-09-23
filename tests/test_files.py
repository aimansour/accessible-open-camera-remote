import shlex
from pathlib import Path

import pytest

from oc_remote.adb import AdbFailure
from oc_remote.catalog import VideoEntry
from oc_remote.files import (
    UncertainMutation, delete_one, move_one, query_media_row, remote_exists, rename_one,
    verify_media_index,
)
from oc_remote.transfer import TransferResult


FOLDER = "/sdcard/DCIM/OpenCamera"


class FakeAdb:
    def __init__(self):
        self.files = {"a.mp4": (4, 1.0)}
        self.media = {"a.mp4": (41, 1000)}
        self.calls = []
        self.fail = False
        self.removed = []
        self.skip_mutation = False

    async def run(self, *args, **kwargs):
        self.calls.append(args)
        if self.fail:
            raise AdbFailure("offline")
        if "find" in args:
            if "-name" in args:
                name = shlex.split(args[args.index("-name") + 1])[0]
                return f"{name}\0".encode() if name in self.files else b""
            if "0" in args and "-maxdepth" in args:
                path = shlex.split(args[3])[0]
                name = path.rsplit("/", 1)[-1]
                if name not in self.files:
                    raise AdbFailure("missing")
                size, modified = self.files[name]
                return f"{size}\0{modified}\0".encode()
            return b"".join(
                f"{name}\0{size}\0{modified}\0".encode()
                for name, (size, modified) in self.files.items()
            )
        if "content" in args and "query" in args:
            where = shlex.split(args[args.index("--where") + 1])[0]
            name = where.rsplit("/", 1)[-1].removesuffix("'").replace("''", "'")
            if name not in self.media:
                return b"No result found.\n"
            row_id, duration = self.media[name]
            path = "/storage/emulated/0/DCIM/OpenCamera/" + name
            return f"Row: 0 _id={row_id}, _data={path}, duration={duration}\n".encode()
        if "content" in args and "update" in args:
            if self.skip_mutation:
                return b""
            bind = shlex.split(args[args.index("--bind") + 1])[0]
            new_name = bind.removeprefix("_display_name:s:")
            old_name = next(iter(self.media))
            self.media[new_name] = self.media.pop(old_name)
            self.files[new_name] = self.files.pop(old_name)
            return b""
        if "content" in args and "delete" in args:
            if self.skip_mutation:
                return b""
            old_name = next(iter(self.media))
            self.media.pop(old_name)
            self.files.pop(old_name)
            self.removed.append(old_name)
            return b""
        raise AssertionError(args)


@pytest.fixture
def adb():
    return FakeAdb()


async def test_move_does_not_delete_after_failed_copy(adb, tmp_path, monkeypatch):
    async def bad_copy(*args):
        return TransferResult("a.mp4", "failed", None, "bad hash")
    monkeypatch.setattr("oc_remote.files.copy_one", bad_copy)
    result = await move_one(adb, VideoEntry("a.mp4", 4, 1.0), FOLDER, tmp_path)
    assert result.outcome == "failed"
    assert adb.removed == []
    assert "a.mp4" in adb.files


async def test_move_connection_loss_after_copy_retains_verified_pc_result(adb, tmp_path, monkeypatch):
    destination = tmp_path / "a.mp4"
    destination.write_bytes(b"data")

    async def good_copy(*args):
        adb.fail = True
        return TransferResult("a.mp4", "verified", str(destination), "verified")

    monkeypatch.setattr("oc_remote.files.copy_one", good_copy)
    result = await move_one(adb, VideoEntry("a.mp4", 4, 1.0), FOLDER, tmp_path)
    assert result.outcome == "uncertain"
    assert destination.read_bytes() == b"data"
    assert adb.removed == []


async def test_rename_preserves_extension_and_updates_index(adb):
    renamed = await rename_one(adb, VideoEntry("a.mp4", 4, 1.0), FOLDER, "اسم جديد")
    assert renamed.name == "اسم جديد.mp4"
    assert "a.mp4" not in adb.files and "اسم جديد.mp4" in adb.files
    assert "a.mp4" not in adb.media and "اسم جديد.mp4" in adb.media


async def test_rename_rejects_existing_target(adb):
    adb.files["b.mp4"] = (4, 1.0)
    adb.media["b.mp4"] = (42, 1000)
    with pytest.raises(FileExistsError):
        await rename_one(adb, VideoEntry("a.mp4", 4, 1.0), FOLDER, "b")
    assert "a.mp4" in adb.files


@pytest.mark.parametrize("confirmation", ["", "other.mp4"])
async def test_delete_requires_exact_filename_confirmation(adb, confirmation):
    with pytest.raises(ValueError):
        await delete_one(adb, VideoEntry("a.mp4", 4, 1.0), FOLDER, confirmation)
    assert adb.removed == []


async def test_delete_removes_file_and_media_row(adb):
    stages = []
    await delete_one(adb, VideoEntry("a.mp4", 4, 1.0), FOLDER, "a.mp4", progress=stages.append)
    assert adb.files == {} and adb.media == {}
    assert adb.removed == ["a.mp4"]
    assert stages == ["checking", "deleting", "verifying", "verified"]


async def test_remote_exists_distinguishes_absent_file_from_adb_failure(adb):
    assert await remote_exists(adb, FOLDER + "/a.mp4")
    adb.files.clear()
    assert not await remote_exists(adb, FOLDER + "/a.mp4")
    adb.fail = True
    with pytest.raises(AdbFailure):
        await remote_exists(adb, FOLDER + "/a.mp4")


async def test_silent_noop_mutations_are_uncertain(adb):
    adb.skip_mutation = True
    with pytest.raises(UncertainMutation):
        await rename_one(adb, VideoEntry("a.mp4", 4, 1.0), FOLDER, "b")
    stages = []
    with pytest.raises(UncertainMutation):
        await delete_one(adb, VideoEntry("a.mp4", 4, 1.0), FOLDER, "a.mp4", progress=stages.append)
    assert stages == ["checking", "deleting", "verifying", "uncertain"]


async def test_stale_source_is_not_renamed_or_deleted(adb):
    adb.files["a.mp4"] = (9, 2.0)
    with pytest.raises(UncertainMutation):
        await rename_one(adb, VideoEntry("a.mp4", 4, 1.0), FOLDER, "b")
    with pytest.raises(UncertainMutation):
        await delete_one(adb, VideoEntry("a.mp4", 4, 1.0), FOLDER, "a.mp4")
    assert "a.mp4" in adb.files


async def test_media_query_rejects_wrong_or_ambiguous_identity(adb):
    assert (await query_media_row(adb, FOLDER, "a.mp4")).duration_ms == 1000
    assert await verify_media_index(adb, old_name="absent.mp4", new_name="a.mp4", folder=FOLDER)


async def test_shell_punctuation_is_quoted_in_media_query(adb):
    name = "a; 'b'.mp4"
    adb.files = {name: (4, 1.0)}
    adb.media = {name: (41, 1000)}
    await query_media_row(adb, FOLDER, name)
    where_arg = adb.calls[-1][-1]
    assert "'\"'\"'" in where_arg
