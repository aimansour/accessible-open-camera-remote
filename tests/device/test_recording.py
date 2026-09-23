"""Opt-in real phone gate. Never runs during the normal test suite."""

import os
import shutil
import time
from pathlib import Path

import pytest

from oc_remote.adb import AdbClient
from oc_remote.camera import CameraAction, CameraController
from oc_remote.state import CaptureState, parse_dump


class SilentTone:
    def success(self):
        pass

    def failure(self):
        pass


class TimedAdb(AdbClient):
    def __init__(self, serial, executable):
        super().__init__(serial, executable)
        self.press_started = None
        self.press_completed = None

    async def press(self, keycode):
        self.press_started = time.perf_counter()
        await super().press(keycode)
        self.press_completed = time.perf_counter()


@pytest.mark.skipif(os.getenv("OC_DEVICE_TEST") != "1", reason="device test is opt-in")
async def test_real_recording_cycle():
    serial = os.getenv("OC_DEVICE_SERIAL")
    if not serial:
        pytest.fail("Set OC_DEVICE_SERIAL to the exact connected ADB serial")
    executable = shutil.which("adb")
    if not executable:
        pytest.fail("ADB is not installed or is not on PATH")
    adb = TimedAdb(serial, Path(executable))
    controller = CameraController(adb, SilentTone())

    async def observe(label, operation, expected):
        started = time.perf_counter()
        status = await operation()
        completed = time.perf_counter()
        elapsed = completed - started
        snapshot = parse_dump(await adb.dump_ui())
        print(f"{label}: state={status.state.value}, elapsed={elapsed:.3f}s, "
              f"take={snapshot.take_description!r}, pause={snapshot.pause_description!r}")
        if label != "initial":
            print(f"{label} timing: before-key={adb.press_started - started:.3f}s, "
                  f"key-command={adb.press_completed - adb.press_started:.3f}s, "
                  f"key-to-verified={completed - adb.press_completed:.3f}s")
        assert status.state is expected, status.message

    await observe("initial", controller.start_session, CaptureState.IDLE)
    await observe("start", lambda: controller.submit(CameraAction.START), CaptureState.RECORDING)
    await observe("pause", lambda: controller.submit(CameraAction.PAUSE), CaptureState.PAUSED)
    await observe("resume", lambda: controller.submit(CameraAction.RESUME), CaptureState.RECORDING)
    await observe("stop", lambda: controller.submit(CameraAction.STOP), CaptureState.IDLE)
