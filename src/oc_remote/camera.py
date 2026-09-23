"""Serialized camera commands with verification before reporting success."""

import asyncio
from collections import deque
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from .adb import AdbFailure
from .state import CaptureState, InvalidDump, classify, parse_dump


class CameraAction(StrEnum):
    START = "start"
    STOP = "stop"
    PAUSE = "pause"
    RESUME = "resume"


class CommandBusy(RuntimeError):
    pass


class CommandUnavailable(RuntimeError):
    pass


class TonePort(Protocol):
    def success(self) -> None: ...
    def failure(self) -> None: ...


@dataclass(frozen=True)
class CameraStatus:
    state: CaptureState
    verification_enabled: bool
    busy: bool
    message: str
    confirmed_state: CaptureState = CaptureState.UNKNOWN
    generation: int = 0


KEY_BY_ACTION = {
    CameraAction.START: 24,
    CameraAction.STOP: 24,
    CameraAction.PAUSE: 25,
    CameraAction.RESUME: 25,
}
EXPECTED = {
    CameraAction.START: CaptureState.RECORDING,
    CameraAction.STOP: CaptureState.IDLE,
    CameraAction.PAUSE: CaptureState.PAUSED,
    CameraAction.RESUME: CaptureState.RECORDING,
}
ALLOWED = {
    CameraAction.START: {CaptureState.IDLE},
    CameraAction.STOP: {CaptureState.RECORDING, CaptureState.PAUSED},
    CameraAction.PAUSE: {CaptureState.RECORDING},
    CameraAction.RESUME: {CaptureState.PAUSED},
}


class CameraController:
    def __init__(self, adb, tone: TonePort, diagnostics=None):
        self.adb = adb
        self.tone = tone
        self._diagnostics = diagnostics
        self._state = CaptureState.UNKNOWN
        self._confirmed_state = CaptureState.UNKNOWN
        self._verification_enabled = True
        self._busy = False
        self._message = "Waiting for a fresh phone state"
        self._generation = 0
        self._unresolved = 0
        self._pending: deque[tuple[int, CameraAction]] = deque()
        self._sender_task: asyncio.Task | None = None
        self._verifier_task: asyncio.Task | None = None
        self._settled = asyncio.Event()
        self._settled.set()

    def _record(self, event: str) -> None:
        if self._diagnostics is not None:
            self._diagnostics.record(event)

    def status(self) -> CameraStatus:
        return CameraStatus(self._state, self._verification_enabled, self._busy,
                            self._message, self._confirmed_state, self._generation)

    async def start_session(self) -> CameraStatus:
        return await self.start_verification()

    async def start_verification(self) -> CameraStatus:
        if self._busy:
            raise CommandBusy("A camera command is still being checked")
        self._verification_enabled = True
        self._state = CaptureState.UNKNOWN
        self._confirmed_state = CaptureState.UNKNOWN
        self._message = "Reading Open Camera state"
        try:
            self._state = classify(parse_dump(await self.adb.dump_ui()))
            self._confirmed_state = self._state
            self._message = (
                "Open Camera is in photo mode or its recording state could not be recognized"
                if self._state is CaptureState.UNKNOWN else "Camera state verified"
            )
        except (AdbFailure, InvalidDump, asyncio.TimeoutError):
            self._message = "Could not read Open Camera; check the phone and connection"
        self._record("camera_verified" if self._state is not CaptureState.UNKNOWN else "camera_uncertain")
        return self.status()

    async def stop_verification(self) -> CameraStatus:
        self._verification_enabled = False
        self._state = CaptureState.UNKNOWN
        self._confirmed_state = CaptureState.UNKNOWN
        self._message = "Verification is off; phone camera controls are disabled"
        self._pending.clear()
        tasks = (self._sender_task, self._verifier_task)
        for task in tasks:
            if task is not None and not task.done():
                task.cancel()
        await asyncio.gather(*(task for task in tasks if task is not None), return_exceptions=True)
        self._busy = False
        self._unresolved = 0
        self._settled.set()
        return self.status()

    def submit(self, action: CameraAction) -> asyncio.Task[CameraStatus]:
        action = CameraAction(action)
        if not self._verification_enabled or self._state not in ALLOWED[action]:
            raise CommandUnavailable("Verify the current camera state before this command")
        if self._unresolved >= 8:
            raise CommandBusy("Too many camera commands are waiting")
        if not self._busy:
            self._settled = asyncio.Event()
        self._generation += 1
        self._unresolved += 1
        self._state = EXPECTED[action]
        self._busy = True
        self._message = "Sending command and checking its result"
        self._pending.append((self._generation, action))
        self._ensure_sender()
        return asyncio.create_task(self._await_settled(self._settled))

    async def _await_settled(self, event: asyncio.Event) -> CameraStatus:
        await event.wait()
        return self.status()

    def _ensure_sender(self) -> None:
        if self._sender_task is None or self._sender_task.done():
            self._sender_task = asyncio.create_task(self._send_loop())

    def _fail(self, message: str) -> None:
        if not self._busy:
            return
        self._pending.clear()
        self._state = CaptureState.UNKNOWN
        self._confirmed_state = CaptureState.UNKNOWN
        self._message = message
        self._busy = False
        self._unresolved = 0
        self.tone.failure()
        self._record("camera_uncertain")
        self._settled.set()

    async def _preflight(self) -> bool:
        window = (await self.adb.run("shell", "dumpsys", "window", timeout=3)).decode(
            "utf-8", errors="replace"
        )
        power = (await self.adb.run("shell", "dumpsys", "power", timeout=3)).decode(
            "utf-8", errors="replace"
        )
        focus = next((line for line in window.splitlines() if "mCurrentFocus=" in line), "")
        return (
            "net.sourceforge.opencamera/" in focus
            and "mWakefulness=Awake" in power
            and "mDreamingLockscreen=true" not in window
            and "mShowingLockscreen=true" not in window
        )

    async def _send_loop(self) -> None:
        try:
            while self._pending and self._verification_enabled:
                _, action = self._pending.popleft()
                if not await self._preflight():
                    self._fail("Unlock the phone and bring Open Camera to the foreground")
                    return
                await self.adb.press(KEY_BY_ACTION[action])
                if self._verifier_task is None or self._verifier_task.done():
                    self._verifier_task = asyncio.create_task(self._verify_loop())
        except asyncio.CancelledError:
            raise
        except (AdbFailure, InvalidDump, asyncio.TimeoutError):
            self._fail("Camera result uncertain; check the phone, then verify again")
        finally:
            self._sender_task = None
            if self._pending and self._busy and self._verification_enabled:
                self._ensure_sender()

    async def _verify_loop(self) -> None:
        try:
            async with asyncio.timeout(8):
                while self._busy and self._verification_enabled:
                    captured_generation = self._generation
                    observed = classify(parse_dump(await self.adb.dump_ui()))
                    if captured_generation != self._generation or self._sender_task is not None:
                        await asyncio.sleep(0.02)
                        continue
                    if observed is self._state:
                        self._confirmed_state = observed
                        self._message = "Camera state verified"
                        self._busy = False
                        self._unresolved = 0
                        self.tone.success()
                        self._record("camera_verified")
                        self._settled.set()
                        return
                    if observed is CaptureState.UNKNOWN:
                        break
            self._fail("Command sent, but the camera state could not be confirmed")
        except asyncio.CancelledError:
            raise
        except (AdbFailure, InvalidDump, asyncio.TimeoutError):
            self._fail("Camera result uncertain; check the phone, then verify again")
