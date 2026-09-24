import asyncio

import pytest

from oc_remote.camera import CameraAction, CameraController, CommandBusy, CommandUnavailable
from oc_remote.state import CaptureState


def xml(take, pause=None, package="net.sourceforge.opencamera"):
    pause_node = "" if pause is None else (
        f'<node package="{package}" resource-id="{package}:id/pause_video" content-desc="{pause}"/>'
    )
    return (
        f'<hierarchy><node package="{package}" resource-id="{package}:id/take_photo" '
        f'content-desc="{take}"/>{pause_node}</hierarchy>'
    ).encode()


IDLE = xml("Start recording video")
RECORDING = xml("Stop recording video", "Pause video recording")
PAUSED = xml("Stop recording video", "Resume video recording")


class FakeAdb:
    def __init__(self, initial=IDLE, after=RECORDING):
        self.dumps = [initial, after]
        self.initial = initial
        self.keys = []
        self.first_press = asyncio.Event()
        self.hold = asyncio.Event()
        self.hold.set()
        self.window = b"mCurrentFocus=Window{1 u0 net.sourceforge.opencamera/.MainActivity}\n"
        self.power = b"mWakefulness=Awake\n"
        self.dump_count = 0
        self.finalize_on_stop = True

    async def run(self, *args, **kwargs):
        if "find" in args:
            if self.finalize_on_stop and len(self.keys) >= (1 if self.initial is PAUSED else 2):
                return b"new.mp4\0" + b"20\0" + b"2.0\0"
            return b""
        if args[-2:] == ("dumpsys", "window"):
            return self.window
        if args[-2:] == ("dumpsys", "power"):
            return self.power
        raise AssertionError(args)

    async def dump_ui(self):
        self.dump_count += 1
        await self.hold.wait()
        return self.dumps.pop(0)

    async def press(self, key):
        self.keys.append(key)
        self.first_press.set()


class FakeTone:
    def __init__(self):
        self.events = []

    def success(self):
        self.events.append("success")

    def failure(self):
        self.events.append("failure")


async def test_command_is_sent_before_verification_finishes():
    adb, tone = FakeAdb(), FakeTone()
    controller = CameraController(adb, tone)
    assert (await controller.start_session()).state is CaptureState.IDLE
    adb.hold.clear()
    task = controller.submit(CameraAction.START)
    await asyncio.wait_for(adb.first_press.wait(), 1)
    assert adb.keys == [24]
    assert controller.status().busy
    assert tone.events == []
    adb.hold.set()
    result = await task
    assert result.state is CaptureState.RECORDING
    assert not result.busy
    assert tone.events == ["success"]


async def test_duplicate_start_during_verification_does_not_send_a_second_key():
    adb, tone = FakeAdb(), FakeTone()
    controller = CameraController(adb, tone)
    await controller.start_session()
    adb.hold.clear()
    task = controller.submit(CameraAction.START)
    await asyncio.wait_for(adb.first_press.wait(), 1)
    with pytest.raises(CommandUnavailable):
        controller.submit(CameraAction.START)
    assert adb.keys == [24]
    adb.hold.set()
    await task


async def test_stop_from_paused_uses_volume_up():
    adb, tone = FakeAdb(PAUSED, IDLE), FakeTone()
    controller = CameraController(adb, tone)
    await controller.start_session()
    assert (await controller.submit(CameraAction.STOP)).state is CaptureState.IDLE
    assert adb.keys == [24]


@pytest.mark.parametrize("window,power", [
    (b"mCurrentFocus=Window{1 u0 other.app/.MainActivity}\n", b"mWakefulness=Awake\n"),
    (b"mCurrentFocus=Window{1 u0 net.sourceforge.opencamera/.MainActivity}\n", b"mWakefulness=Dozing\n"),
])
async def test_bad_foreground_or_locked_phone_sends_no_key(window, power):
    adb, tone = FakeAdb(), FakeTone()
    controller = CameraController(adb, tone)
    await controller.start_session()
    adb.window, adb.power = window, power
    status = await controller.submit(CameraAction.START)
    assert status.state is CaptureState.UNKNOWN
    assert adb.keys == []
    assert tone.events == ["failure"]


async def test_verification_can_be_stopped_during_dump():
    adb, tone = FakeAdb(), FakeTone()
    controller = CameraController(adb, tone)
    await controller.start_session()
    adb.hold.clear()
    task = controller.submit(CameraAction.START)
    await asyncio.wait_for(adb.first_press.wait(), 1)
    assert (await controller.stop_verification()).state is CaptureState.UNKNOWN
    assert not controller.status().verification_enabled
    with pytest.raises(CommandUnavailable):
        controller.submit(CameraAction.STOP)
    adb.hold.set()
    await asyncio.gather(task, return_exceptions=True)
    assert tone.events == []


async def test_unrecognized_result_never_retries_the_key():
    adb, tone = FakeAdb(IDLE, xml("Stop recording video", "different")), FakeTone()
    controller = CameraController(adb, tone)
    await controller.start_session()
    result = await controller.submit(CameraAction.START)
    assert result.state is CaptureState.UNKNOWN
    assert not result.busy
    assert adb.keys == [24]
    assert tone.events == ["failure"]


