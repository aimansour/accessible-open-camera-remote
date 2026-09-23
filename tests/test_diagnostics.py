import json
import subprocess
from pathlib import Path

import pytest

from oc_remote.adb import AdbClient, AdbFailure
from oc_remote.diagnostics import DiagnosticLog


def test_export_contains_safe_fields_but_no_xml_or_video_name(tmp_path):
    log = DiagnosticLog(tmp_path / "diagnostics.jsonl", "SM-A155F")
    dump = '<node content-desc="Secret spoken sentence" />'
    filename = "private recording.mp4"
    log.record("adb_failure", elapsed_ms=273, adb_status=1,
               xml=dump, filename=filename, command=f"adb pull {filename}")
    data = (tmp_path / "diagnostics.jsonl").read_text(encoding="utf-8")
    assert dump not in data and filename not in data
    event = json.loads(data)
    assert event["event"] == "adb_failure"
    assert event["elapsed_ms"] == 273
    assert event["adb_status"] == 1
    assert event["device_model"] == "SM-A155F"


def test_invalid_event_code_cannot_inject_private_text(tmp_path):
    log = DiagnosticLog(tmp_path / "diagnostics.jsonl", "SM-A155F")
    log.record("private recording.mp4", elapsed_ms=1, adb_status=0)
    assert "private recording.mp4" not in (tmp_path / "diagnostics.jsonl").read_text()


async def test_adb_failure_log_omits_command_and_device_output(tmp_path):
    log = DiagnosticLog(tmp_path / "diagnostics.jsonl", "SM-A155F")

    def runner(command, **kwargs):
        return subprocess.CompletedProcess(command, 1, b"private recording.mp4", b"secret XML")

    adb = AdbClient("serial", Path("adb"), runner=runner, diagnostics=log)
    with pytest.raises(AdbFailure):
        await adb.run("pull", "private recording.mp4", "destination")
    content = log.path.read_text(encoding="utf-8")
    assert "private recording.mp4" not in content
    assert "secret XML" not in content
    assert json.loads(content)["adb_status"] == 1
