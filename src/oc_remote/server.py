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
FILE_JOB_KEY = web.AppKey("file_job", dict)
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
    app[TRANSFER_JOB_KEY] = {"kind": None, "total": 0, "stages": {}, "results": [],
                             "running": False, "completed": 0}
    app[FILE_JOB_KEY] = {"id": None, "kind": None, "stage": None, "running": False,
                         "outcome": None, "message": ""}
    app[VERIFIED_CATALOG_KEY] = {}
    app[FILE_LOCK_KEY] = asyncio.Lock()

    def record(event: str) -> None:
        if diagnostics is not None:
            diagnostics.record(event)

    def note_selected_files(folder, entries):
        observer = getattr(controller, "note_selected_files", None)
        if observer is not None:
            observer(folder, entries)

    def note_file_change(folder, old_name, new_entry=None, uncertain=False):
        observer = getattr(controller, "note_file_change", None)
        if observer is not None:
            observer(folder, old_name, new_entry, uncertain=uncertain)

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

    async def selected_entries(folder, names):
        try:
            if (not isinstance(names, list) or not 1 <= len(names) <= 1000
                    or any(not isinstance(name, str) for name in names)
                    or len(set(names)) != len(names)):
                raise ValueError
            names = [validate_name(name) for name in names]
            available = {entry.name: entry for entry in await list_videos(controller.adb, folder)}
        except (ValueError, InvalidListing):
            raise web.HTTPBadRequest(text="Choose distinct video names from the phone folder")
        except AdbFailure:
            raise web.HTTPBadGateway(text="Could not read phone videos")
        if any(name not in available for name in names):
            raise web.HTTPNotFound(text="A selected video no longer exists")
        return [available[name] for name in names]

    def require_expected_entries(entries, expected):
        if expected is None:
            return
        actual = [{"name": entry.name, "size": entry.size, "modified": entry.modified}
                  for entry in entries]
        if expected != actual:
            raise web.HTTPConflict(text="Selected phone files changed; refresh the list")

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
        verified = app[VERIFIED_CATALOG_KEY].get(folder, {})
        copyable = [entry.name for entry in entries if verified.get(entry.name) == entry]
        return web.json_response({"folder": folder, "videos": [asdict(entry) for entry in entries],
                                  "copyable_names": copyable})

    async def transfers(request):
        require_local_host(request)
        return web.json_response(app[TRANSFER_JOB_KEY])

    async def file_operation(request):
        require_local_host(request)
        return web.json_response(app[FILE_JOB_KEY])

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
                if (not isinstance(names, list) or not names or len(names) > 1000
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
            require_expected_entries(entries, payload.get("expected_entries"))
            note_selected_files(folder, entries)
            if camera.verification_enabled:
                require_idle_for_mutation()
        except BaseException:
            app[FILE_LOCK_KEY].release()
            raise
        job = app[TRANSFER_JOB_KEY]
        job.clear()
        job.update({"id": uuid4().hex, "kind": "copy", "folder": folder, "total": len(entries),
                    "stages": {name: "waiting" for name in names},
                    "results": [], "running": True, "completed": 0})

        def progress(name, stage):
            job["stages"][name] = stage

        def on_result(result):
            job["results"].append(asdict(result))
            job["stages"][result.name] = result.outcome
            job["completed"] += 1

        async def perform_copy():
            try:
                results = await copy_many(controller.adb, entries, folder, destination,
                                          progress=progress, on_result=on_result)
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
            require_expected_entries([entry], payload.get("expected_entries"))
            note_selected_files(folder, [entry])
            require_idle_for_mutation()
            try:
                result = await rename_one(controller.adb, entry, folder, new_stem)
            except FileExistsError:
                controller.tone.failure()
                raise web.HTTPConflict(text="A video with the new name already exists")
            except ValueError:
                raise web.HTTPBadRequest(text="Invalid new video name")
            except (UncertainMutation, MediaIndexError, AdbFailure):
                note_file_change(folder, name, uncertain=True)
                controller.tone.failure()
                record("rename_uncertain")
                raise web.HTTPConflict(text="Rename result uncertain; inspect the phone")
            app[VERIFIED_CATALOG_KEY].pop(folder, None)
            note_file_change(folder, name, result)
            controller.tone.success()
            record("rename_verified")
            return web.json_response(asdict(result))

    async def post_delete(request):
        require_local_origin_and_token(request)
        if app[TRANSFER_JOB_KEY]["running"] or app[FILE_LOCK_KEY].locked():
            raise web.HTTPConflict(text="A file operation is already running")
        await app[FILE_LOCK_KEY].acquire()
        try:
            require_idle_for_mutation()
            try:
                payload = await request.json()
                folder = validate_folder(payload.get("folder", DEFAULT_PHONE_FOLDER))
                names = payload.get("names", [payload.get("name")])
                confirmed_names = payload.get("confirmed_names", [payload.get("confirmed_name")])
                if confirmed_names != names:
                    raise ValueError
            except (ValueError, KeyError, TypeError):
                raise web.HTTPBadRequest(text="Confirm the exact selected video names")
            entries = await selected_entries(folder, names)
            require_expected_entries(entries, payload.get("expected_entries"))
            note_selected_files(folder, entries)
            require_idle_for_mutation()
        except BaseException:
            app[FILE_LOCK_KEY].release()
            raise

        job = app[FILE_JOB_KEY]
        job.update({"id": uuid4().hex, "kind": "delete", "folder": folder,
                    "stage": "checking", "running": True,
                    "outcome": None, "message": "Checking selected videos", "total": len(entries),
                    "completed": 0, "stages": {entry.name: "waiting" for entry in entries},
                    "results": []})

        def progress(name: str, stage: str) -> None:
            job["stage"] = stage
            job["stages"][name] = stage
            job["message"] = {
                "checking": "Checking the selected video",
                "deleting": "Deleting from the phone",
                "verifying": "Checking phone file and Android media index",
                "verified": "Deletion verified",
                "uncertain": "Deletion result uncertain; inspect the phone",
            }[stage]

        async def perform_delete():
            try:
                remaining = iter(entries)

                async def delete_worker():
                    for entry in remaining:
                        name = entry.name
                        try:
                            await delete_one(controller.adb, entry, folder, name,
                                             progress=lambda stage, name=name: progress(name, stage))
                            note_file_change(folder, name)
                            job["results"].append({"name": name, "outcome": "verified"})
                        except Exception:
                            note_file_change(folder, name, uncertain=True)
                            progress(name, "uncertain")
                            job["results"].append({"name": name, "outcome": "uncertain"})
                        job["completed"] += 1

                await asyncio.gather(*(delete_worker() for _ in range(min(2, len(entries)))))
                verified = all(result["outcome"] == "verified" for result in job["results"])
                job["outcome"] = "verified" if verified else "uncertain"
                job["stage"] = job["outcome"]
                app[VERIFIED_CATALOG_KEY].pop(folder, None)
                if verified:
                    controller.tone.success()
                    record("delete_verified")
                else:
                    controller.tone.failure()
                    record("delete_uncertain")
            finally:
                job["running"] = False
                app[FILE_LOCK_KEY].release()

        task = asyncio.create_task(perform_delete())
        app[TRANSFER_TASKS_KEY].add(task)
        task.add_done_callback(app[TRANSFER_TASKS_KEY].discard)
        return web.json_response({"accepted": True, "id": job["id"]}, status=202)

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
                names = payload.get("names", [payload.get("name")])
                destination = Path(payload["destination"]).expanduser()
                if not destination.is_absolute():
                    raise ValueError
            except (ValueError, KeyError, TypeError):
                raise web.HTTPBadRequest(text="Choose videos and an absolute PC folder")
            entries = await selected_entries(folder, names)
            require_expected_entries(entries, payload.get("expected_entries"))
            note_selected_files(folder, entries)
            require_idle_for_mutation()
        except Exception:
            app[FILE_LOCK_KEY].release()
            raise
        job = app[TRANSFER_JOB_KEY]
        job.clear()
        job.update({"id": uuid4().hex, "kind": "move", "folder": folder,
                    "total": len(entries),
                    "stages": {entry.name: "waiting" for entry in entries},
                    "results": [], "running": True, "completed": 0})

        async def perform_move():
            try:
                remaining = iter(entries)

                async def move_worker():
                    for entry in remaining:
                        name = entry.name
                        job["stages"][name] = "copying"
                        try:
                            result = await move_one(controller.adb, entry, folder, destination)
                            if result.outcome == "verified":
                                note_file_change(folder, name)
                            elif result.outcome == "uncertain":
                                note_file_change(folder, name, uncertain=True)
                            job["results"].append(asdict(result))
                            job["stages"][name] = result.outcome
                        except Exception:
                            note_file_change(folder, name, uncertain=True)
                            job["stages"][name] = "uncertain"
                            job["results"].append({"name": name, "outcome": "uncertain", "destination": None,
                                                   "message": "Move result uncertain; inspect phone and PC"})
                        job["completed"] += 1

                await asyncio.gather(*(move_worker() for _ in range(min(4, len(entries)))))
                verified = all(result["outcome"] == "verified" for result in job["results"])
                if any(result["outcome"] == "verified" for result in job["results"]):
                    app[VERIFIED_CATALOG_KEY].pop(folder, None)
                if verified:
                    controller.tone.success()
                    record("move_verified")
                else:
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
    app.router.add_get("/api/file-operation", file_operation)
    app.router.add_post("/api/copy", post_copy)
    app.router.add_post("/api/move", post_move)
    app.router.add_post("/api/rename", post_rename)
    app.router.add_post("/api/delete", post_delete)
    app.router.add_post("/api/camera", post_camera)
    app.router.add_post("/api/verification", post_verification)
    return app