async def test_dump_timeout_after_press_is_uncertain_without_retry():
    adb, tone = FakeAdb(), FakeTone()
    controller = CameraController(adb, tone)
    await controller.start_session()

    async def timeout_dump():
        raise asyncio.TimeoutError

    adb.dump_ui = timeout_dump
    result = await controller.submit(CameraAction.START)
    assert result.state is CaptureState.UNKNOWN
    assert adb.keys == [24]
    assert tone.events == ["failure"]


async def test_stop_key_is_sent_while_start_result_dump_is_still_waiting():
    adb, tone = FakeAdb(), FakeTone()
    adb.dumps.append(IDLE)
    controller = CameraController(adb, tone)
    assert (await controller.start_session()).confirmed_state is CaptureState.IDLE
    adb.hold.clear()
    start = controller.submit(CameraAction.START)
    await asyncio.wait_for(adb.first_press.wait(), 1)
    for _ in range(100):
        if adb.dump_count >= 2:
            break
        await asyncio.sleep(0.001)
    assert adb.dump_count >= 2
    stop = controller.submit(CameraAction.STOP)
    assert controller.status().state is CaptureState.IDLE
    for _ in range(100):
        if len(adb.keys) == 2:
            break
        await asyncio.sleep(0.001)
    assert adb.keys == [24, 24]
    assert tone.events == []
    adb.hold.set()
    await asyncio.gather(start, stop)


async def test_failed_second_key_drops_queued_third_key():
    adb, tone = FakeAdb(), FakeTone()
    controller = CameraController(adb, tone)
    await controller.start_session()

    async def press(key):
        adb.keys.append(key)
        if len(adb.keys) == 2:
            from oc_remote.adb import AdbFailure
            raise AdbFailure("offline")

    adb.press = press
    tasks = [controller.submit(action) for action in (
        CameraAction.START, CameraAction.STOP, CameraAction.START,
    )]
    await asyncio.gather(*tasks, return_exceptions=True)
    assert adb.keys == [24, 24]
    assert controller.status().state is CaptureState.UNKNOWN
    assert tone.events == ["failure"]


async def test_failure_from_stale_dump_does_not_override_newer_stop_result():
    first_result_started = asyncio.Event()
    release_first_result = asyncio.Event()

    class RaceAdb(FakeAdb):
        async def dump_ui(self):
            self.dump_count += 1
            if self.dump_count == 1:
                return IDLE
            if self.dump_count == 2:
                first_result_started.set()
                await release_first_result.wait()
                from oc_remote.adb import AdbFailure
                raise AdbFailure("old dump failed")
            return IDLE

    adb, tone = RaceAdb(), FakeTone()
    controller = CameraController(adb, tone)
    await controller.start_session()
    start = controller.submit(CameraAction.START)
    await asyncio.wait_for(first_result_started.wait(), 1)
    stop = controller.submit(CameraAction.STOP)
    for _ in range(100):
        if len(adb.keys) == 2:
            break
        await asyncio.sleep(0.001)
    assert adb.keys == [24, 24]
    release_first_result.set()
    await asyncio.gather(start, stop)
    assert controller.status().confirmed_state is CaptureState.IDLE
    assert tone.events == ["success"]


async def test_repeated_wrong_state_has_a_bounded_uncertain_result():
    class WrongStateAdb(FakeAdb):
        async def dump_ui(self):
            self.dump_count += 1
            await asyncio.sleep(0.01)
            return IDLE

    adb, tone = WrongStateAdb(), FakeTone()
    controller = CameraController(adb, tone)
    await controller.start_session()
    result = await asyncio.wait_for(controller.submit(CameraAction.START), 0.3)
    assert result.state is CaptureState.UNKNOWN
    assert adb.keys == [24]
    assert tone.events == ["failure"]


async def test_rapid_stop_with_idle_dump_but_no_finalized_video_is_uncertain():
    adb, tone = FakeAdb(), FakeTone()
    adb.dumps = [IDLE, IDLE]
    adb.finalize_on_stop = False
    controller = CameraController(adb, tone)
    await controller.start_session()
    start = controller.submit(CameraAction.START)
    stop = controller.submit(CameraAction.STOP)
    await asyncio.wait_for(asyncio.gather(start, stop), 9)
    assert adb.keys == [24, 24]
    assert controller.status().state is CaptureState.UNKNOWN
    assert tone.events == ["failure"]


async def test_old_stop_snapshot_cannot_settle_new_start(monkeypatch):
    snapshot_started = asyncio.Event()
    release_snapshot = asyncio.Event()
    adb, tone = FakeAdb(), FakeTone()
    adb.dumps = [IDLE, IDLE, RECORDING]
    controller = CameraController(adb, tone)
    await controller.start_session()

    async def finalized(*args, **kwargs):
        return True

    async def held_snapshot(*args, **kwargs):
        snapshot_started.set()
        await release_snapshot.wait()
        return {}

    monkeypatch.setattr("oc_remote.camera.finalized_since", finalized)
    monkeypatch.setattr("oc_remote.camera.snapshot", held_snapshot)
    start = controller.submit(CameraAction.START)
    stop = controller.submit(CameraAction.STOP)
    await asyncio.wait_for(snapshot_started.wait(), 2)
    newer_start = controller.submit(CameraAction.START)
    adb.hold.clear()
    release_snapshot.set()
    await asyncio.sleep(0.05)
    assert controller.status().state is CaptureState.RECORDING
    assert controller.status().busy is True
    assert tone.events == []
    adb.hold.set()
    await asyncio.wait_for(asyncio.gather(start, stop, newer_start), 2)
