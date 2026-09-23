"""ADB commands bound to one selected device."""

import asyncio
import subprocess
from pathlib import Path
from uuid import uuid4


class AdbFailure(RuntimeError):
    """ADB reported an unsuccessful command."""


class AdbTimeout(AdbFailure):
    """ADB did not finish within its command deadline."""


class AdbClient:
    def __init__(self, serial: str, executable: Path, runner=None):
        if not serial or serial.startswith("-"):
            raise ValueError("A selected device serial is required")
        self.serial = serial
        self.executable = Path(executable)
        self._runner = runner or subprocess.run

    async def run(self, *args: str, timeout: float = 15) -> bytes:
        command = (str(self.executable), "-s", self.serial, *args)
        try:
            result = await asyncio.to_thread(
                self._runner, command, capture_output=True, timeout=timeout, check=False
            )
        except subprocess.TimeoutExpired as exc:
            raise AdbTimeout("ADB command timed out") from exc
        except OSError as exc:
            raise AdbFailure("ADB could not start") from exc
        if result.returncode != 0:
            raise AdbFailure(f"ADB command failed ({result.returncode})")
        return result.stdout

    async def press(self, keycode: int) -> None:
        if keycode not in (24, 25):
            raise ValueError("Unsupported camera key")
        await self.run("shell", "input", "keyevent", str(keycode), timeout=3)

    async def dump_ui(self) -> bytes:
        remote_path = f"/data/local/tmp/oc-remote-{uuid4().hex}.xml"
        try:
            await self.run("shell", "uiautomator", "dump", remote_path, timeout=8)
            return await self.run("exec-out", "cat", remote_path, timeout=3)
        finally:
            try:
                await self.run("shell", "rm", "-f", remote_path, timeout=3)
            except AdbFailure:
                pass

    async def pull(self, remote: str, local: Path) -> None:
        await self.run("pull", remote, str(local), timeout=300)
