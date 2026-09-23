# Accessible Open Camera Control Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** Deliver a public, accessible Windows controller for Open Camera recording and verified video management over wireless ADB.

**Architecture:** A local Python service serves a plain HTML page to the user's normal browser. It sends volume key events and reads Open Camera state with ADB and uiautomator dump; file operations use ADB with integrity checks. There is no Android companion app, screen stream, or cloud service.

**Tech Stack:** Python 3.14, aiohttp 3.14.3, pytest 9 with pytest-asyncio 1.4, standard HTML/CSS/JavaScript, ADB platform-tools 37, PyInstaller 6.22.3, uv.

**Spec:** docs/superpowers/specs/2026-09-23-accessible-open-camera-control-design.md

## Global Constraints

- Target Windows 10/11. Initial device validation is Samsung Galaxy A15, Android 16, Open Camera 1.56.2.
- The phone and PC share Wi-Fi; wireless ADB is already paired. Always address the selected device by serial.
- The user switches TalkBack off manually before remote filming. The app never changes TalkBack settings. Stop verification before the user uses the phone.
- Send the camera command before waiting for verification. Never replay a toggle automatically after an uncertain result.
- Verification runs at session start and after a recording command, not as a continuous loop.
- The web UI must work with NVDA browse mode, use native controls, avoid focus capture and automatic NVDA speech, and offer Arabic and English.
- Play no sound on click or dispatch. Play a short PC tone only after a verified outcome or verification failure.
- Copy and move must verify size and SHA-256. A move deletes its source only after a verified local copy.
- No Android APK, screenshot capture, live camera view, cloud account, or external network listener.

## Review Focus

1. Open Camera is not foreground or the phone is locked: a recording request sends no volume key and returns a readable error. Test in Task 3.
2. A second click arrives while a UI dump is pending: only one volume key is sent, and no automatic retry occurs after timeout. Test in Task 3.
3. UI dump is malformed, stale, or uses an unrecognized description: state becomes UNKNOWN rather than a guessed recording state. Test in Tasks 1 and 3.
4. A filename contains Arabic, spaces, a newline, shell punctuation, or a path separator; a Windows destination already exists: safe names round-trip, traversal is rejected, and no file is overwritten. Test in Tasks 7 and 8.
5. ADB drops after copying but before a move deletes its source, or source content changes mid-copy: the phone copy remains and the PC result is not reported as verified. Test in Tasks 8 and 9.

## ملخص عربي للمراجعة

الخطة مرتبة في ثلاث مراحل. الأولى تبني إرسال أوامر التصوير عبر ADB وفحص الحالة باستخدام uiautomator dump ثم صفحة متصفح عربية وإنجليزية متوافقة مع وضع التصفح في NVDA. الثانية تعرض الفيديوهات وتنسخها مع فحص الحجم والبصمة، ثم تضيف النقل وإعادة التسمية والحذف بعد اختبار فهرس وسائط Android. الثالثة تختبر التجربة معك، وتجهز نسخة Windows قابلة للتشغيل، ثم تنشر المستودع والإصدار علنًا.

لا تتضمن الخطة تطبيقًا أو مكوّنًا إضافيًا على الهاتف. TalkBack توقفه وتشغّله أنت. عند إيقاف الفحص تتوقف أزرار التصوير، وعند تشغيله تُقرأ الحالة من جديد. اختبار الهاتف الفعلي محطة إلزامية مبكرة: لو طريقة ADB لا تحقق الحالة بثقة، نتوقف ونراجع التصميم قبل بناء بقية المزايا. لا تُحذف نسخة الهاتف في النقل إلا بعد التحقق من النسخة على الكمبيوتر.

## File map and interfaces

| File | Responsibility |
| --- | --- |
| pyproject.toml, uv.lock, .gitignore | Reproducible Python environment and repository hygiene |
| src/oc_remote/state.py | Capture states, UI XML parser, known Open Camera descriptions |
| src/oc_remote/adb.py | Selected-device subprocess transport, timeouts, dump cleanup |
| src/oc_remote/camera.py | Command state machine and verification lifecycle |
| src/oc_remote/server.py | Loopback HTTP API, session token, origin check |
| src/oc_remote/audio.py | Verified-result PC tones |
| src/oc_remote/catalog.py | Phone video listing, metadata, safe remote names |
| src/oc_remote/transfer.py | Verified single and batch copies |
| src/oc_remote/files.py | Move, rename, delete, media-index checks |
| src/oc_remote/diagnostics.py | Local timing/error log without media or UI-tree content |
| src/oc_remote/main.py | CLI startup, browser launch, shutdown |
| src/oc_remote/web/index.html, app.js, styles.css | Accessible Arabic/English browser page |
| tests/ | Pure, fake-ADB, HTTP, browser-contract, and gated device tests |
| docs/ | Arabic and English setup, operation, troubleshooting, and tested support |

