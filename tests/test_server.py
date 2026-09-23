import asyncio
from pathlib import Path

import pytest
from aiohttp.test_utils import TestClient, TestServer

from oc_remote.camera import CameraAction, CameraStatus, CommandBusy
from oc_remote.server import create_app
from oc_remote.state import CaptureState


class FakeController:
    def __init__(self):
        self.calls = []
        self.release = asyncio.Event()
        self.busy = False

    def status(self):
        return CameraStatus(CaptureState.IDLE, True, self.busy, "Ready")

    def submit(self, action):
        if self.busy:
            raise CommandBusy
        self.busy = True
        self.calls.append(action)

        async def wait():
            await self.release.wait()
            self.busy = False
            return self.status()

        return asyncio.create_task(wait())

    async def stop_verification(self):
        return self.status()

    async def start_verification(self):
        return self.status()


@pytest.fixture
async def client():
    controller = FakeController()
    async with TestClient(TestServer(create_app(controller, "valid"))) as test_client:
        yield test_client, controller
        controller.release.set()


def auth(client):
    origin = str(client.make_url("/")).rstrip("/")
    return {"Origin": origin, "X-Session-Token": "valid"}


async def test_cross_origin_request_cannot_press_camera(client):
    http, controller = client
    response = await http.post(
        "/api/camera",
        json={"action": "start"},
        headers={"Origin": "https://other.example", "X-Session-Token": "valid"},
    )
    assert response.status == 403
    assert controller.calls == []


@pytest.mark.parametrize("token", [None, "wrong"])
async def test_missing_or_wrong_token_is_rejected(client, token):
    http, controller = client
    headers = auth(http)
    if token is None:
        del headers["X-Session-Token"]
    else:
        headers["X-Session-Token"] = token
    response = await http.post("/api/camera", json={"action": "start"}, headers=headers)
    assert response.status == 403
    assert controller.calls == []


async def test_command_returns_before_verification_and_second_request_conflicts(client):
    http, controller = client
    first = await http.post("/api/camera", json={"action": "start"}, headers=auth(http))
    assert first.status == 202
    assert controller.busy
    second = await http.post("/api/camera", json={"action": "start"}, headers=auth(http))
    assert second.status == 409
    assert controller.calls == [CameraAction.START]


async def test_status_is_readable_without_token(client):
    http, _ = client
    response = await http.get("/api/status")
    assert response.status == 200
    assert (await response.json())["state"] == "idle"


async def test_page_serves_session_token_and_web_assets(client):
    http, _ = client
    page = await http.get("/")
    assert page.status == 200
    page_html = await page.text()
    assert '<meta name="session-token" content="valid">' in page_html
    assert "__PC_FOLDER__" not in page_html
    assert str(Path.home() / "Videos" / "OpenCameraRemote") in page_html
    script = await http.get("/app.js")
    assert script.status == 200
    assert "renderCamera" in await script.text()


async def test_video_catalog_returns_selected_folder_entries(client):
    http, controller = client

    class FakeAdb:
        async def run(self, *args, **kwargs):
            return b"clip.mp4\x004\x001700000000\x00"

    controller.adb = FakeAdb()
    response = await http.get("/api/videos?folder=/sdcard/DCIM/OpenCamera")
    assert response.status == 200
    assert (await response.json())["videos"][0]["name"] == "clip.mp4"


async def test_catalog_rejects_folder_outside_shared_storage(client):
    http, _ = client
    response = await http.get("/api/videos?folder=/data/local/tmp")
    assert response.status == 400


async def test_copy_batch_returns_202_and_reports_progress(client, monkeypatch, tmp_path):
    http, controller = client
    release = asyncio.Event()

    class FakeAdb:
        async def run(self, *args, **kwargs):
            return b"clip.mp4\x004\x001.0\x00"

    class FakeTone:
        def __init__(self):
            self.events = []

        def success(self):
            self.events.append("success")

        def failure(self):
            self.events.append("failure")

    async def fake_copy_many(adb, entries, folder, pc_folder, progress=None):
        progress("clip.mp4", "copying")
        await release.wait()
        from oc_remote.transfer import TransferResult
        return [TransferResult("clip.mp4", "verified", str(pc_folder / "clip.mp4"), "verified")]

    controller.adb = FakeAdb()
    controller.tone = FakeTone()
    monkeypatch.setattr("oc_remote.server.copy_many", fake_copy_many)
    response = await http.post("/api/copy", json={
        "names": ["clip.mp4"], "folder": "/sdcard/DCIM/OpenCamera", "destination": str(tmp_path),
    }, headers=auth(http))
    assert response.status == 202
    status = await http.get("/api/transfers")
    assert (await status.json())["total"] == 1
    release.set()
    await asyncio.sleep(0)
    assert controller.tone.events == ["success"]


async def test_copy_rejects_unlisted_name(client, tmp_path):
    http, controller = client

    class FakeAdb:
        async def run(self, *args, **kwargs):
            return b"clip.mp4\x004\x001.0\x00"

    controller.adb = FakeAdb()
    response = await http.post("/api/copy", json={
        "names": ["other.mp4"], "folder": "/sdcard/DCIM/OpenCamera", "destination": str(tmp_path),
    }, headers=auth(http))
    assert response.status == 400
