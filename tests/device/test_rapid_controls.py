"""Opt-in rapid-control gate on the selected phone; keeps the recorded clip."""

import asyncio
import os
import shlex
import shutil
import subprocess
import time
from pathlib import Path
from uuid import uuid4

import pytest

from oc_remote.adb import AdbClient
from oc_remote.camera import CameraAction, CameraController
from oc_remote.catalog import DEFAULT_PHONE_FOLDER
from oc_remote.recording_evidence import snapshot
from oc_remote.state import CaptureState
from oc_remote.transfer import copy_one


class TimedAdb(AdbClient):
    def __init__(self, serial, executable):
        super().__init__(serial, executable)
        self.key_completions = []
        self.dump_completions = []
        self.first_key_completed = asyncio.Event()

    async def press(self, keycode):
        await super().press(keycode)
        self.key_completions.append(time.perf_counter())
        self.first_key_completed.set()

    async def dump_ui(self):
        result = await super().dump_ui()
        self.dump_completions.append(time.perf_counter())
        return result


class RecordingTone:
    def __init__(self):
        self.events = []

    def success(self):
        self.events.append("success")

    def failure(self):
        self.events.append("failure")


@pytest.mark.skipif(os.getenv("OC_DEVICE_TEST") != "1", reason="device test is opt-in")
async def test_rapid_start_stop_verifies_one_finalized_video():
    serial = os.getenv("OC_DEVICE_SERIAL")
    if not serial:
        pytest.fail("Set OC_DEVICE_SERIAL to the exact connected ADB serial")
    executable = shutil.which("adb")
    if not executable:
        pytest.fail("ADB is required for this gated test")
    adb = TimedAdb(serial, Path(executable))
    tone = RecordingTone()
    controller = CameraController(adb, tone)
    initial = await controller.start_session()
    assert initial.confirmed_state is CaptureState.IDLE, initial.message
    baseline = await snapshot(adb, DEFAULT_PHONE_FOLDER)
    try:
        started_at = time.perf_counter()
        start = controller.submit(CameraAction.START)
        await asyncio.wait_for(adb.first_key_completed.wait(), 5)
        await asyncio.sleep(0.7)
        stop = controller.submit(CameraAction.STOP)
        results = await asyncio.wait_for(asyncio.gather(start, stop), 25)
        settled_at = time.perf_counter()

        assert len(adb.key_completions) == 2
        assert len(adb.dump_completions) >= 2
        assert adb.key_completions[1] < adb.dump_completions[-1]
        assert all(result.confirmed_state is CaptureState.IDLE for result in results)
        assert tone.events == ["success"]
        after = await snapshot(adb, DEFAULT_PHONE_FOLDER)
        assert any(
            entry.name.lower().endswith(".mp4") and entry.size > 0
            and baseline.get(entry.name) != entry
            for entry in after.values()
        )
        print(f"rapid keys complete: {adb.key_completions[1] - started_at:.3f}s; "
              f"final dump: {adb.dump_completions[-1] - started_at:.3f}s; "
              f"verified: {settled_at - started_at:.3f}s; one result tone")
    finally:
        await controller.stop_verification()


@pytest.mark.skipif(os.getenv("OC_DEVICE_TEST") != "1", reason="device test is opt-in")
async def test_camera_keys_continue_while_old_test_video_copy_is_held(tmp_path):
    serial = os.getenv("OC_DEVICE_SERIAL")
    executable, ffmpeg = shutil.which("adb"), shutil.which("ffmpeg")
    if not serial or not executable or not ffmpeg:
        pytest.fail("Set OC_DEVICE_SERIAL and install ADB and ffmpeg")

    class HeldPullAdb(AdbClient):
        def __init__(self):
            super().__init__(serial, Path(executable))
            self.entered = asyncio.Event()
            self.release = asyncio.Event()

        async def pull(self, remote, local):
            self.entered.set()
            await self.release.wait()
            await super().pull(remote, local)

    marker = f"oc_remote_priority_test_{uuid4().hex}.mp4"
    local = tmp_path / marker
    subprocess.run([ffmpeg, "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
                    "color=c=black:s=32x32:d=1", "-c:v", "mpeg4", "-t", "1", "-y", str(local)],
                   check=True, capture_output=True, timeout=30)
    remote = f"{DEFAULT_PHONE_FOLDER}/{marker}"
    copy_adb = HeldPullAdb()
    camera_adb = TimedAdb(serial, Path(executable))
    tone = RecordingTone()
    controller = CameraController(camera_adb, tone)
    copy_task = None
    try:
        await copy_adb.run("push", str(local), remote, timeout=30)
        entry = (await snapshot(copy_adb, DEFAULT_PHONE_FOLDER))[marker]
        assert (await controller.start_session()).confirmed_state is CaptureState.IDLE
        copy_task = asyncio.create_task(copy_one(copy_adb, entry, DEFAULT_PHONE_FOLDER, tmp_path / "pc"))
        await asyncio.wait_for(copy_adb.entered.wait(), 5)
        start = controller.submit(CameraAction.START)
        await asyncio.wait_for(camera_adb.first_key_completed.wait(), 5)
        assert not copy_task.done()
        await asyncio.sleep(0.7)
        stop = controller.submit(CameraAction.STOP)
        for _ in range(100):
            if len(camera_adb.key_completions) == 2:
                break
            await asyncio.sleep(0.05)
        assert len(camera_adb.key_completions) == 2
        assert not copy_task.done()
        copy_adb.release.set()
        copied = await asyncio.wait_for(copy_task, 20)
        assert copied.outcome == "verified"
        await asyncio.wait_for(asyncio.gather(start, stop), 25)
        assert controller.status().confirmed_state is CaptureState.IDLE
        assert tone.events == ["success"]
        print("Both camera keys completed while the random test video copy was held")
    finally:
        copy_adb.release.set()
        if copy_task is not None:
            await asyncio.gather(copy_task, return_exceptions=True)
        await controller.stop_verification()
        await copy_adb.run("shell", "rm", "-f", shlex.quote(remote), timeout=10)