All paths in the tasks below are relative to the repository root. Each test first fails against the previous task's tree, then passes after the smallest implementation. Commit only after the named checks pass.

## Phase A: remote recording and accessible page

### Task 1: State model and Open Camera UI parser

**Files:** Create pyproject.toml, .gitignore, src/oc_remote/__init__.py, src/oc_remote/state.py, tests/test_state.py.

**Interfaces:** Produce CaptureState, UiSnapshot(package: str | None, take_description: str | None, pause_description: str | None), parse_dump(xml: bytes) -> UiSnapshot, and classify(snapshot: UiSnapshot) -> CaptureState. Later tasks consume these exact names.

- [ ] **Step 1: Set up the project and write failing parser tests.** Create pyproject.toml as below, .gitignore containing .venv/, __pycache__/, .pytest_cache/, build/, and dist/, then run uv lock. Cover English 1.56.2 idle, recording and paused fixtures; wrong package; missing pause button; malformed XML raising InvalidDump; and an unknown localized pause description. Task 3 maps InvalidDump to UNKNOWN.

~~~toml
[build-system]
requires = ["hatchling>=1.27"]
build-backend = "hatchling.build"

[project]
name = "accessible-open-camera-remote"
version = "0.1.0"
requires-python = ">=3.14,<3.15"
dependencies = ["aiohttp==3.14.3"]

[dependency-groups]
dev = ["pytest>=9,<10", "pytest-asyncio==1.4.0", "pyinstaller==6.22.3"]

