"""Start the local browser controller on Windows."""

import argparse
import asyncio
import secrets
import shutil
import subprocess
import webbrowser
from pathlib import Path

from aiohttp import web

from .adb import AdbClient
from .audio import ToneSink
from .camera import CameraController
from .server import CAMERA_TASKS_KEY, create_app


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


async def serve(serial: str, adb_path: Path) -> None:
    controller = CameraController(AdbClient(serial, adb_path), ToneSink())
    await controller.start_session()
    app = create_app(controller, secrets.token_urlsafe(32))
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
        for task in tuple(app[CAMERA_TASKS_KEY]):
            task.cancel()
        await asyncio.gather(*app[CAMERA_TASKS_KEY], return_exceptions=True)
        await runner.cleanup()


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
