import asyncio

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
    assert '<meta name="session-token" content="valid">' in await page.text()
    script = await http.get("/app.js")
    assert script.status == 200
    assert "renderCamera" in await script.text()
