import asyncio

import pytest

from oc_remote.adb import AdbClient, AdbFailure
from oc_remote.camera import CameraAction, CameraController, CommandUnavailable
from oc_remote.catalog import VideoEntry
from oc_remote.state import CaptureState
from oc_remote.server import CAMERA_TASKS_KEY, TRANSFER_TASKS_KEY
from oc_remote.main import _stop_tasks
from oc_remote.transfer import copy_one


IDLE = (b'<hierarchy><node package="net.sourceforge.opencamera" '
        b'resource-id="net.sourceforge.opencamera:id/take_photo" '
        b'content-desc="Start recording video"/></hierarchy>')
RECORDING = (b'<hierarchy><node package="net.sourceforge.opencamera" '
             b'resource-id="net.sourceforge.opencamera:id/take_photo" '
             b'content-desc="Stop recording video"/><node '
             b'package="net.sourceforge.opencamera" '
             b'resource-id="net.sourceforge.opencamera:id/pause_video" '
             b'content-desc="Pause video recording"/></hierarchy>')


class Tone:
    def __init__(self):
        self.events = []

    def success(self):
        self.events.append("success")

    def failure(self):
        self.events.append("failure")


class CameraAdb:
    def __init__(self):
        self.dumps = [IDLE]
        self.keys = []

    async def run(self, *args, **kwargs):
        return (b'mCurrentFocus=net.sourceforge.opencamera/.MainActivity\n'
                if "window" in args else b'mWakefulness=Awake\n')

    async def dump_ui(self):
        value = self.dumps.pop(0)
        if isinstance(value, Exception):
            raise value
        return value

    async def press(self, key):
        self.keys.append(key)


async def test_lost_connection_after_key_requires_fresh_state_before_retry():
    adb, tone = CameraAdb(), Tone()
    controller = CameraController(adb, tone)
    assert (await controller.start_session()).state is CaptureState.IDLE
    adb.dumps.append(AdbFailure("offline"))
    result = await controller.submit(CameraAction.START)
    assert result.state is CaptureState.UNKNOWN
    assert adb.keys == [24]
    assert tone.events == ["failure"]
    with pytest.raises(CommandUnavailable):
        controller.submit(CameraAction.START)
    adb.dumps.append(RECORDING)
    assert (await controller.start_verification()).state is CaptureState.RECORDING
    assert adb.keys == [24]


async def test_camera_diagnostics_use_event_codes_only():
    class Log:
        def __init__(self):
            self.events = []

        def record(self, event, **fields):
            self.events.append((event, fields))

    adb, tone, log = CameraAdb(), Tone(), Log()
    controller = CameraController(adb, tone, diagnostics=log)
    await controller.start_session()
    adb.dumps.append(AdbFailure("secret phone output"))
    await controller.submit(CameraAction.START)
    assert [event for event, _ in log.events] == ["camera_verified", "camera_uncertain"]
    assert "secret phone output" not in repr(log.events)


async def test_restart_requires_fresh_phone_state():
    adb, tone = CameraAdb(), Tone()
    controller = CameraController(adb, tone)
    assert controller.status().state is CaptureState.UNKNOWN
    with pytest.raises(CommandUnavailable):
        controller.submit(CameraAction.START)
    assert (await controller.start_session()).state is CaptureState.IDLE


class PartialAdb:
    async def run(self, *args, **kwargs):
        if "find" in args:
            return b"4\0" + b"1.0\0"
        raise AssertionError(args)

    async def pull(self, remote, local):
        local.write_bytes(b"da")
        raise AdbFailure("offline during pull")


async def test_disconnect_mid_pull_removes_incomplete_pc_file(tmp_path):
    result = await copy_one(PartialAdb(), VideoEntry("clip.mp4", 4, 1.0),
                            "/sdcard/DCIM/OpenCamera", tmp_path)
    assert result.outcome == "failed"
    assert not (tmp_path / "clip.mp4").exists()
    assert list(tmp_path.glob("*.partial")) == []


async def test_cancelling_active_adb_stops_its_child_process(monkeypatch):
    started = asyncio.Event()

    class Process:
        returncode = None

        def __init__(self):
            self.killed = False

        async def communicate(self):
            started.set()
            if not self.killed:
                await asyncio.Event().wait()
            return b"", b""

        def kill(self):
            self.killed = True

    process = Process()

    async def create(*args, **kwargs):
        return process

    monkeypatch.setattr("oc_remote.adb.asyncio.create_subprocess_exec", create)
    adb = AdbClient("phone-serial", "adb")
    task = asyncio.create_task(adb.run("pull", "file", "partial"))
    await asyncio.wait_for(started.wait(), 0.5)
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)
    assert process.killed


async def test_service_shutdown_waits_for_camera_and_transfer_jobs():
    entered = asyncio.Event()
    stopped = []

    async def job(name):
        entered.set()
        try:
            await asyncio.Event().wait()
        finally:
            stopped.append(name)

    camera = asyncio.create_task(job("camera"))
    transfer = asyncio.create_task(job("transfer"))
    await entered.wait()
    await asyncio.sleep(0)
    await _stop_tasks({CAMERA_TASKS_KEY: {camera}, TRANSFER_TASKS_KEY: {transfer}})
    assert set(stopped) == {"camera", "transfer"}


async def test_shutdown_cancels_camera_key_sender_before_it_finishes():
    entered, release = asyncio.Event(), asyncio.Event()

    class HeldAdb(CameraAdb):
        async def press(self, key):
            entered.set()
            await release.wait()
            self.keys.append(key)

    adb, tone = HeldAdb(), Tone()
    controller = CameraController(adb, tone)
    await controller.start_session()
    completion = controller.submit(CameraAction.START)
    await entered.wait()
    await _stop_tasks({CAMERA_TASKS_KEY: {completion}, TRANSFER_TASKS_KEY: set()}, controller)
    release.set()
    await asyncio.sleep(0)
    assert adb.keys == []
    assert controller.status().state is CaptureState.UNKNOWN
