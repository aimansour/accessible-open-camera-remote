"""Serialized camera commands with verification before reporting success."""

import asyncio
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
    def __init__(self, adb, tone: TonePort):
        self.adb = adb
        self.tone = tone
        self._state = CaptureState.UNKNOWN
        self._verification_enabled = True
        self._busy = False
        self._message = "Waiting for a fresh phone state"
        self._task: asyncio.Task | None = None

    def status(self) -> CameraStatus:
        return CameraStatus(self._state, self._verification_enabled, self._busy, self._message)

    async def start_session(self) -> CameraStatus:
        return await self.start_verification()

    async def start_verification(self) -> CameraStatus:
        if self._busy:
            raise CommandBusy("A camera command is still being checked")
        self._verification_enabled = True
        self._state = CaptureState.UNKNOWN
        self._message = "Reading Open Camera state"
        try:
            self._state = classify(parse_dump(await self.adb.dump_ui()))
            self._message = (
                "Open Camera is in photo mode or its recording state could not be recognized"
                if self._state is CaptureState.UNKNOWN else "Camera state verified"
            )
        except (AdbFailure, InvalidDump, asyncio.TimeoutError):
            self._message = "Could not read Open Camera; check the phone and connection"
        return self.status()

    async def stop_verification(self) -> CameraStatus:
        self._verification_enabled = False
        self._state = CaptureState.UNKNOWN
        self._message = "Verification is off; phone camera controls are disabled"
        task = self._task
        if task is not None and not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        self._busy = False
        return self.status()

    def submit(self, action: CameraAction) -> asyncio.Task[CameraStatus]:
        action = CameraAction(action)
        if self._busy:
            raise CommandBusy("A camera command is still being checked")
        if not self._verification_enabled or self._state not in ALLOWED[action]:
            raise CommandUnavailable("Verify the current camera state before this command")
        self._busy = True
        self._message = "Sending command and checking its result"
        self._task = asyncio.create_task(self._perform(action))
        return self._task

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

    async def _perform(self, action: CameraAction) -> CameraStatus:
        try:
            if not await self._preflight():
                self._state = CaptureState.UNKNOWN
                self._message = "Unlock the phone and bring Open Camera to the foreground"
                self.tone.failure()
            else:
                await self.adb.press(KEY_BY_ACTION[action])
                verified = False
                async with asyncio.timeout(8):
                    for _ in range(2):
                        state = classify(parse_dump(await self.adb.dump_ui()))
                        if state is EXPECTED[action]:
                            verified = True
                            break
                        if state is CaptureState.UNKNOWN:
                            break
                if verified:
                    self._state = state
                    self._message = "Camera state verified"
                    self.tone.success()
                else:
                    self._state = CaptureState.UNKNOWN
                    self._message = "Command sent, but the camera state could not be confirmed"
                    self.tone.failure()
        except asyncio.CancelledError:
            self._state = CaptureState.UNKNOWN
            self._message = "Verification stopped"
            raise
        except (AdbFailure, InvalidDump, asyncio.TimeoutError):
            self._state = CaptureState.UNKNOWN
            self._message = "Camera result uncertain; check the phone, then verify again"
            self.tone.failure()
        finally:
            self._busy = False
        return self.status()