[tool.hatch.build.targets.wheel]
packages = ["src/oc_remote"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"
~~~

~~~python
def test_unknown_pause_description_is_not_guessed():
    snapshot = UiSnapshot(
        package="net.sourceforge.opencamera",
        take_description="Stop recording video",
        pause_description="unrecognized description",
    )
    assert classify(snapshot) is CaptureState.UNKNOWN
~~~

- [ ] **Step 2: Run red.** Run: uv run pytest tests/test_state.py -q. Expected: import or assertion failure.
- [ ] **Step 3: Implement the smallest model and XML parser.** Match nodes by Android resource-id suffix /take_photo and /pause_video, check package, and match known Open Camera 1.56.2 descriptions exactly. An absent pause button plus the known start label is IDLE. Stop plus known pause label is RECORDING; stop plus known resume label is PAUSED. Every other combination is UNKNOWN. Include a plain error for a photo-mode UI.

~~~python
class CaptureState(StrEnum):
    IDLE = "idle"
    RECORDING = "recording"
    PAUSED = "paused"
    UNKNOWN = "unknown"

def classify(s: UiSnapshot) -> CaptureState:
    if s.package != "net.sourceforge.opencamera":
        return CaptureState.UNKNOWN
    if s.take_description == "Start recording video" and s.pause_description is None:
        return CaptureState.IDLE
    if s.take_description == "Stop recording video":
        return {
            "Pause video recording": CaptureState.RECORDING,
            "Resume video recording": CaptureState.PAUSED,
        }.get(s.pause_description, CaptureState.UNKNOWN)
    return CaptureState.UNKNOWN
~~~

- [ ] **Step 4: Run green and syntax check.** Run: uv run pytest tests/test_state.py -q; uv run python -m compileall -q src. Expected: all selected tests pass, exit 0.
- [ ] **Step 5: Commit.** git add pyproject.toml uv.lock .gitignore src/oc_remote tests/test_state.py; git commit -m "feat: parse Open Camera recording state".

### Task 2: ADB transport and disposable UI dumps

**Files:** Create src/oc_remote/adb.py, tests/test_adb.py.

**Interfaces:** Produce AdbClient(serial: str, executable: Path, runner=None), async run(*args: str, timeout: float = 15) -> bytes, async press(keycode: int) -> None, async dump_ui() -> bytes, and async pull(remote: str, local: Path) -> None. The optional runner is a test subprocess substitute. Device serial is mandatory; never default to the first device.

- [ ] **Step 1: Write failing fake-subprocess tests.** Assert the exact adb argument prefix includes -s and the chosen serial; a timed-out command raises AdbTimeout; a nonzero exit raises AdbFailure; dump_ui always removes its unique /data/local/tmp XML file, including when reading fails.

~~~python
async def test_press_targets_selected_phone(fake_process):
    adb = AdbClient("phone-serial", Path("adb"), runner=fake_process)
    await adb.press(24)
    assert fake_process.calls[0][:4] == ("adb", "-s", "phone-serial", "shell")
    assert fake_process.calls[0][4:] == ("input", "keyevent", "24")
~~~

- [ ] **Step 2: Run red.** Run: uv run pytest tests/test_adb.py -q. Expected: import or assertion failure.
- [ ] **Step 3: Implement with asyncio.to_thread(subprocess.run).** Capture bytes and stderr, enforce per-command timeout, and use one unique XML path per dump. Run uiautomator dump to that path, read it with adb exec-out cat, and remove it in finally. Do not invoke dump when verification is paused; that gate belongs to Task 3.

~~~python
async def press(self, keycode: int) -> None:
    if keycode not in (24, 25):
        raise ValueError("Unsupported camera key")
    await self.run("shell", "input", "keyevent", str(keycode), timeout=3)
~~~

- [ ] **Step 4: Run green.** Run: uv run pytest tests/test_adb.py -q. Expected: all selected tests pass.
- [ ] **Step 5: Commit.** git add src/oc_remote/adb.py tests/test_adb.py; git commit -m "feat: add selected-device ADB transport".

### Task 3: Recording command state machine

**Files:** Create src/oc_remote/camera.py, tests/test_camera.py.

**Interfaces:** Produce CameraAction (START="start", STOP="stop", PAUSE="pause", RESUME="resume"), CameraStatus (state: CaptureState, verification_enabled: bool, busy: bool, message: str), TonePort protocol with success() and failure(), CameraController(adb, tone: TonePort), async start_session() -> CameraStatus, submit(action: CameraAction) -> asyncio.Task[CameraStatus], async stop_verification() -> CameraStatus, async start_verification() -> CameraStatus, and status() -> CameraStatus. submit reserves the command slot synchronously before scheduling the private async _perform; this makes two rapid HTTP requests safe.

- [ ] **Step 1: Write failing fake-ADB tests.** Use asyncio.Event to hold dump_ui open. Verify key 24 arrives before the held dump completes; a second action sends no key; timeout causes UNKNOWN and one failure tone but no retry; STOP is allowed from PAUSED; non-Open-Camera and locked snapshots send no key; stop_verification cancels an in-flight dump and disables buttons.

~~~python
async def test_second_click_during_verification_does_not_toggle_twice():
    task = controller.submit(CameraAction.START)
    await fake_adb.first_press.wait()
    with pytest.raises(CommandBusy):
        controller.submit(CameraAction.START)
    assert fake_adb.keys == [24]
    fake_adb.release_dump.set()
    await task
~~~

- [ ] **Step 2: Run red.** Run: uv run pytest tests/test_camera.py -q. Expected: import or assertion failure.
- [ ] **Step 3: Implement transition table and bounded verifier.** START requires IDLE and key 24; STOP requires RECORDING or PAUSED and key 24; PAUSE requires RECORDING and key 25; RESUME requires PAUSED and key 25. A cheap ADB window/keyguard preflight checks foreground and lock state before sending, without a slow UI dump; measure its latency in Task 4. submit marks busy before create_task. After press, inspect at most two fresh dumps within an 8-second overall deadline. Never send a second key as a retry. stop_verification cancels a pending dump and sets UNKNOWN; start_verification reads one fresh state before accepting actions. An unfamiliar description or InvalidDump stays UNKNOWN with an actionable message.

~~~python
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
~~~

- [ ] **Step 4: Run green and relevant regression tests.** Run: uv run pytest tests/test_state.py tests/test_adb.py tests/test_camera.py -q. Expected: all pass.
- [ ] **Step 5: Commit.** git add src/oc_remote/camera.py tests/test_camera.py; git commit -m "feat: verify recording transitions without retrying toggles".

### Task 4: Phone feasibility gate

**Files:** Create tests/device/test_recording.py and docs/device-test-notes.md.

**Interfaces:** Validate Tasks 1-3 on the paired Samsung device. This gate records observed XML labels and timings; it does not change the public CameraController interface. If Open Camera's actual labels, volume behavior, or uiautomator dump differ, correct the pure parser/transport and their tests before continuing.

- [ ] **Step 1: Write a gated device test.** Require OC_DEVICE_SERIAL and an explicit OC_DEVICE_TEST=1 so ordinary pytest never starts a recording. Capture an initial dump, start a short disposable recording, pause, resume, stop, and assert each recognized state. Keep the resulting test video for the user's inspection; do not delete a personal video.

~~~python
@pytest.mark.skipif(os.getenv("OC_DEVICE_TEST") != "1", reason="device test is opt-in")
async def test_real_recording_cycle(device_controller):
    assert (await device_controller.start_session()).state is CaptureState.IDLE
    assert (await device_controller.submit(CameraAction.START)).state is CaptureState.RECORDING
    assert (await device_controller.submit(CameraAction.PAUSE)).state is CaptureState.PAUSED
    assert (await device_controller.submit(CameraAction.RESUME)).state is CaptureState.RECORDING
    assert (await device_controller.submit(CameraAction.STOP)).state is CaptureState.IDLE
~~~

- [ ] **Step 2: Run red safely with no opt-in.** Run: uv run pytest tests/device/test_recording.py -q. Expected: skipped, no phone action. Then arrange the user's manual TalkBack-off and camera-ready state before the opt-in run.
- [ ] **Step 3: Run the opt-in cycle and record evidence.** Run adb devices -l, then in PowerShell after user readiness: $env:OC_DEVICE_TEST='1'; $env:OC_DEVICE_SERIAL=Read-Host 'Paste the exact connected ADB serial'; uv run pytest tests/device/test_recording.py -q -s. Record preflight time, command-to-key and key-to-state times, UI descriptions, TalkBack condition, and microphone behavior in docs/device-test-notes.md. Do not auto-select a serial when multiple devices exist.
- [ ] **Step 4: Apply only evidence-driven fixes and rerun.** Run: uv run pytest tests/test_state.py tests/test_adb.py tests/test_camera.py tests/device/test_recording.py -q. Expected: all unit tests pass and device cycle passes. If the device cycle cannot pass within this architecture, stop and ask for a design change before building the web or file layers.
- [ ] **Step 5: Commit.** git add tests/device/test_recording.py docs/device-test-notes.md src/oc_remote; git commit -m "test: validate recording control on Android 16".

### Task 5: Local HTTP API and request isolation

**Files:** Create src/oc_remote/server.py, tests/test_server.py.

**Interfaces:** Produce create_app(controller: CameraController, token: str) -> aiohttp.web.Application and require_local_origin_and_token(request: web.Request) -> None. GET / serves the page, GET /api/status returns CameraStatus JSON with snake_case field names, POST /api/camera starts a command and returns HTTP 202 or 409 for busy, POST /api/verification switches verification. POST requests require an exact same-origin Origin and X-Session-Token.

- [ ] **Step 1: Write failing HTTP tests.** An external Origin, absent token, or wrong token receives 403 with no ADB action. A valid camera POST returns 202 while the fake verifier is still blocked. Two POSTs during the pending operation make only one controller call.

~~~python
async def test_cross_origin_request_cannot_press_camera(client, fake_controller):
    response = await client.post(
        "/api/camera",
        json={"action": "start"},
        headers={"Origin": "https://other.example", "X-Session-Token": "valid"},
    )
    assert response.status == 403
    assert fake_controller.calls == []
~~~

- [ ] **Step 2: Run red.** Run: uv run pytest tests/test_server.py -q. Expected: import or assertion failure.
- [ ] **Step 3: Implement aiohttp routes and guards.** Serve a minimal inline HTML response at GET / until Task 6 adds the final page. Validate Host/Origin against the actual bound address and token. Keep task references until completion, and serialize status for polling. Bind only to 127.0.0.1 on port 0 when main.py is added in Task 6. Never expose a LAN listener.

~~~python
async def post_camera(request):
    require_local_origin_and_token(request)
    request_json = await request.json()
    action = CameraAction(request_json["action"])
    try:
        task = controller.submit(action)
    except CommandBusy:
        raise web.HTTPConflict(text="Camera command already in progress")
    request.app["camera_tasks"].add(task)
    return web.json_response({"accepted": True}, status=202)
~~~

- [ ] **Step 4: Run green.** Run: uv run pytest tests/test_server.py tests/test_camera.py -q. Expected: all pass.
- [ ] **Step 5: Commit.** git add src/oc_remote/server.py tests/test_server.py; git commit -m "feat: expose loopback camera API".

### Task 6: Browse-mode page, languages, and result tones

**Files:** Create src/oc_remote/web/index.html, app.js, styles.css, src/oc_remote/audio.py, src/oc_remote/main.py, tests/test_web_contract.py, tests/test_audio.py.

**Interfaces:** main.main() starts the loopback server and opens the default browser. The browser reads /api/status at a modest interval and POSTs commands with the session token. ToneSink.success() and ToneSink.failure() are called only by completed verification paths.

- [ ] **Step 1: Write failing contract and audio tests.** Assert semantic main and headings; all action elements are native button; Arabic and English have the same message keys; no aria-live, role=status, autofocus, custom arrow-key navigation, or NVDA Controller call; fake winsound receives no call on dispatch and one call after result.

~~~python
def test_page_has_no_auto_announcing_status():
    html = Path("src/oc_remote/web/index.html").read_text(encoding="utf-8")
    assert "<main" in html and "<button" in html
    assert "aria-live" not in html and "autofocus" not in html
~~~

- [ ] **Step 2: Run red.** Run: uv run pytest tests/test_web_contract.py tests/test_audio.py -q. Expected: missing-file or assertion failure.
- [ ] **Step 3: Implement the page and tones.** Keep one stable DOM button per camera action position; update visible text and accessible name only after confirmed state. Keep the user's focus where it is. Show pending/error text without automatic announcements. The verification button changes between Arabic/English equivalents of “Stop verification” and “Start verification”; while off, camera buttons have aria-disabled=true and explain why. Use winsound on a worker thread for two short distinguishable PC tones after outcomes. Main discovers the selected device, opens the URL in the normal browser, and shuts down cleanly.

~~~javascript
const labels = {
  ar: { start: "بدء التسجيل", stop: "إنهاء التسجيل", pause: "إيقاف مؤقت", resume: "استئناف", unknown: "حالة التسجيل غير معروفة" },
  en: { start: "Start recording", stop: "Stop recording", pause: "Pause", resume: "Resume", unknown: "Recording state unknown" }
};
function renderCamera(status) {
  const primary = status.state === "unknown" ? "unknown" : status.state === "idle" ? "start" : "stop";
  const secondary = status.state === "paused" ? "resume" : "pause";
  cameraButton.textContent = labels[language][primary];
  cameraButton.setAttribute("aria-disabled", String(status.busy || !status.verification_enabled || status.state === "unknown"));
  pauseButton.textContent = labels[language][secondary];
  pauseButton.setAttribute("aria-disabled", String(status.busy || !status.verification_enabled || status.state === "idle" || status.state === "unknown"));
}
~~~

- [ ] **Step 4: Run tests and browser/NVDA acceptance.** Run: uv run pytest tests/test_web_contract.py tests/test_audio.py tests/test_server.py -q. Start the local server; verify with NVDA that browse mode navigates headings and buttons normally, that no click tone/speech is added, that a verified result tone plays, and that focus stays in place. Record manual observations in docs/device-test-notes.md.
- [ ] **Step 5: Commit.** git add src/oc_remote/web src/oc_remote/audio.py src/oc_remote/main.py tests/test_web_contract.py tests/test_audio.py docs/device-test-notes.md; git commit -m "feat: add accessible bilingual camera page".

## Phase B: verified video management

### Task 7: Video catalog and safe names

**Files:** Create src/oc_remote/catalog.py, tests/test_catalog.py. Modify src/oc_remote/server.py and src/oc_remote/web/app.js.

**Interfaces:** Produce VideoEntry(name: str, size: int, modified: float, duration_ms: int | None = None), parse_listing(raw: bytes) -> list[VideoEntry], validate_name(name: str) -> str, and async list_videos(adb, folder: str) -> list[VideoEntry]. GET /api/videos returns the sorted catalog; a labeled page setting chooses an Open Camera folder constrained to shared storage.

- [ ] **Step 1: Write failing listing tests.** Parse NUL-delimited name/size/time triples; preserve Arabic and newline names; reject slash, backslash, dot-only names, and non-video extensions; sort newest first; expose duration_ms only when a MediaStore duration can be matched confidently. Block file mutation while recording, paused, or unknown.

~~~python
def test_newline_and_arabic_filename_round_trips():
    raw = "فيديو\nأول.mp4\0" + "1024\0" + "1700000000.0\0"
    assert parse_listing(raw.encode("utf-8"))[0].name == "فيديو\nأول.mp4"
~~~

- [ ] **Step 2: Run red.** Run: uv run pytest tests/test_catalog.py -q. Expected: import or assertion failure.
- [ ] **Step 3: Implement bounded folder listing.** The default folder is /sdcard/DCIM/OpenCamera; expose a labeled setting for a different shared-storage Open Camera folder. Use the selected serial and Android toybox find with maxdepth 1, type f, and NUL-separated printf fields. Treat the output as bytes, validate each basename, and raise InvalidListing on malformed output rather than silently skipping it. Query MediaStore duration by exact file identity where available; otherwise return None. Add GET /api/videos and a native checkbox per video; no automatic focus movement. While the camera is RECORDING, PAUSED, or UNKNOWN, disable file mutation actions; after STOP and file finalization, list files as complete.

~~~python
def validate_name(name: str) -> str:
    if not name or name in (".", "..") or "/" in name or "\\" in name or "\0" in name:
        raise InvalidVideoName(name)
    if Path(name).suffix.lower() not in (".mp4", ".mkv", ".3gp"):
        raise InvalidVideoName(name)
    return name
~~~

- [ ] **Step 4: Run green and web checks.** Run: uv run pytest tests/test_catalog.py tests/test_server.py tests/test_web_contract.py -q. Expected: all pass.
- [ ] **Step 5: Commit.** git add src/oc_remote/catalog.py src/oc_remote/server.py src/oc_remote/web/app.js tests/test_catalog.py tests/test_server.py; git commit -m "feat: list completed Open Camera videos".

### Task 8: Verified copy and batch copy

**Files:** Create src/oc_remote/transfer.py, tests/test_transfer.py. Modify src/oc_remote/server.py and src/oc_remote/web/app.js.

**Interfaces:** Produce TransferResult(name, outcome, destination, message), publish_without_overwrite(partial_path: Path, destination: Path) -> None, async copy_one(adb, entry: VideoEntry, phone_folder: str, pc_folder: Path) -> TransferResult, and async copy_many(adb, entries: list[VideoEntry], phone_folder: str, pc_folder: Path) -> list[TransferResult]. POST /api/copy queues a selected list and GET /api/transfers reports per-file stages (waiting, copying, hashing, verified, failed) and batch count.

- [ ] **Step 1: Write failing transfer tests.** Use fake ADB and tmp_path: source changes after pull, hash differs, destination already exists, path is outside selected folder, remote disconnects, and one file fails in a three-file batch. In every failure, keep the phone source and do not publish a final PC file.

~~~python
async def test_bad_hash_never_publishes_destination(fake_adb, tmp_path):
    fake_adb.remote_hash = "0" * 64
    result = await copy_one(fake_adb, VideoEntry("clip.mp4", 4, 1.0),
                            "/sdcard/DCIM/OpenCamera", tmp_path)
    assert result.outcome == "failed"
    assert not (tmp_path / "clip.mp4").exists()
    assert fake_adb.removed == []
~~~

- [ ] **Step 2: Run red.** Run: uv run pytest tests/test_transfer.py -q. Expected: import or assertion failure.
- [ ] **Step 3: Implement copy with bounded temporary files.** Offer a labeled PC destination text field defaulting to the user's Videos/OpenCameraRemote folder, validate it, and create a unique .partial file there. Check available space; read remote size/mtime; adb pull; hash local bytes with hashlib.sha256 and remote with Android sha256sum -b; check remote size/mtime again; publish with Path.rename on Windows, which fails if the destination exists. Delete only the partial on failure. Run a batch sequentially, report per-file stages and batch count, and play one final verified-result tone. Treat filenames as data, never as raw shell syntax.

~~~python
if before.size != after.size or before.modified != after.modified:
    raise SourceChanged(entry.name)
if local_size != after.size or local_hash != remote_hash:
    raise IntegrityFailure(entry.name)
publish_without_overwrite(partial_path, destination)
~~~

- [ ] **Step 4: Run green.** Run: uv run pytest tests/test_transfer.py tests/test_catalog.py tests/test_server.py -q. Expected: all pass.
- [ ] **Step 5: Commit.** git add src/oc_remote/transfer.py src/oc_remote/server.py src/oc_remote/web/app.js tests/test_transfer.py; git commit -m "feat: verify single and batch video copies".

### Task 9: Move, rename, delete, and Android media index

**Files:** Create src/oc_remote/files.py, tests/test_files.py, tests/device/test_media_index.py. Modify src/oc_remote/server.py and src/oc_remote/web/app.js.

**Interfaces:** Produce async move_one(adb: AdbClient, entry: VideoEntry, phone_folder: str, pc_folder: Path) -> TransferResult; async rename_one(adb: AdbClient, entry: VideoEntry, phone_folder: str, new_stem: str) -> VideoEntry; async delete_one(adb: AdbClient, entry: VideoEntry, phone_folder: str, confirmed_name: str) -> None; and async verify_media_index(adb: AdbClient, old_name: str | None, new_name: str | None) -> bool. The move function consumes copy_one and removes the phone source only after TransferResult.outcome == "verified". POST /api/move, /api/rename, and /api/delete call these functions; the delete endpoint requires the exact selected filename in confirmed_name from an inline confirmation step.

- [ ] **Step 1: Write failing mutation tests.** Failed copy never removes source; successful copy followed by ADB loss reports uncertain but leaves the verified PC copy; rename preserves extension and rejects an existing target; deletion requires a second explicit confirmation matching the selected file; shell punctuation is quoted; each successful change is checked in filesystem and media index. RECORDING, PAUSED, and UNKNOWN camera states reject phone file mutation.

~~~python
async def test_move_does_not_delete_after_failed_copy(fake_adb, tmp_path):
    fake_adb.remote_hash = "0" * 64
    result = await move_one(fake_adb, VideoEntry("a.mp4", 4, 1.0),
                            "/sdcard/DCIM/OpenCamera", tmp_path)
    assert result.outcome == "failed"
    assert fake_adb.removed == []
~~~

- [ ] **Step 2: Run red.** Run: uv run pytest tests/test_files.py -q. Expected: import or assertion failure.
- [ ] **Step 3: Implement guarded mutations and a device gate.** Pass validated paths through shlex.quote before Android shell operations. Confirm a file still matches the selected size/mtime before any rename or delete. Rename by changing the stem while keeping its extension. After mutation, query both the filesystem and MediaStore video row; use the Android media scan request if index refresh is needed. The device test creates its own tiny file under the Open Camera folder, checks rename and delete index behavior, and cleans up only that test file. If the media index cannot be made consistent using ADB alone on Android 16, stop and revise the approved architecture instead of shipping partial behavior.

~~~python
copy_result = await copy_one(adb, entry, phone_folder, pc_folder)
if copy_result.outcome != "verified":
    return copy_result
await assert_source_unchanged(adb, entry)
await remove_remote(adb, entry.name)
await verify_media_index(adb, old_name=entry.name, new_name=None)
~~~

- [ ] **Step 4: Run green and gated phone check.** Run: uv run pytest tests/test_files.py tests/test_transfer.py -q. After the user confirms the test folder is safe, set OC_DEVICE_TEST=1 and run uv run pytest tests/device/test_media_index.py -q -s. Expected: both filesystem and index show the same mutation.
- [ ] **Step 5: Commit.** git add src/oc_remote/files.py src/oc_remote/server.py src/oc_remote/web/app.js tests/test_files.py tests/device/test_media_index.py; git commit -m "feat: guard video move rename and delete".

## Phase C: acceptance and public delivery

### Task 10: Full workflow acceptance and recovery

**Files:** Create src/oc_remote/diagnostics.py, tests/test_recovery.py, tests/test_diagnostics.py, docs/acceptance-ar.md, docs/acceptance-en.md. Modify src/oc_remote/main.py and affected modules only for failures found.

**Interfaces:** No new public API. This task verifies the user journey across startup, control, pause verification, manual phone use, resume, stop, batch copy, rename, move, delete, and reconnect.

- [ ] **Step 1: Write failing recovery tests.** Start with a lost ADB connection after command dispatch and after partial copy; ensure camera state becomes UNKNOWN, no second key is sent, and partial copies are offered for cleanup. Restart the service and require a fresh dump before recording controls return. A diagnostics test feeds a fake XML dump and a video filename through logging and asserts neither appears in the exported log.

~~~python
async def test_restart_requires_fresh_phone_state(fake_adb, fake_tone):
    controller = CameraController(fake_adb, fake_tone)
    assert controller.status().state is CaptureState.UNKNOWN
    fake_adb.dump_bytes = IDLE_DUMP
    assert (await controller.start_session()).state is CaptureState.IDLE
~~~

- [ ] **Step 2: Run red.** Run: uv run pytest tests/test_recovery.py tests/test_diagnostics.py -q. Expected: import or assertion failure.
- [ ] **Step 3: Implement recovery, sanitized diagnostics, and acceptance scripts.** Show connection and uncertain states in both languages. Log only event code, elapsed milliseconds, ADB exit status, and device model; never log filenames, video bytes, or XML dumps. Document exact NVDA browse-mode steps and expected button-name/tone changes, including the manual TalkBack off/on sequence. Include a PC folder copy/move check and a phone gallery rename/delete check. Record device/version/timings from actual runs; do not claim support for untested configurations.

~~~python
async def reconnect(controller: CameraController) -> CameraStatus:
    await controller.stop_verification()
    return await controller.start_verification()
~~~
- [ ] **Step 4: Run full suite and manual acceptance.** Run: uv run pytest -q; uv run python -m compileall -q src. Then run the Arabic NVDA and TalkBack acceptance checklist with the user and record the results. Fix observed failures and rerun only the affected checks plus full suite before committing.
- [ ] **Step 5: Commit.** git add src tests docs/acceptance-ar.md docs/acceptance-en.md; git commit -m "test: verify complete accessible filming workflow".

### Task 11: Windows distribution and documentation

**Files:** Create README.md, README.ar.md, LICENSE, docs/install-ar.md, docs/install-en.md, tools/build-windows.ps1, tests/test_distribution.py, .github/workflows/checks.yml. Modify pyproject.toml and src/oc_remote/main.py only as needed for packaged paths.

**Interfaces:** A Windows release directory contains the program, web assets, and a verified ADB installation path. Starting the executable opens the local browser page without requiring Python or development tools.

- [ ] **Step 1: Write failing distribution checks.** Assert packaged assets exist, the executable can resolve the ADB binary, the local server binds only to 127.0.0.1, and README instructions name the manual TalkBack and wireless ADB setup. The GitHub workflow runs unit tests on Windows.

~~~python
def test_packaged_assets_are_present(package_root):
    assert (package_root / "oc_remote" / "web" / "index.html").is_file()
    assert (package_root / "adb" / "adb.exe").is_file()
~~~

- [ ] **Step 2: Run red.** Run: uv run pytest tests/test_distribution.py -q. Expected: missing package assets.
- [ ] **Step 3: Implement the Windows build script.** Use PyInstaller --onedir with --contents-directory . for Python 3.14. Add HTML/CSS/JS assets and the three official Android platform-tools Windows binaries adb.exe, AdbWinApi.dll, and AdbWinUsbApi.dll to the release directory. Resolve bundled ADB first, then an explicitly selected system ADB. Keep binaries out of Git source.

~~~powershell
uv run pyinstaller --onedir --contents-directory . --name OpenCameraRemote --add-data "src/oc_remote/web;oc_remote/web" src/oc_remote/main.py
$adbDir = Split-Path (Get-Command adb).Source
New-Item -ItemType Directory -Force -Path 'dist/OpenCameraRemote/adb' | Out-Null
foreach ($name in @('adb.exe','AdbWinApi.dll','AdbWinUsbApi.dll')) {
    Copy-Item -LiteralPath (Join-Path $adbDir $name) -Destination (Join-Path 'dist/OpenCameraRemote/adb' $name)
}
~~~

- [ ] **Step 4: Write installation and contributor docs.** Use the MIT license for this repository's original code; copy no Open Camera code. Write Arabic and English installation, keyboard usage, recovery, privacy, version support, build, test, and platform-tools notice documentation. Create the Windows GitHub test workflow.
- [ ] **Step 5: Verify the release package.** Run: uv run pytest -q; powershell -File tools/build-windows.ps1; then start the built executable and confirm the browser opens, a missing phone is reported clearly, and a connected phone works with the acceptance checklist. Check the official platform-tools redistribution terms and include required notices before the package is uploaded. Run git diff --check.
- [ ] **Step 6: Commit.** git add README.md README.ar.md LICENSE docs tools tests/test_distribution.py .github/workflows/checks.yml pyproject.toml src/oc_remote/main.py; git commit -m "build: package tested Windows release".

### Task 12: Publish the tested project

**Files:** Create docs/release-notes.md. Modify README.md and README.ar.md with the actual public repository and release links.

**Interfaces:** The public repository and release point to the exact tested commit and Windows package from Task 11. No code interface changes.

- [ ] **Step 1: Verify publication inputs.** Run git status --short, git log -1 --oneline, gh auth status, and git grep -n -I -E 'ghp_|github_pat_|BEGIN.*PRIVATE KEY' -- . to scan tracked files. Require a clean tree, authorized GitHub account, passing Task 11 evidence, a reviewed platform-tools notice, and the user's completed NVDA acceptance observations.
- [ ] **Step 2: Create the public GitHub repository.** Run gh repo create accessible-open-camera-remote --public --source . --push. If that name is unavailable, choose a descriptive available name and record the resulting URL; do not create duplicate repositories. Run gh repo view --json nameWithOwner,url,visibility and require visibility PUBLIC.
- [ ] **Step 3: Create and verify a tagged release.** Write docs/release-notes.md with tested OS, Android, Open Camera, ADB, known limits, and installation link. Run Compress-Archive -Path dist/OpenCameraRemote -DestinationPath dist/OpenCameraRemote.zip in PowerShell, then gh release create v0.1.0 dist/OpenCameraRemote.zip --notes-file docs/release-notes.md. Run gh release view v0.1.0 --json url,assets to confirm the asset.
- [ ] **Step 4: Add public links and recheck.** Put the actual repository and release URLs in both READMEs; run uv run pytest -q and git diff --check.
- [ ] **Step 5: Commit and push final docs.** git add README.md README.ar.md docs/release-notes.md; git commit -m "docs: link public release"; git push. Verify the public workflow result and report the repository and release links.

## Final evidence

Before claiming completion, collect the full pytest result, package startup result, the device control and media-index test results, the user's NVDA/TalkBack acceptance observations, git status, public repository URL, and release URL. Report any untested platform or locale as unverified rather than supported.
