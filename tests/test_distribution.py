"""Release packaging contract, with an opt-in check of a built artifact."""

import os
from pathlib import Path

import pytest

from oc_remote.main import resolve_adb_path


ROOT = Path(__file__).resolve().parents[1]


def test_bundled_adb_is_preferred_when_complete(tmp_path, monkeypatch):
    bundled = tmp_path / "adb"
    bundled.mkdir()
    for name in ("adb.exe", "AdbWinApi.dll", "AdbWinUsbApi.dll", "NOTICE.txt"):
        (bundled / name).write_bytes(b"test")
    monkeypatch.setattr("oc_remote.main.sys.frozen", True, raising=False)
    monkeypatch.setattr("oc_remote.main.sys._MEIPASS", str(tmp_path), raising=False)
    assert resolve_adb_path() == bundled / "adb.exe"


def test_incomplete_bundled_adb_fails_clearly(tmp_path, monkeypatch):
    bundled = tmp_path / "adb"
    bundled.mkdir()
    (bundled / "adb.exe").write_bytes(b"test")
    monkeypatch.setattr("oc_remote.main.sys.frozen", True, raising=False)
    monkeypatch.setattr("oc_remote.main.sys._MEIPASS", str(tmp_path), raising=False)
    with pytest.raises(RuntimeError, match="ADB"):
        resolve_adb_path()


def test_explicit_adb_path_recovers_an_incomplete_bundle(tmp_path, monkeypatch):
    system_adb = tmp_path / "other" / "adb.exe"
    system_adb.parent.mkdir()
    system_adb.write_bytes(b"test")
    monkeypatch.setattr("oc_remote.main.sys.frozen", True, raising=False)
    monkeypatch.setattr("oc_remote.main.sys._MEIPASS", str(tmp_path), raising=False)
    assert resolve_adb_path(str(system_adb)) == system_adb


def test_build_and_install_instructions_cover_required_components():
    build = (ROOT / "tools" / "build-windows.ps1").read_text(encoding="utf-8")
    assert "--onedir" in build and "--contents-directory" in build
    for name in ("adb.exe", "AdbWinApi.dll", "AdbWinUsbApi.dll", "NOTICE.txt"):
        assert name in build
    for name in ("README.md", "README.ar.md", "docs/install-en.md", "docs/install-ar.md"):
        instructions = (ROOT / name).read_text(encoding="utf-8")
        assert "TalkBack" in instructions
        assert "ADB" in instructions
    workflow = (ROOT / ".github" / "workflows" / "checks.yml").read_text(encoding="utf-8")
    assert "windows-latest" in workflow and "pytest" in workflow
    startup = (ROOT / "src" / "oc_remote" / "main.py").read_text(encoding="utf-8")
    assert 'web.TCPSite(runner, "127.0.0.1", 0)' in startup


@pytest.mark.skipif(not os.getenv("OC_PACKAGE_ROOT"), reason="set OC_PACKAGE_ROOT after building")
def test_built_release_contains_executable_web_assets_and_adb():
    package = Path(os.environ["OC_PACKAGE_ROOT"])
    assert (package / "OpenCameraRemote.exe").is_file()
    for name in ("index.html", "app.js", "styles.css"):
        assert (package / "oc_remote" / "web" / name).is_file()
    for name in ("adb.exe", "AdbWinApi.dll", "AdbWinUsbApi.dll", "NOTICE.txt"):
        assert (package / "adb" / name).is_file()
    assert (package / "LICENSE.txt").is_file()
    assert (package / "licenses" / "PYTHON_LICENSE.txt").is_file()
    assert any((package / "licenses").glob("pyinstaller-*.dist-info/licenses/COPYING.txt"))
