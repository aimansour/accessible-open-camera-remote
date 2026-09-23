"""Conservative interpretation of Open Camera's accessibility tree."""

from dataclasses import dataclass
from enum import StrEnum
from xml.etree import ElementTree


class InvalidDump(ValueError):
    """The phone did not return a usable UI hierarchy."""


class CaptureState(StrEnum):
    IDLE = "idle"
    RECORDING = "recording"
    PAUSED = "paused"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class UiSnapshot:
    package: str | None
    take_description: str | None
    pause_description: str | None


def parse_dump(xml: bytes) -> UiSnapshot:
    try:
        root = ElementTree.fromstring(xml)
    except ElementTree.ParseError as exc:
        raise InvalidDump("The phone UI could not be read") from exc
    if root.tag != "hierarchy":
        raise InvalidDump("The phone UI hierarchy is missing")

    take = []
    pause = []
    for node in root.iter("node"):
        resource_id = node.get("resource-id", "")
        if resource_id.endswith("/take_photo"):
            take.append(node)
        elif resource_id.endswith("/pause_video"):
            pause.append(node)
    if len(take) != 1 or len(pause) > 1:
        return UiSnapshot(None, None, None)
    take_node = take[0]
    if pause and pause[0].get("package") != take_node.get("package"):
        return UiSnapshot(None, None, None)
    return UiSnapshot(
        package=take_node.get("package"),
        take_description=take_node.get("content-desc"),
        pause_description=pause[0].get("content-desc") if pause else None,
    )


def classify(snapshot: UiSnapshot) -> CaptureState:
    if snapshot.package != "net.sourceforge.opencamera":
        return CaptureState.UNKNOWN
    if snapshot.take_description == "Start recording video" and snapshot.pause_description is None:
        return CaptureState.IDLE
    if snapshot.take_description == "Stop recording video":
        return {
            "Pause video recording": CaptureState.RECORDING,
            "Resume video recording": CaptureState.PAUSED,
        }.get(snapshot.pause_description, CaptureState.UNKNOWN)
    return CaptureState.UNKNOWN
