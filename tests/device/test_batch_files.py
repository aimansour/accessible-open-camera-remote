"""Opt-in batch API gate; touches only random videos created here."""

import asyncio
import hashlib
import os
import shlex
import shutil
import subprocess
from pathlib import Path
from urllib.parse import quote
from uuid import uuid4

import pytest
from aiohttp.test_utils import TestClient, TestServer

from oc_remote.adb import AdbClient
from oc_remote.camera import CameraAction, CameraController, CameraStatus
from oc_remote.catalog import DEFAULT_PHONE_FOLDER
from oc_remote.files import media_path, query_media_row, remote_exists
from oc_remote.server import create_app
from oc_remote.state import CaptureState


@pytest.mark.skipif(os.getenv("OC_DEVICE_TEST") != "1", reason="device test is opt-in")
async def test_batch_delete_copy_and_move_only_created_videos(tmp_path):
    serial = os.getenv("OC_DEVICE_SERIAL")
    executable, ffmpeg = shutil.which("adb"), shutil.which("ffmpeg")
    if not serial or not executable or not ffmpeg:
        pytest.fail("Set OC_DEVICE_SERIAL and install ADB and ffmpeg")

    class Tone:
        def __init__(self):
            self.events = []

        def success(self):
            self.events.append("success")

        def failure(self):
            self.events.append("failure")

    class ObservedAdb(AdbClient):
        def __init__(self):
            super().__init__(serial, Path(executable))
            self.key_sent = asyncio.Event()

        async def press(self, keycode):
            await super().press(keycode)
            self.key_sent.set()

    class Controller:
        def __init__(self):
            self.adb = ObservedAdb()
            self.tone = Tone()
            self.camera = CameraController(self.adb, Tone())

        def status(self):
            return CameraStatus(CaptureState.IDLE, True, False, "Test session", CaptureState.IDLE)

        def submit(self, action):
            return self.camera.submit(action)

    controller = Controller()
    assert (await controller.camera.start_session()).state is CaptureState.IDLE
    marker = f"oc_remote_batch_test_{uuid4().hex}"
    delete_names = [f"{marker}_delete_{i}.mp4" for i in range(3)]
    move_names = [f"{marker}_move_{i}.mp4" for i in range(4)]
    names = delete_names + move_names

    async def scan(name):
        uri = "file://" + quote(media_path(DEFAULT_PHONE_FOLDER, name), safe="/")
        await controller.adb.run(
            "shell", "am", "broadcast", "-a", "android.intent.action.MEDIA_SCANNER_SCAN_FILE",
            "-d", shlex.quote(uri), timeout=10,
        )

    async def wait_job(http, endpoint):
        for _ in range(120):
            job = await (await http.get(endpoint)).json()
            if not job["running"]:
                return job
            await asyncio.sleep(0.25)
        pytest.fail(f"Batch job did not finish: {endpoint}")

    try:
        for name in names:
            local = tmp_path / name
            subprocess.run(
                [ffmpeg, "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
                 "color=c=black:s=32x32:d=1", "-c:v", "mpeg4", "-t", "1", "-y", str(local)],
                check=True, capture_output=True, timeout=30,
            )
            await controller.adb.run("push", str(local), f"{DEFAULT_PHONE_FOLDER}/{name}", timeout=30)
            await scan(name)
        for _ in range(10):
            if all([await query_media_row(controller.adb, DEFAULT_PHONE_FOLDER, name) is not None
                    for name in names]):
                break
            await asyncio.sleep(0.5)
        else:
            pytest.fail("Android did not index all random test videos")

        async with TestClient(TestServer(create_app(controller, "batch-test-token"))) as http:
            headers = {"Origin": str(http.make_url("/")).rstrip("/"),
                       "X-Session-Token": "batch-test-token"}
            deleted = await http.post("/api/delete", json={
                "names": delete_names, "confirmed_names": delete_names,
            }, headers=headers)
            assert deleted.status == 202
            delete_job = await wait_job(http, "/api/file-operation")
            assert delete_job["outcome"] == "verified"
            assert delete_job["completed"] == delete_job["total"] == 3
            assert controller.tone.events == ["success"]
            for name in delete_names:
                assert not await remote_exists(controller.adb, f"{DEFAULT_PHONE_FOLDER}/{name}")
                assert await query_media_row(controller.adb, DEFAULT_PHONE_FOLDER, name) is None

            copied = await http.post("/api/copy", json={
                "names": move_names, "destination": str(tmp_path / "copied"),
            }, headers=headers)
            assert copied.status == 202
            copy_job = await wait_job(http, "/api/transfers")
            assert copy_job["kind"] == "copy"
            assert copy_job["completed"] == copy_job["total"] == 4
            assert {result["name"]: result["outcome"] for result in copy_job["results"]} == {
                name: "verified" for name in move_names
            }
            assert controller.tone.events == ["success", "success"]
            for name in move_names:
                original = (tmp_path / name).read_bytes()
                pc_copy = (tmp_path / "copied" / name).read_bytes()
                assert hashlib.sha256(original).digest() == hashlib.sha256(pc_copy).digest()
                assert await remote_exists(controller.adb, f"{DEFAULT_PHONE_FOLDER}/{name}")
                assert await query_media_row(controller.adb, DEFAULT_PHONE_FOLDER, name) is not None

            moved = await http.post("/api/move", json={
                "names": move_names, "destination": str(tmp_path / "pc"),
            }, headers=headers)
            assert moved.status == 202
            started_camera = await http.post("/api/camera", json={"action": "start"},
                                             headers=headers)
            assert started_camera.status == 202
            await asyncio.wait_for(controller.adb.key_sent.wait(), 10)
            moving = await (await http.get("/api/transfers")).json()
            assert moving["running"] is True
            await asyncio.sleep(0.7)
            stopped_camera = await http.post("/api/camera", json={"action": "stop"},
                                             headers=headers)
            assert stopped_camera.status == 202
            move_job = await wait_job(http, "/api/transfers")
            assert move_job["kind"] == "move"
            assert move_job["completed"] == move_job["total"] == 4
            assert {result["name"]: result["outcome"] for result in move_job["results"]} == {
                name: "verified" for name in move_names
            }
            assert controller.tone.events == ["success", "success", "success"]
            for name in move_names:
                assert (tmp_path / "pc" / name).is_file()
                assert hashlib.sha256((tmp_path / name).read_bytes()).digest() == hashlib.sha256(
                    (tmp_path / "pc" / name).read_bytes()).digest()
                assert not await remote_exists(controller.adb, f"{DEFAULT_PHONE_FOLDER}/{name}")
                assert await query_media_row(controller.adb, DEFAULT_PHONE_FOLDER, name) is None
            for _ in range(120):
                camera_status = controller.camera.status()
                if camera_status.state is CaptureState.IDLE and not camera_status.busy:
                    break
                await asyncio.sleep(0.25)
            else:
                pytest.fail("Camera did not settle to idle after the concurrent move")

    finally:
        try:
            if controller.camera.status().state in (CaptureState.RECORDING, CaptureState.PAUSED):
                await controller.camera.submit(CameraAction.STOP)
            await controller.camera.stop_verification()
        finally:
            for name in names:
                await controller.adb.run("shell", "rm", "-f",
                                         shlex.quote(f"{DEFAULT_PHONE_FOLDER}/{name}"), timeout=10)
                await scan(name)
