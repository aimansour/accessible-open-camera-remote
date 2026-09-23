"""Loopback HTTP API for the browser controls."""

import asyncio
from dataclasses import asdict
from html import escape
from pathlib import Path
from uuid import uuid4

from aiohttp import web

from .camera import CameraAction, CommandBusy, CommandUnavailable
from .catalog import DEFAULT_PHONE_FOLDER, InvalidListing, list_videos, validate_folder, validate_name
from .adb import AdbFailure
from .files import MediaIndexError, UncertainMutation, delete_one, move_one, rename_one
from .state import CaptureState
from .transfer import copy_many


CONTROLLER_KEY = web.AppKey("controller", object)
SESSION_TOKEN_KEY = web.AppKey("session_token", str)
CAMERA_TASKS_KEY = web.AppKey("camera_tasks", set)
TRANSFER_TASKS_KEY = web.AppKey("transfer_tasks", set)
TRANSFER_JOB_KEY = web.AppKey("transfer_job", dict)
VERIFIED_CATALOG_KEY = web.AppKey("verified_catalog", dict)
FILE_LOCK_KEY = web.AppKey("file_lock", asyncio.Lock)
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


def create_app(controller, token: str, diagnostics=None) -> web.Application:
    if not token:
        raise ValueError("A session token is required")
    app = web.Application()
    app[CONTROLLER_KEY] = controller
    app[SESSION_TOKEN_KEY] = token
    app[CAMERA_TASKS_KEY] = set()
    app[TRANSFER_TASKS_KEY] = set()
    app[TRANSFER_JOB_KEY] = {"total": 0, "stages": {}, "results": [], "running": False, "completed": 0}
    app[VERIFIED_CATALOG_KEY] = {}
    app[FILE_LOCK_KEY] = asyncio.Lock()

    def record(event: str) -> None:
        if diagnostics is not None:
            diagnostics.record(event)

    def require_idle_for_mutation():
        camera = controller.status()
        if (camera.confirmed_state is not CaptureState.IDLE or not camera.verification_enabled
                or camera.busy):
            raise web.HTTPConflict(text="Verify that recording has stopped before changing phone files")

    async def selected_entry(folder, name):
        try:
            name = validate_name(name)
            entries = await list_videos(controller.adb, folder)
        except (ValueError, InvalidListing):
            raise web.HTTPBadRequest(text="Invalid selected video")
        except AdbFailure:
            raise web.HTTPBadGateway(text="Could not read phone videos")
        entry = next((item for item in entries if item.name == name), None)
        if entry is None:
            raise web.HTTPNotFound(text="Selected video no longer exists")
        return entry

    async def page(request):
        require_local_host(request)
        html = (WEB_DIR / "index.html").read_text(encoding="utf-8")
        html = html.replace("__SESSION_TOKEN__", escape(token, quote=True))
        html = html.replace("__PC_FOLDER__", escape(str(Path.home() / "Videos" / "OpenCameraRemote"), quote=True))
        return web.Response(text=html, content_type="text/html", charset="utf-8",
                            headers={"Cache-Control": "no-store"})

    async def asset(request):
        require_local_host(request)
        name = request.match_info["name"]
        return web.FileResponse(WEB_DIR / name, headers={"Cache-Control": "no-store"})

    async def status(request):
        require_local_host(request)
        return web.json_response(asdict(controller.status()))

    async def videos(request):
        require_local_host(request)
        try:
            folder = validate_folder(request.query.get("folder", DEFAULT_PHONE_FOLDER))
        except ValueError:
            raise web.HTTPBadRequest(text="Choose a shared-storage phone folder")
        try:
            entries = await list_videos(controller.adb, folder)
        except (InvalidListing, AdbFailure):
            raise web.HTTPBadGateway(text="Could not read the phone video folder")
        camera = controller.status()
        if (camera.confirmed_state is CaptureState.IDLE and camera.verification_enabled
                and not camera.busy):
            app[VERIFIED_CATALOG_KEY][folder] = {entry.name: entry for entry in entries}
        return web.json_response({"folder": folder, "videos": [asdict(entry) for entry in entries]})

    async def transfers(request):
        require_local_host(request)
        return web.json_response(app[TRANSFER_JOB_KEY])

    async def post_copy(request):
        require_local_origin_and_token(request)
        if app[TRANSFER_JOB_KEY]["running"] or app[FILE_LOCK_KEY].locked():
            raise web.HTTPConflict(text="A transfer is already running")
        await app[FILE_LOCK_KEY].acquire()
        try:
            try:
                payload = await request.json()
                names = payload["names"]
                folder = validate_folder(payload.get("folder", DEFAULT_PHONE_FOLDER))
                destination = Path(payload["destination"]).expanduser()
                if (not isinstance(names, list) or not names or len(names) > 100
                        or any(not isinstance(name, str) for name in names)
                        or len(set(names)) != len(names) or not destination.is_absolute()):
                    raise ValueError
            except (ValueError, KeyError, TypeError):
                raise web.HTTPBadRequest(text="Choose videos and an absolute PC folder")
            camera = controller.status()
            if (camera.confirmed_state is CaptureState.IDLE and camera.verification_enabled
                    and not camera.busy):
                try:
                    latest = await list_videos(controller.adb, folder)
                except (InvalidListing, AdbFailure):
                    raise web.HTTPBadGateway(text="Could not read selected phone videos")
                available = {entry.name: entry for entry in latest}
                app[VERIFIED_CATALOG_KEY][folder] = available
            elif not camera.verification_enabled:
                available = app[VERIFIED_CATALOG_KEY].get(folder, {})
            else:
                raise web.HTTPConflict(text="Finish recording or verify camera state before copying")
            if any(name not in available for name in names):
                raise web.HTTPBadRequest(text="A selected video is no longer available as completed")
            entries = [available[name] for name in names]
        except BaseException:
            app[FILE_LOCK_KEY].release()
            raise
        job = app[TRANSFER_JOB_KEY]
        job.clear()
        job.update({"id": uuid4().hex, "total": len(entries), "stages": {name: "waiting" for name in names},
                    "results": [], "running": True, "completed": 0})

        def progress(name, stage):
            job["stages"][name] = stage

        async def perform_copy():
            try:
                results = await copy_many(controller.adb, entries, folder, destination, progress=progress)
                job["results"] = [asdict(result) for result in results]
                job["completed"] = len(results)
                if all(result.outcome == "verified" for result in results):
                    controller.tone.success()
                    record("copy_verified")
                else:
                    controller.tone.failure()
                    record("copy_failed")
            except Exception:
                job["results"] = [{"name": name, "outcome": "failed", "destination": None,
                                   "message": "Unexpected transfer error"} for name in names]
                job["completed"] = len(names)
                job["stages"] = {name: "failed" for name in names}
                controller.tone.failure()
                record("copy_failed")
            finally:
                job["running"] = False
                app[FILE_LOCK_KEY].release()

        task = asyncio.create_task(perform_copy())
        app[TRANSFER_TASKS_KEY].add(task)
        task.add_done_callback(app[TRANSFER_TASKS_KEY].discard)
        return web.json_response({"accepted": True, "id": job["id"]}, status=202)

    async def post_rename(request):
        require_local_origin_and_token(request)
        if app[TRANSFER_JOB_KEY]["running"]:
            raise web.HTTPConflict(text="A transfer is running")
        async with app[FILE_LOCK_KEY]:
            require_idle_for_mutation()
            try:
                payload = await request.json()
                folder = validate_folder(payload.get("folder", DEFAULT_PHONE_FOLDER))
                name = payload["name"]
                new_stem = payload["new_stem"]
                if not isinstance(name, str) or not isinstance(new_stem, str):
                    raise ValueError
            except (ValueError, KeyError, TypeError):
                raise web.HTTPBadRequest(text="Choose one video and a new name")
            entry = await selected_entry(folder, name)
            try:
                result = await rename_one(controller.adb, entry, folder, new_stem)
            except FileExistsError:
                controller.tone.failure()
                raise web.HTTPConflict(text="A video with the new name already exists")
            except ValueError:
                raise web.HTTPBadRequest(text="Invalid new video name")
            except (UncertainMutation, MediaIndexError, AdbFailure):
                controller.tone.failure()
                record("rename_uncertain")
                raise web.HTTPConflict(text="Rename result uncertain; inspect the phone")
            app[VERIFIED_CATALOG_KEY].pop(folder, None)
            controller.tone.success()
            record("rename_verified")
            return web.json_response(asdict(result))

    async def post_delete(request):
        require_local_origin_and_token(request)
        if app[TRANSFER_JOB_KEY]["running"]:
            raise web.HTTPConflict(text="A transfer is running")
        async with app[FILE_LOCK_KEY]:
            require_idle_for_mutation()
            try:
                payload = await request.json()
                folder = validate_folder(payload.get("folder", DEFAULT_PHONE_FOLDER))
                name = payload["name"]
                confirmed_name = payload["confirmed_name"]
                if not isinstance(name, str) or confirmed_name != name:
                    raise ValueError
            except (ValueError, KeyError, TypeError):
                raise web.HTTPBadRequest(text="Confirm the exact selected video name")
            entry = await selected_entry(folder, name)
            try:
                await delete_one(controller.adb, entry, folder, confirmed_name)
            except (UncertainMutation, MediaIndexError, AdbFailure):
                controller.tone.failure()
                record("delete_uncertain")
                raise web.HTTPConflict(text="Deletion result uncertain; inspect the phone")
            app[VERIFIED_CATALOG_KEY].pop(folder, None)
            controller.tone.success()
            record("delete_verified")
            return web.json_response({"deleted": name})

    async def post_move(request):
        require_local_origin_and_token(request)
        if app[TRANSFER_JOB_KEY]["running"] or app[FILE_LOCK_KEY].locked():
            raise web.HTTPConflict(text="A file operation is already running")
        await app[FILE_LOCK_KEY].acquire()
        try:
            require_idle_for_mutation()
            try:
                payload = await request.json()
                folder = validate_folder(payload.get("folder", DEFAULT_PHONE_FOLDER))
                name = payload["name"]
                destination = Path(payload["destination"]).expanduser()
                if not isinstance(name, str) or not destination.is_absolute():
                    raise ValueError
            except (ValueError, KeyError, TypeError):
                raise web.HTTPBadRequest(text="Choose one video and an absolute PC folder")
            entry = await selected_entry(folder, name)
        except Exception:
            app[FILE_LOCK_KEY].release()
            raise
        job = app[TRANSFER_JOB_KEY]
        job.clear()
        job.update({"id": uuid4().hex, "total": 1, "stages": {name: "copying"},
                    "results": [], "running": True, "completed": 0})

        async def perform_move():
            try:
                result = await move_one(controller.adb, entry, folder, destination)
                job["results"] = [asdict(result)]
                job["stages"][name] = result.outcome
                job["completed"] = 1
                if result.outcome == "verified":
                    app[VERIFIED_CATALOG_KEY].pop(folder, None)
                    controller.tone.success()
                    record("move_verified")
                else:
                    controller.tone.failure()
                    record("move_uncertain")
            except Exception:
                job["stages"][name] = "uncertain"
                job["results"] = [{"name": name, "outcome": "uncertain", "destination": None,
                                   "message": "Move result uncertain; inspect phone and PC"}]
                job["completed"] = 1
                controller.tone.failure()
                record("move_uncertain")
            finally:
                job["running"] = False
                app[FILE_LOCK_KEY].release()

        task = asyncio.create_task(perform_move())
        app[TRANSFER_TASKS_KEY].add(task)
        task.add_done_callback(app[TRANSFER_TASKS_KEY].discard)
        return web.json_response({"accepted": True, "id": job["id"]}, status=202)

    async def post_camera(request):
        require_local_origin_and_token(request)
        if app[FILE_LOCK_KEY].locked():
            raise web.HTTPConflict(text="A phone file operation is in progress")
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
        return web.json_response({"accepted": True, **asdict(controller.status())}, status=202)

    async def post_verification(request):
        require_local_origin_and_token(request)
        if app[FILE_LOCK_KEY].locked():
            raise web.HTTPConflict(text="A phone file operation is in progress")
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
    app.router.add_get("/api/videos", videos)
    app.router.add_get("/api/transfers", transfers)
    app.router.add_post("/api/copy", post_copy)
    app.router.add_post("/api/move", post_move)
    app.router.add_post("/api/rename", post_rename)
    app.router.add_post("/api/delete", post_delete)
    app.router.add_post("/api/camera", post_camera)
    app.router.add_post("/api/verification", post_verification)
    return app
