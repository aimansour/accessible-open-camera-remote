"""Start the local browser controller on Windows."""

import argparse
import asyncio
import os
import secrets
import shutil
import subprocess
import webbrowser
from pathlib import Path

from aiohttp import web

from .adb import AdbClient
from .audio import ToneSink
from .camera import CameraController
from .diagnostics import DiagnosticLog
from .server import CAMERA_TASKS_KEY, TRANSFER_TASKS_KEY, create_app


def choose_device(adb_path: Path, requested: str | None) -> str:
    result = subprocess.run([str(adb_path), "devices"], capture_output=True, text=True,
                            timeout=10, check=True)
    connected = [line.split("\t", 1)[0] for line in result.stdout.splitlines()
                 if "\tdevice" in line]
    if requested:
        if requested not in connected:
            raise RuntimeError("The selected phone is not connected through ADB")
        return requested
    if len(connected) != 1:
        raise RuntimeError("Connect one phone or select its exact ADB serial with --serial")
    return connected[0]


async def _stop_tasks(app) -> None:
    tasks = tuple(app[CAMERA_TASKS_KEY] | app[TRANSFER_TASKS_KEY])
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)


async def serve(serial: str, adb_path: Path) -> None:
    probe = AdbClient(serial, adb_path)
    try:
        model = (await probe.run("shell", "getprop", "ro.product.model", timeout=5)).decode(
            "utf-8", errors="replace").strip()
    except Exception:
        model = "unknown"
    data_root = Path(os.getenv("LOCALAPPDATA", str(Path.home() / "AppData" / "Local")))
    diagnostics = DiagnosticLog(data_root / "OpenCameraRemote" / "diagnostics.jsonl", model)
    adb = AdbClient(serial, adb_path, diagnostics=diagnostics)
    diagnostics.record("service_started")
    controller = CameraController(adb, ToneSink(), diagnostics=diagnostics)
    await controller.start_session()
    app = create_app(controller, secrets.token_urlsafe(32), diagnostics=diagnostics)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = site._server.sockets[0].getsockname()[1]
    url = f"http://127.0.0.1:{port}/"
    print(f"Open Camera Remote: {url}", flush=True)
    webbrowser.open(url)
    try:
        await asyncio.Event().wait()
    finally:
        await _stop_tasks(app)
        await runner.cleanup()
        diagnostics.record("service_stopped")


def main() -> None:
    parser = argparse.ArgumentParser(description="Accessible Open Camera Remote")
    parser.add_argument("--serial", help="Exact wireless ADB serial of the phone")
    args = parser.parse_args()
    adb_command = shutil.which("adb")
    if not adb_command:
        parser.error("ADB was not found")
    adb_path = Path(adb_command)
    try:
        serial = choose_device(adb_path, args.serial)
        asyncio.run(serve(serial, adb_path))
    except KeyboardInterrupt:
        pass
    except (RuntimeError, subprocess.SubprocessError) as exc:
        parser.exit(1, f"{exc}\n")


if __name__ == "__main__":
    main()
