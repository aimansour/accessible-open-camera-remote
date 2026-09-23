from pathlib import Path


WEB = Path("src/oc_remote/web")


def test_page_has_native_browse_mode_controls_without_auto_announcements():
    html = (WEB / "index.html").read_text(encoding="utf-8")
    script = (WEB / "app.js").read_text(encoding="utf-8")
    assert "<main" in html and "<h1" in html and "<button" in html
    assert '<button id="camera"' in html
    assert '<button id="pause"' in html
    assert '<button id="verification"' in html
    for forbidden in ("aria-live", "role=\"status\"", "autofocus"):
        assert forbidden not in html
    for forbidden in ("keydown", "ArrowUp", "ArrowDown", "nvdaController", "speechSynthesis"):
        assert forbidden not in script


def test_both_languages_have_matching_camera_action_keys():
    script = (WEB / "app.js").read_text(encoding="utf-8")
    for key in ("start", "stop", "pause", "resume", "unknown", "verificationOn", "verificationOff"):
        assert script.count(f"{key}:") == 2
    for message in ("Camera state verified", "Unlock the phone and bring Open Camera to the foreground",
                    "Camera result uncertain; check the phone, then verify again"):
        assert script.count(f'"{message}":') == 2
