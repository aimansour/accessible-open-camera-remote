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
    label_definitions = script.split("const cameraButton", 1)[0]
    for key in ("start", "stop", "pause", "resume", "unknown", "verificationOn", "verificationOff"):
        assert label_definitions.count(f"{key}:") == 2
    for message in ("Camera state verified", "Unlock the phone and bring Open Camera to the foreground",
                    "Camera result uncertain; check the phone, then verify again"):
        assert script.count(f'"{message}":') == 2


def test_video_list_uses_labeled_folder_and_native_checkboxes():
    html = (WEB / "index.html").read_text(encoding="utf-8")
    script = (WEB / "app.js").read_text(encoding="utf-8")
    assert '<label for="phoneFolder"' in html
    assert '<ul id="videos"' in html
    assert 'document.createElement("input")' in script
    assert 'checkbox.type = "checkbox"' in script
    assert "innerHTML" not in script


def test_copy_controls_are_labeled_and_progress_is_plain_text():
    html = (WEB / "index.html").read_text(encoding="utf-8")
    assert '<label for="pcFolder"' in html
    assert '<button id="copy"' in html
    assert '<ul id="transferResults"' in html
    assert "aria-live" not in html


def test_mutation_controls_use_inline_delete_confirmation():
    html = (WEB / "index.html").read_text(encoding="utf-8")
    script = (WEB / "app.js").read_text(encoding="utf-8")
    for control in ('id="move"', 'id="rename"', 'id="delete"', 'id="confirmDelete"'):
        assert control in html
    assert '<label for="newStem"' in html
    assert 'id="deleteConfirmation"' in html
    assert "window.confirm" not in script and "window.alert" not in script


def test_camera_buttons_are_not_disabled_just_for_pending_verification():
    script = (WEB / "app.js").read_text(encoding="utf-8")
    assert 'String(status.busy ||' not in script
    assert 'confirmed_state' in script


def test_select_all_is_a_native_button_with_localized_toggle_labels():
    html = (WEB / "index.html").read_text(encoding="utf-8")
    script = (WEB / "app.js").read_text(encoding="utf-8")
    assert '<button id="selectAll"' in html
    assert script.count("selectAll:") == 2
    assert script.count("clearSelection:") == 2
    assert 'selectAllButton.addEventListener("click"' in script
