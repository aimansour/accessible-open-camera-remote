import asyncio
from pathlib import Path

import pytest
from aiohttp.test_utils import TestClient, TestServer

from oc_remote.camera import CameraAction, CameraController, CameraStatus, CommandBusy
from oc_remote.server import FILE_LOCK_KEY, create_app
from oc_remote.state import CaptureState


class FakeController:
    def __init__(self):
        self.calls = []
        self.release = asyncio.Event()
        self.busy = False
        self.state = CaptureState.IDLE
        self.verification_enabled = True

    def status(self):
        return CameraStatus(self.state, self.verification_enabled, self.busy, "Ready", self.state)

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


async def test_real_controller_accepts_stop_before_start_dump_completes():
    held = asyncio.Event()
    dump_started = asyncio.Event()

    class Adb:
        def __init__(self):
            self.dumps = 0
            self.keys = []

        async def run(self, *args, **kwargs):
            if "find" in args:
                return b"new.mp4\x0020\x002.0\x00" if len(self.keys) == 2 else b""
            if "window" in args:
                return b"mCurrentFocus=net.sourceforge.opencamera/.MainActivity\n"
            return b"mWakefulness=Awake\n"

        async def dump_ui(self):
            self.dumps += 1
            if self.dumps == 1:
                return (b'<hierarchy><node package="net.sourceforge.opencamera" '
                        b'resource-id="net.sourceforge.opencamera:id/take_photo" '
                        b'content-desc="Start recording video"/></hierarchy>')
            if self.dumps == 2:
                dump_started.set()
                await held.wait()
            return (b'<hierarchy><node package="net.sourceforge.opencamera" '
                    b'resource-id="net.sourceforge.opencamera:id/take_photo" '
                    b'content-desc="Start recording video"/></hierarchy>')

        async def press(self, key):
            self.keys.append(key)

    class Tone:
        def success(self):
            pass

        def failure(self):
            pass

    adb = Adb()
    controller = CameraController(adb, Tone())
    await controller.start_session()
    async with TestClient(TestServer(create_app(controller, "valid"))) as http:
        first = await http.post("/api/camera", json={"action": "start"}, headers=auth(http))
        assert first.status == 202
        await asyncio.wait_for(dump_started.wait(), 1)
        second = await http.post("/api/camera", json={"action": "stop"}, headers=auth(http))
        assert second.status == 202
        payload = await second.json()
        assert payload["state"] == "idle"
        assert payload["confirmed_state"] == "idle"
        assert payload["busy"] is True
        assert payload["generation"] == 2
        held.set()
        await asyncio.sleep(0)
    await controller.stop_verification()


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
    assert http.server.app[FILE_LOCK_KEY].locked()
    release.set()
    await asyncio.sleep(0)
    assert not http.server.app[FILE_LOCK_KEY].locked()
    assert controller.tone.events == ["success"]


async def test_camera_key_bypasses_active_copy_of_captured_old_video(monkeypatch, tmp_path):
    copy_started, release_copy, key_sent, release_dump = (
        asyncio.Event() for _ in range(4)
    )

    class Adb:
        def __init__(self):
            self.dump_count = 0

        async def run(self, *args, **kwargs):
            if "find" in args:
                return b"old.mp4\x004\x001.0\x00"
            if "window" in args:
                return b"mCurrentFocus=net.sourceforge.opencamera/.MainActivity\n"
            return b"mWakefulness=Awake\n"

        async def dump_ui(self):
            self.dump_count += 1
            if self.dump_count > 1:
                await release_dump.wait()
            return (b'<hierarchy><node package="net.sourceforge.opencamera" '
                    b'resource-id="net.sourceforge.opencamera:id/take_photo" '
                    b'content-desc="Start recording video"/></hierarchy>')

        async def press(self, key):
            key_sent.set()

    class Tone:
        def success(self):
            pass

        def failure(self):
            pass

    async def held_copy(adb, entries, folder, destination, progress=None):
        assert [entry.name for entry in entries] == ["old.mp4"]
        copy_started.set()
        await release_copy.wait()
        from oc_remote.transfer import TransferResult
        return [TransferResult("old.mp4", "verified", str(destination / "old.mp4"), "verified")]

    monkeypatch.setattr("oc_remote.server.copy_many", held_copy)
    controller = CameraController(Adb(), Tone())
    await controller.start_session()
    async with TestClient(TestServer(create_app(controller, "valid"))) as http:
        response = await http.post("/api/copy", json={
            "names": ["old.mp4"], "destination": str(tmp_path),
        }, headers=auth(http))
        assert response.status == 202
        await asyncio.wait_for(copy_started.wait(), 1)
        camera = await http.post("/api/camera", json={"action": "start"}, headers=auth(http))
        assert camera.status == 202
        await asyncio.wait_for(key_sent.wait(), 1)
        assert http.server.app[FILE_LOCK_KEY].locked()
        another_mutation = await http.post("/api/rename", json={
            "name": "old.mp4", "new_stem": "new",
        }, headers=auth(http))
        assert another_mutation.status == 409
        release_copy.set()
        await asyncio.sleep(0)
    await controller.stop_verification()


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


async def test_bad_copy_json_releases_file_lock(client):
    http, _ = client
    response = await http.post("/api/copy", data="{", headers={
        **auth(http), "Content-Type": "application/json",
    })
    assert response.status == 400
    assert not http.server.app[FILE_LOCK_KEY].locked()


