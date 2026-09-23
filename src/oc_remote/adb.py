"""ADB commands bound to one selected device."""

import asyncio
import subprocess
import time
from pathlib import Path
from uuid import uuid4


class AdbFailure(RuntimeError):
    """ADB reported an unsuccessful command."""


class AdbTimeout(AdbFailure):
    """ADB did not finish within its command deadline."""


class AdbClient:
    def __init__(self, serial: str, executable: Path, runner=None, diagnostics=None):
        if not serial or serial.startswith("-"):
            raise ValueError("A selected device serial is required")
        self.serial = serial
        self.executable = Path(executable)
        self._runner = runner
        self._diagnostics = diagnostics

    def _record(self, event: str, started: float, status: int | None) -> None:
        if self._diagnostics is not None:
            try:
                self._diagnostics.record(event, elapsed_ms=int((time.monotonic() - started) * 1000),
                                         adb_status=status)
            except OSError:
                pass

    async def run(self, *args: str, timeout: float = 15) -> bytes:
        command = (str(self.executable), "-s", self.serial, *args)
        started = time.monotonic()
        try:
            if self._runner is not None:
                result = await asyncio.to_thread(
                    self._runner, command, capture_output=True, timeout=timeout, check=False
                )
                stdout, status = result.stdout, result.returncode
            else:
                process = await asyncio.create_subprocess_exec(
                    *command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                )
                try:
                    stdout, _stderr = await asyncio.wait_for(process.communicate(), timeout)
                except (asyncio.TimeoutError, asyncio.CancelledError):
                    process.kill()
                    await process.communicate()
                    raise
                status = process.returncode
        except (subprocess.TimeoutExpired, asyncio.TimeoutError) as exc:
            self._record("adb_timeout", started, None)
            raise AdbTimeout("ADB command timed out") from exc
        except OSError as exc:
            self._record("adb_start_failure", started, None)
            raise AdbFailure("ADB could not start") from exc
        if status != 0:
            self._record("adb_failure", started, status)
            raise AdbFailure(f"ADB command failed ({status})")
        self._record("adb_ok", started, 0)
        return stdout

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
