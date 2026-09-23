import subprocess
from pathlib import Path

import pytest

from oc_remote.adb import AdbClient, AdbFailure, AdbTimeout


class FakeProcess:
    def __init__(self):
        self.calls = []
        self.fail_at = None
        self.timeout_at = None

    def __call__(self, args, **kwargs):
        self.calls.append(tuple(args))
        if len(self.calls) == self.timeout_at:
            raise subprocess.TimeoutExpired(args, kwargs["timeout"])
        if len(self.calls) == self.fail_at:
            return subprocess.CompletedProcess(args, 1, b"", b"offline")
        return subprocess.CompletedProcess(args, 0, b"<hierarchy/>", b"")


@pytest.fixture
def fake_process():
    return FakeProcess()


async def test_press_targets_selected_phone(fake_process):
    adb = AdbClient("phone-serial", Path("adb"), runner=fake_process)
    await adb.press(24)
    assert fake_process.calls[0][:4] == ("adb", "-s", "phone-serial", "shell")
    assert fake_process.calls[0][4:] == ("input", "keyevent", "24")


async def test_invalid_key_never_runs(fake_process):
    adb = AdbClient("phone-serial", Path("adb"), runner=fake_process)
    with pytest.raises(ValueError):
        await adb.press(26)
    assert fake_process.calls == []


async def test_timeout_is_distinct(fake_process):
    fake_process.timeout_at = 1
    adb = AdbClient("phone-serial", Path("adb"), runner=fake_process)
    with pytest.raises(AdbTimeout):
        await adb.run("devices", timeout=1)


async def test_nonzero_exit_is_failure(fake_process):
    fake_process.fail_at = 1
    adb = AdbClient("phone-serial", Path("adb"), runner=fake_process)
    with pytest.raises(AdbFailure):
        await adb.run("devices")


@pytest.mark.parametrize("fail_at", [None, 2])
async def test_dump_always_removes_temporary_file(fake_process, fail_at):
    fake_process.fail_at = fail_at
    adb = AdbClient("phone-serial", Path("adb"), runner=fake_process)
    if fail_at:
        with pytest.raises(AdbFailure):
            await adb.dump_ui()
    else:
        assert await adb.dump_ui() == b"<hierarchy/>"
    assert len(fake_process.calls) == 3
    dump_path = fake_process.calls[0][-1]
    assert dump_path.startswith("/data/local/tmp/") and dump_path.endswith(".xml")
    assert fake_process.calls[1][-1] == dump_path
    assert fake_process.calls[2][-1] == dump_path