async def test_copy_outcome_diagnostic_uses_code_without_filename(monkeypatch, tmp_path):
    class Log:
        def __init__(self):
            self.events = []

        def record(self, event, **fields):
            self.events.append((event, fields))

    class Adb:
        async def run(self, *args, **kwargs):
            return b"private recording.mp4\x004\x001.0\x00"

    class Tone:
        def success(self):
            pass

        def failure(self):
            pass

    async def copied(*args, **kwargs):
        from oc_remote.transfer import TransferResult
        return [TransferResult("private recording.mp4", "verified", str(tmp_path / "copy"), "ok")]

    monkeypatch.setattr("oc_remote.server.copy_many", copied)
    controller, log = FakeController(), Log()
    controller.adb, controller.tone = Adb(), Tone()
    async with TestClient(TestServer(create_app(controller, "valid", diagnostics=log))) as http:
        response = await http.post("/api/copy", json={
            "names": ["private recording.mp4"], "destination": str(tmp_path),
        }, headers=auth(http))
        assert response.status == 202
        await asyncio.sleep(0)
    assert [event for event, _ in log.events] == ["copy_verified"]
    assert "private recording.mp4" not in repr(log.events)


@pytest.mark.parametrize("state,enabled", [
    (CaptureState.RECORDING, True), (CaptureState.PAUSED, True),
    (CaptureState.UNKNOWN, True), (CaptureState.UNKNOWN, False),
])
@pytest.mark.parametrize("endpoint,payload", [
    ("/api/move", {"name": "clip.mp4", "destination": "C:\\Videos"}),
    ("/api/rename", {"name": "clip.mp4", "new_stem": "new"}),
    ("/api/delete", {"name": "clip.mp4", "confirmed_name": "clip.mp4"}),
])
async def test_phone_mutations_reject_unverified_or_active_recording(client, state, enabled, endpoint, payload):
    http, controller = client
    controller.state = state
    controller.verification_enabled = enabled
    body = {"folder": "/sdcard/DCIM/OpenCamera", **payload}
    response = await http.post(endpoint, json=body, headers=auth(http))
    assert response.status == 409


async def test_delete_requires_matching_explicit_confirmation(client):
    http, controller = client

    class FakeAdb:
        async def run(self, *args, **kwargs):
            return b"clip.mp4\x004\x001.0\x00"

    controller.adb = FakeAdb()
    response = await http.post("/api/delete", json={
        "folder": "/sdcard/DCIM/OpenCamera", "name": "clip.mp4", "confirmed_name": "other.mp4",
    }, headers=auth(http))
    assert response.status == 400


async def test_delete_returns_progress_before_completion_and_conflicts_with_second_delete(client, monkeypatch):
    http, controller = client
    deleting, release = asyncio.Event(), asyncio.Event()

    class Adb:
        async def run(self, *args, **kwargs):
            return b"clip.mp4\x004\x001.0\x00"

    class Tone:
        def __init__(self):
            self.events = []

        def success(self):
            self.events.append("success")

        def failure(self):
            self.events.append("failure")

    async def held_delete(adb, entry, folder, name, progress=None):
        assert entry.name == "clip.mp4" and name == "clip.mp4"
        progress("checking")
        progress("deleting")
        deleting.set()
        await release.wait()
        progress("verifying")
        progress("verified")

    monkeypatch.setattr("oc_remote.server.delete_one", held_delete)
    controller.adb, controller.tone = Adb(), Tone()
    body = {"name": "clip.mp4", "confirmed_name": "clip.mp4"}
    response = await http.post("/api/delete", json=body, headers=auth(http))
    assert response.status == 202
    await asyncio.wait_for(deleting.wait(), 1)
    progress = await (await http.get("/api/file-operation")).json()
    assert progress["kind"] == "delete" and progress["stage"] == "deleting"
    assert progress["running"] is True and progress["id"]
    second = await http.post("/api/delete", json=body, headers=auth(http))
    assert second.status == 409
    release.set()
    for _ in range(100):
        progress = await (await http.get("/api/file-operation")).json()
        if not progress["running"]:
            break
        await asyncio.sleep(0.001)
    assert progress["stage"] == "verified"
    assert controller.tone.events == ["success"]


async def test_move_rejects_relative_destination_without_starting_transfer(client):
    http, controller = client
    response = await http.post("/api/move", json={
        "folder": "/sdcard/DCIM/OpenCamera", "name": "clip.mp4", "destination": "relative/folder",
    }, headers=auth(http))
    assert response.status == 400
    assert controller.calls == []


async def test_malformed_media_index_is_reported_as_uncertain(client):
    http, controller = client

    class FakeAdb:
        async def run(self, *args, **kwargs):
            if "content" in args:
                return b"unexpected media row\n"
            if "0" in args and "-maxdepth" in args:
                return b"4\x001.0\x00"
            return b"clip.mp4\x004\x001.0\x00"

    class FakeTone:
        def __init__(self):
            self.events = []

        def failure(self):
            self.events.append("failure")

    controller.adb = FakeAdb()
    controller.tone = FakeTone()
    response = await http.post("/api/delete", json={
        "folder": "/sdcard/DCIM/OpenCamera", "name": "clip.mp4", "confirmed_name": "clip.mp4",
    }, headers=auth(http))
    assert response.status == 202
    for _ in range(100):
        progress = await (await http.get("/api/file-operation")).json()
        if not progress["running"]:
            break
        await asyncio.sleep(0.001)
    assert progress["stage"] == "uncertain"
    assert progress["outcome"] == "uncertain"
    assert controller.tone.events == ["failure"]
