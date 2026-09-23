"""Loopback HTTP API for the browser controls."""

from dataclasses import asdict
from html import escape
from pathlib import Path

from aiohttp import web

from .camera import CameraAction, CommandBusy, CommandUnavailable


CONTROLLER_KEY = web.AppKey("controller", object)
SESSION_TOKEN_KEY = web.AppKey("session_token", str)
CAMERA_TASKS_KEY = web.AppKey("camera_tasks", set)
WEB_DIR = Path(__file__).resolve().parent / "web"


def require_local_host(request: web.Request) -> str:
    sockname = request.transport.get_extra_info("sockname") if request.transport else None
    if not sockname or sockname[0] != "127.0.0.1":
        raise web.HTTPForbidden(text="Local service only")
    expected_host = f"127.0.0.1:{sockname[1]}"
    if request.host != expected_host or request.remote != "127.0.0.1":
        raise web.HTTPForbidden(text="Invalid local host")
    return expected_host


def require_local_origin_and_token(request: web.Request) -> None:
    expected_host = require_local_host(request)
    if request.headers.get("Origin") != f"http://{expected_host}":
        raise web.HTTPForbidden(text="Invalid request origin")
    if request.headers.get("X-Session-Token") != request.app[SESSION_TOKEN_KEY]:
        raise web.HTTPForbidden(text="Invalid session token")


def create_app(controller, token: str) -> web.Application:
    if not token:
        raise ValueError("A session token is required")
    app = web.Application()
    app[CONTROLLER_KEY] = controller
    app[SESSION_TOKEN_KEY] = token
    app[CAMERA_TASKS_KEY] = set()

    async def page(request):
        require_local_host(request)
        html = (WEB_DIR / "index.html").read_text(encoding="utf-8")
        html = html.replace("__SESSION_TOKEN__", escape(token, quote=True))
        return web.Response(text=html, content_type="text/html", charset="utf-8",
                            headers={"Cache-Control": "no-store"})

    async def asset(request):
        require_local_host(request)
        name = request.match_info["name"]
        return web.FileResponse(WEB_DIR / name, headers={"Cache-Control": "no-store"})

    async def status(request):
        require_local_host(request)
        return web.json_response(asdict(controller.status()))

    async def post_camera(request):
        require_local_origin_and_token(request)
        try:
            payload = await request.json()
            action = CameraAction(payload["action"])
        except (ValueError, KeyError, TypeError):
            raise web.HTTPBadRequest(text="Invalid camera action")
        try:
            task = controller.submit(action)
        except CommandBusy:
            raise web.HTTPConflict(text="Camera command already in progress")
        except CommandUnavailable:
            raise web.HTTPConflict(text="Verify camera state before this command")
        app[CAMERA_TASKS_KEY].add(task)
        task.add_done_callback(app[CAMERA_TASKS_KEY].discard)
        return web.json_response({"accepted": True}, status=202)

    async def post_verification(request):
        require_local_origin_and_token(request)
        try:
            payload = await request.json()
        except ValueError:
            raise web.HTTPBadRequest(text="Invalid verification request")
        if type(payload.get("enabled")) is not bool:
            raise web.HTTPBadRequest(text="enabled must be a boolean")
        try:
            result = (await controller.start_verification() if payload["enabled"]
                      else await controller.stop_verification())
        except CommandBusy:
            raise web.HTTPConflict(text="Camera command already in progress")
        return web.json_response(asdict(result))

    app.router.add_get("/", page)
    app.router.add_get("/{name:app\\.js|styles\\.css}", asset)
    app.router.add_get("/api/status", status)
    app.router.add_post("/api/camera", post_camera)
    app.router.add_post("/api/verification", post_verification)
    return app
