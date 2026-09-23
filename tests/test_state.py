import pytest

from oc_remote.state import CaptureState, InvalidDump, UiSnapshot, classify, parse_dump


def dump(take: str, pause: str | None = None, package: str = "net.sourceforge.opencamera") -> bytes:
    pause_node = "" if pause is None else (
        f'<node package="{package}" resource-id="{package}:id/pause_video" '
        f'content-desc="{pause}" />'
    )
    return (
        f'<hierarchy><node package="{package}" resource-id="{package}:id/take_photo" '
        f'content-desc="{take}" />{pause_node}</hierarchy>'
    ).encode()


@pytest.mark.parametrize(
    ("take", "pause", "expected"),
    [
        ("Start recording video", None, CaptureState.IDLE),
        ("Stop recording video", "Pause video recording", CaptureState.RECORDING),
        ("Stop recording video", "Resume video recording", CaptureState.PAUSED),
        ("Take photo", None, CaptureState.UNKNOWN),
        ("Stop recording video", None, CaptureState.UNKNOWN),
        ("Stop recording video", "unrecognized description", CaptureState.UNKNOWN),
    ],
)
def test_open_camera_states(take, pause, expected):
    assert classify(parse_dump(dump(take, pause))) is expected


def test_wrong_package_is_unknown():
    assert classify(parse_dump(dump("Start recording video", package="other.app"))) is CaptureState.UNKNOWN


def test_malformed_xml_is_rejected():
    with pytest.raises(InvalidDump):
        parse_dump(b"<hierarchy><node")


def test_unknown_pause_description_is_not_guessed():
    snapshot = UiSnapshot(
        package="net.sourceforge.opencamera",
        take_description="Stop recording video",
        pause_description="unrecognized description",
    )
    assert classify(snapshot) is CaptureState.UNKNOWN
