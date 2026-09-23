import asyncio
import hashlib
from pathlib import Path

import pytest

from oc_remote.adb import AdbFailure
from oc_remote.catalog import VideoEntry
from oc_remote.transfer import copy_many, copy_one, publish_without_overwrite


PHONE = "/sdcard/DCIM/OpenCamera"


class FakeAdb:
    def __init__(self):
        self.data = b"data"
        self.remote_hash = hashlib.sha256(self.data).hexdigest()
        self.changed_after_pull = False
        self.disconnect_after_pull = False
        self.pulled = False
        self.calls = []
        self.removed = []
        self.fail_name = None

    async def run(self, *args, **kwargs):
        self.calls.append(args)
        if self.disconnect_after_pull and self.pulled:
            raise AdbFailure("offline")
        if "find" in args:
            modified = b"2.0" if self.changed_after_pull and self.pulled else b"1.0"
            return b"4\x00" + modified + b"\x00"
        if "sha256sum" in args:
            if self.fail_name and self.fail_name in " ".join(args):
                return ("0" * 64).encode() + b"\n"
            return self.remote_hash.encode() + b"\n"
        raise AssertionError(args)

    async def pull(self, remote, local):
        self.calls.append(("pull", remote, str(local)))
        Path(local).write_bytes(self.data)
        self.pulled = True


@pytest.fixture
def fake_adb():
    return FakeAdb()


async def test_good_copy_publishes_exact_bytes(fake_adb, tmp_path):
    result = await copy_one(fake_adb, VideoEntry("clip.mp4", 4, 1.0), PHONE, tmp_path)
    assert result.outcome == "verified"
    assert (tmp_path / "clip.mp4").read_bytes() == b"data"
    assert not list(tmp_path.glob("*.partial"))
    assert fake_adb.removed == []


async def test_bad_hash_never_publishes_destination(fake_adb, tmp_path):
    fake_adb.remote_hash = "0" * 64
    result = await copy_one(fake_adb, VideoEntry("clip.mp4", 4, 1.0), PHONE, tmp_path)
    assert result.outcome == "failed"
    assert not (tmp_path / "clip.mp4").exists()
    assert not list(tmp_path.glob("*.partial"))
    assert fake_adb.removed == []


async def test_source_change_after_pull_keeps_phone_source(fake_adb, tmp_path):
    fake_adb.changed_after_pull = True
    result = await copy_one(fake_adb, VideoEntry("clip.mp4", 4, 1.0), PHONE, tmp_path)
    assert result.outcome == "failed"
    assert not (tmp_path / "clip.mp4").exists()
    assert fake_adb.removed == []


async def test_remote_disconnect_cleans_partial_and_never_publishes(fake_adb, tmp_path):
    fake_adb.disconnect_after_pull = True
    result = await copy_one(fake_adb, VideoEntry("clip.mp4", 4, 1.0), PHONE, tmp_path)
    assert result.outcome == "failed"
    assert not (tmp_path / "clip.mp4").exists()
    assert not list(tmp_path.glob("*.partial"))


async def test_existing_destination_is_never_overwritten(fake_adb, tmp_path):
    (tmp_path / "clip.mp4").write_bytes(b"original")
    result = await copy_one(fake_adb, VideoEntry("clip.mp4", 4, 1.0), PHONE, tmp_path)
    assert result.outcome == "failed"
    assert (tmp_path / "clip.mp4").read_bytes() == b"original"


async def test_publish_refuses_existing_name(tmp_path):
    partial = tmp_path / "x.partial"
    target = tmp_path / "x.mp4"
    partial.write_bytes(b"new")
    target.write_bytes(b"old")
    with pytest.raises(FileExistsError):
        publish_without_overwrite(partial, target)
    assert target.read_bytes() == b"old"


@pytest.mark.parametrize("name,folder", [("../bad.mp4", PHONE), ("clip.mp4", "/data/local/tmp")])
async def test_traversal_or_outside_phone_folder_is_rejected(fake_adb, tmp_path, name, folder):
    result = await copy_one(fake_adb, VideoEntry(name, 4, 1.0), folder, tmp_path)
    assert result.outcome == "failed"
    assert fake_adb.calls == []


async def test_shell_punctuation_is_quoted(fake_adb, tmp_path):
    name = "clip; touch bad 'quote'.mp4"
    result = await copy_one(fake_adb, VideoEntry(name, 4, 1.0), PHONE, tmp_path)
    assert result.outcome == "verified"
    assert any("'\"'\"'" in " ".join(call) for call in fake_adb.calls if call[0] == "shell")


async def test_batch_continues_after_one_bad_hash(fake_adb, tmp_path):
    fake_adb.fail_name = "b.mp4"
    entries = [VideoEntry(name, 4, 1.0) for name in ("a.mp4", "b.mp4", "c.mp4")]
    results = await copy_many(fake_adb, entries, PHONE, tmp_path)
    assert [item.outcome for item in results] == ["verified", "failed", "verified"]
    assert (tmp_path / "a.mp4").exists()
    assert not (tmp_path / "b.mp4").exists()
    assert (tmp_path / "c.mp4").exists()


async def test_copy_batch_uses_two_workers_and_keeps_result_order(monkeypatch, tmp_path):
    started = {name: asyncio.Event() for name in ("a.mp4", "b.mp4", "c.mp4", "d.mp4")}
    release = {name: asyncio.Event() for name in started}

    async def held_copy(adb, entry, phone_folder, pc_folder, progress=None):
        from oc_remote.transfer import TransferResult
        started[entry.name].set()
        await release[entry.name].wait()
        return TransferResult(entry.name, "verified", str(pc_folder / entry.name), "verified")

    monkeypatch.setattr("oc_remote.transfer.copy_one", held_copy)
    entries = [VideoEntry(name, 4, 1.0) for name in started]
    task = asyncio.create_task(copy_many(object(), entries, PHONE, tmp_path))
    try:
        await asyncio.wait_for(asyncio.gather(started["a.mp4"].wait(), started["b.mp4"].wait()), 1)
        assert not started["c.mp4"].is_set() and not started["d.mp4"].is_set()
        release["a.mp4"].set()
        await asyncio.wait_for(started["c.mp4"].wait(), 1)
        assert not started["d.mp4"].is_set()
        release["b.mp4"].set()
        await asyncio.wait_for(started["d.mp4"].wait(), 1)
    finally:
        for event in release.values():
            event.set()
    results = await asyncio.wait_for(task, 1)
    assert [result.name for result in results] == ["a.mp4", "b.mp4", "c.mp4", "d.mp4"]
