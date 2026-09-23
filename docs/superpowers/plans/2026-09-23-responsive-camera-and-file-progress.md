# Responsive Camera and File Progress Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a blind NVDA user send valid Open Camera actions in quick succession without waiting for UI dumps, while giving truthful file-operation progress and keeping camera commands responsive during old-video operations.

**Architecture:** Keep one ordered camera key dispatcher and a separate generation-aware verifier. The browser shows the accepted, predicted camera state immediately; confirmed state remains a separate safety gate for new destructive file operations. File mutations expose a small progress job, while camera ADB commands can run independently of old-video copy or deletion.

**Tech Stack:** Python 3.14, asyncio, aiohttp, ADB wireless, Android MediaStore, native HTML/JavaScript, pytest, NVDA on Windows.

**Spec:** `docs/superpowers/specs/2026-09-23-responsive-camera-and-file-progress-design.md`; existing foundation in `docs/superpowers/specs/2026-09-23-accessible-open-camera-control-design.md`.

## Global Constraints

- Work in the current `main` checkout; the user declined a separate worktree.
- Implement inline without subagents; the user explicitly requested this.
- Preserve normal NVDA browse mode: native buttons, labels and checkboxes; no focus trap, `aria-live`, synthetic speech, or click tone.
- No phone APK, screen stream, or automatic TalkBack changes. Verification uses `uiautomator dump` only while the user has manually turned TalkBack off.
- A camera key is never retried automatically; a failed or unverified sequence becomes UNKNOWN until a fresh verification.
- One result tone per unresolved action burst; a rapid START → STOP has one tone after idle and a finalized video are verified.
- File operations may continue on a previously selected video while a new recording begins; no new phone mutation starts from an unconfirmed camera state.
- Never delete a personal video in tests. Device mutation tests use only random names they created in `/sdcard/DCIM/OpenCamera` and clean up only those names.

## Review Focus

1. Two clicks before the first HTTP response must become ordered START → STOP, not two START requests. Task 4 has a browser test that delays the first response.
2. A stale dump returning after a newer command must not change the button or play a tone. Task 2 has a controlled verifier test.
3. ADB failure after one dispatched key must clear unsent keys and prohibit another until resynchronization. Task 2 has a failure test.
4. Missing baseline or an unfinished MP4 after rapid STOP must never produce a success tone. Task 3 has both tests.
5. A camera key accepted during copy or deletion of an old video must not wait for the file job, while the file still uses its captured identity. Task 5 has a server concurrency test and Task 8 has a phone gate.

## File map

- `src/oc_remote/camera.py`: predicted and confirmed states, ordered dispatcher, generation-aware verification, stop/reconnect semantics.
- `src/oc_remote/recording_evidence.py`: lightweight baseline and finalized-video check, separate from UI classification and file mutation.
- `src/oc_remote/server.py`: status contract, file progress job, independent camera request acceptance, strict mutation gate.
- `src/oc_remote/files.py`: targeted delete postconditions and stage callback, preserving MediaStore and filesystem checks.
- `src/oc_remote/web/app.js`, `index.html`: optimistic button names, serialized HTTP requests, delete stages, select-all.
- `tests/test_camera.py`, `test_recording_evidence.py`, `test_server.py`, `test_files.py`, `test_web_contract.py`: deterministic failure and concurrency checks.
- `tests/device/test_rapid_controls.py`, `tests/device/test_media_index.py`, `docs/acceptance-ar.md`, `docs/acceptance-en.md`, `docs/device-test-notes.md`: opt-in phone and NVDA acceptance evidence.

## Preflight: preserve the recovery checkpoint

The working tree already contains tested but uncommitted recovery and sanitized-diagnostics work from Task 10 of the original plan. Before Task 1, run `uv run pytest -q` and `uv run python -m compileall -q src`, review `git diff --check` and the diff, then commit only `src/oc_remote/adb.py`, `camera.py`, `main.py`, `server.py`, `web/app.js`, `diagnostics.py`, `tests/test_recovery.py`, `test_diagnostics.py`, `test_server.py`, and `docs/acceptance-ar.md` / `acceptance-en.md` as `test: harden recovery and private diagnostics`. The last observed suite was `107 passed, 2 skipped`; rerun it fresh. Do not include this new plan or the user's responsive behavior in that checkpoint commit. Keep the original Task 10 ledger open until final acceptance.

---

### Task 1: Camera state contract and acceptance queue

**Files:** Modify `src/oc_remote/camera.py`, `tests/test_camera.py`, `tests/test_recovery.py`.

**Interfaces:** `CameraStatus` adds `confirmed_state: CaptureState` and `generation: int` while retaining `state`, `verification_enabled`, `busy`, and `message`; `state` is predicted while commands are pending. `CameraController.submit(CameraAction) -> asyncio.Task[CameraStatus]` still returns a tracked task. `CameraController.status()` is side-effect-free. `CommandBusy` is used only for a full eight-intent queue or an explicit resynchronization, not for an ordinary ongoing dump.

- [ ] **Step 1: Write failing tests.** Use a fake ADB whose first `dump_ui()` waits on an event. After an initial IDLE dump, submit START, wait until key 24 is sent and its result dump begins, then submit STOP. Assert predicted state becomes IDLE and both keys `[24, 24]` are sent before releasing the dump. Also queue a third action and make the second `press()` raise `AdbFailure`; assert no third key, UNKNOWN state, and one failure tone.

```python
start = controller.submit(CameraAction.START)
await adb.first_key.wait()
stop = controller.submit(CameraAction.STOP)
await adb.second_key.wait()  # first result dump is still held
assert controller.status().state is CaptureState.IDLE
assert adb.keys == [24, 24]
```

- [ ] **Step 2: Run red.** `uv run pytest tests/test_camera.py tests/test_recovery.py -q`; expect the second submit to raise `CommandBusy` and the confirmed-state assertion to fail.
- [ ] **Step 3: Implement the state machine.** Keep a `deque[tuple[int, CameraAction]]`, one sender task, one verifier task, a monotonic `generation`, predicted and confirmed states, and a fixed cap of eight unresolved accepted actions. Apply the predicted transition synchronously in `submit()`. The sender runs `_preflight()` and `adb.press()` for each entry without awaiting a UI dump, then schedules a basic verifier after the queue drains so existing single-action tone tests still pass. The task returned by `submit()` resolves only when that generation has a verified or uncertain outcome. Any send failure clears the deque, sets both states UNKNOWN, and emits one failure tone. Make `stop_verification()` cancel queued intents and mark UNKNOWN without sending a compensating key.

```python
def submit(self, action):
    if not self._verification_enabled or self._state not in ALLOWED[action]:
        raise CommandUnavailable()
    if self._unresolved >= 8:
        raise CommandBusy()
    self._generation += 1
    self._unresolved += 1
    self._state = EXPECTED[action]
    self._pending.append((self._generation, action))
    self._ensure_sender()
    return asyncio.create_task(self._await_generation(self._generation))
```

- [ ] **Step 4: Run green and regression suite.** `uv run pytest tests/test_camera.py tests/test_recovery.py -q`, then `uv run pytest -q`. Fix tests that previously treated `busy` as a ban on every camera command; retain the file safety assertion against `confirmed_state` and pending work.
- [ ] **Step 5: Commit.** `git add src/oc_remote/camera.py tests/test_camera.py tests/test_recovery.py; git commit -m "feat: queue camera intents without waiting for dumps"`.

### Task 2: Generation-aware verifier and result tones

**Files:** Modify `src/oc_remote/camera.py`, `tests/test_camera.py`, `tests/test_recovery.py`.

**Interfaces:** The sender schedules one verifier for the latest `generation`; verification may overlap sending a later key. Only a verifier whose captured generation still equals `CameraController._generation` may apply its state or play a tone. `start_verification()` re-reads actual Open Camera state and clears an UNKNOWN fault only after a valid dump.

- [ ] **Step 1: Write failing tests.** Hold dump A, submit START, then STOP, release dump A with RECORDING and dump B with IDLE. Assert A produces no tone or state rollback, B produces one success tone. Make B raise `AdbFailure` and assert UNKNOWN, queued intents cleared, one failure tone, and no automatic key retry. Include stopping verification during a pending dump: no result tone and no further key.

```python
await adb.dump_a_started.wait()
controller.submit(CameraAction.STOP)
adb.release_dump_a.set()
await controller.wait_until_settled()
assert tone.events == ["success"]
assert controller.status().confirmed_state is CaptureState.IDLE
```

- [ ] **Step 2: Run red.** `uv run pytest tests/test_camera.py tests/test_recovery.py -q`; expect stale results to change state or the new `wait_until_settled()` test hook to be missing.
- [ ] **Step 3: Implement latest-generation verification.** A dump may finish after a newer key is sent, but its result is discarded. After the sender drains, verify the latest predicted state within a bounded deadline; a mismatch or unreadable dump makes the state UNKNOWN. Provide `wait_until_settled()` as an internal async test/cleanup method, not an HTTP API. Record only `camera_verified` or `camera_uncertain` diagnostic codes. Emit a result tone only when the latest generation settles.

```python
observed = classify(parse_dump(await self.adb.dump_ui()))
if captured_generation != self._generation:
    continue
if observed is self._state:
    self._confirmed_state = observed
    self.tone.success()
else:
    self._set_unknown_and_fail()
```

- [ ] **Step 4: Run green.** `uv run pytest tests/test_camera.py tests/test_recovery.py -q` and `uv run pytest -q`.
- [ ] **Step 5: Commit.** `git add src/oc_remote/camera.py tests/test_camera.py tests/test_recovery.py; git commit -m "feat: verify only the latest camera intent"`.

### Task 3: Evidence that a short recording was finalized

**Files:** Create `src/oc_remote/recording_evidence.py`, `tests/test_recording_evidence.py`. Modify `src/oc_remote/camera.py`, `tests/test_camera.py`.

**Interfaces:** `async snapshot(adb, folder: str) -> dict[str, VideoEntry]` reads the configured Open Camera folder without UI dump; `async finalized_since(adb, folder: str, baseline: dict[str, VideoEntry], deadline: float) -> bool` requires a new or changed MP4 that has positive size and the same size on two reads 0.5 seconds apart. `CameraController` keeps the latest baseline from session startup and refreshes it after verified STOP. A missing baseline or unstable video yields uncertain, never success.

- [ ] **Step 1: Write failing tests.** Fake two catalog reads with an unchanged old file: false. Fake a new file whose size grows between reads: wait and require two stable reads before true. Fake a missing baseline: false. In the controller test, submit START then STOP quickly with final IDLE dump but no new finalized video; assert one failure tone and UNKNOWN.

```python
baseline = {"old.mp4": VideoEntry("old.mp4", 10, 1.0)}
assert not await finalized_since(adb_with_only_old_video, FOLDER, baseline, deadline=1.0)
```

- [ ] **Step 2: Run red.** `uv run pytest tests/test_recording_evidence.py tests/test_camera.py -q`; expect missing module/function and a false success tone in rapid STOP.
- [ ] **Step 3: Implement baseline and finalization.** Use `catalog.list_videos()` at session startup and after verified STOP, not on the key dispatch path. Track the baseline for each START generation. A STOP whose pending burst includes START requires changed-file evidence; a STOP from already confirmed RECORDING also checks stabilization. Respect the deadline and never infer success from IDLE alone.

```python
candidate = next((entry for entry in await list_videos(adb, folder)
                  if entry.size > 0 and baseline.get(entry.name) != entry), None)
await asyncio.sleep(0.5)
stable = next((entry for entry in await list_videos(adb, folder)
               if candidate and entry.name == candidate.name and entry.size == candidate.size), None)
return stable is not None
```

- [ ] **Step 4: Run green.** `uv run pytest tests/test_recording_evidence.py tests/test_camera.py -q` and `uv run pytest -q`.
- [ ] **Step 5: Commit.** `git add src/oc_remote/recording_evidence.py src/oc_remote/camera.py tests/test_recording_evidence.py tests/test_camera.py; git commit -m "feat: verify finalized video after rapid stop"`.

### Task 4: Immediate browser actions and status contract

**Files:** Modify `src/oc_remote/server.py`, `src/oc_remote/web/app.js`, `tests/test_server.py`, `tests/test_web_contract.py`.

**Interfaces:** `POST /api/camera` returns HTTP 202 plus current `CameraStatus` JSON including predicted `state`, `confirmed_state`, `busy`, `generation`, and `message`. `GET /api/status` returns the same shape. File-mutation endpoints require `confirmed_state == idle` and no pending camera generation. The browser applies the predicted action locally before awaiting POST, serializes POST requests in acceptance order, and reconciles replies by generation.

- [ ] **Step 1: Write failing tests.** A server test posts START then STOP while the first dump is held and expects two 202 responses plus predicted `idle`. A browser test uses a delayed first POST, clicks the primary button twice, and asserts request bodies `start`, `stop`, immediate button names, no click tone, and unchanged focused element. A delayed older status response must not roll the label back. Use agent-browser against a local fake server for the browser test.

```python
first = await client.post("/api/camera", json={"action": "start"}, headers=auth(client))
second = await client.post("/api/camera", json={"action": "stop"}, headers=auth(client))
assert [first.status, second.status] == [202, 202]
assert (await second.json())["state"] == "idle"
```

- [ ] **Step 2: Run red.** `uv run pytest tests/test_server.py tests/test_web_contract.py -q` and the agent-browser delayed-response check; expect 409 on the second command or two `start` requests.
- [ ] **Step 3: Implement.** Keep `aria-disabled` only for verification off, UNKNOWN, invalid transition, or queue-full conditions; `busy` alone does not disable camera buttons. Update the primary/pause names synchronously on user click and show a plain pending text. Chain fetch POSTs so request order matches clicks. Ignore status payloads older than the latest accepted generation; on rejection refresh from the server and show the error. Do not add `aria-live` or force focus.

```javascript
const action = current.state === "idle" ? "start" : "stop";
applyPredictedAction(action);
cameraRequests = cameraRequests.then(() => postCamera(action));
```

- [ ] **Step 4: Run green.** `uv run pytest tests/test_server.py tests/test_web_contract.py -q`, full suite, and agent-browser snapshot/error check in Arabic and English.
- [ ] **Step 5: Commit.** `git add src/oc_remote/server.py src/oc_remote/web/app.js tests/test_server.py tests/test_web_contract.py; git commit -m "feat: keep camera controls responsive during verification"`.

### Task 5: Camera priority during old-video operations

**Files:** Modify `src/oc_remote/server.py`, `tests/test_server.py`, `tests/test_files.py`.

**Interfaces:** Existing file-operation lock still serializes copy, move, rename, and delete. `POST /api/camera` and manual verification do not wait for that lock. `POST /api/rename` and `POST /api/delete` require confirmed IDLE with no pending camera intent at acceptance; an already accepted file operation keeps its captured `VideoEntry` even if filming starts later.

- [ ] **Step 1: Write failing concurrency tests.** Hold `copy_many()` or `delete_one()` on an event after it captures `old.mp4`; post START and assert 202 and key dispatch before releasing the file event. A simultaneous second file mutation must conflict or wait without acting on a new video. A selected file changed between selection and deletion still raises uncertain and remains on the phone.

```python
copy_response = await client.post("/api/copy", json=copy_payload, headers=auth(client))
await copy_started.wait()
camera_response = await client.post("/api/camera", json={"action": "start"}, headers=auth(client))
assert camera_response.status == 202
await first_key.wait()  # copy is still held
```

- [ ] **Step 2: Run red.** `uv run pytest tests/test_server.py tests/test_files.py -q`; expect HTTP 409 from the current camera/file lock.
- [ ] **Step 3: Implement the independence.** Remove the file-lock rejection from camera submission and verification. Keep one lock for concurrent file operations. Recheck confirmed camera state and pending generation immediately before accepting each new phone mutation; do not cancel a mutation already operating on a captured stable old file merely because filming starts.
- [ ] **Step 4: Run green.** `uv run pytest tests/test_server.py tests/test_files.py -q`, then full suite.
- [ ] **Step 5: Commit.** `git add src/oc_remote/server.py tests/test_server.py tests/test_files.py; git commit -m "feat: prioritize recording during old-video work"`.

### Task 6: Truthful asynchronous delete progress

**Files:** Modify `src/oc_remote/files.py`, `src/oc_remote/server.py`, `src/oc_remote/web/app.js`, `src/oc_remote/web/index.html`, `tests/test_files.py`, `tests/test_server.py`, `tests/device/test_media_index.py`.

**Interfaces:** `async remote_exists(adb: AdbClient, path: str) -> bool` uses a targeted shell `find`: an empty successful result means absent, while an ADB failure remains uncertain. `async delete_one(adb: AdbClient, entry: VideoEntry, phone_folder: str, confirmed_name: str, progress: Callable[[str], None] | None = None) -> None` emits `checking`, `deleting`, `verifying`, `verified` or `uncertain`. `POST /api/delete` retains exact-name confirmation but returns 202 and an operation id immediately; `GET /api/file-operation` returns `{id, kind, stage, running, outcome, message}` without exposing a filename in diagnostics. The page changes its focused confirmation button label and result text immediately, polls stages, and plays no click tone.

- [ ] **Step 1: Write failing tests.** Hold fake ADB at the delete command: POST must return 202 promptly with `stage == deleting`; a second delete conflicts. On release, require absence from targeted filesystem path and MediaStore row before `verified` and one success tone. Make the MediaStore check fail: `uncertain` and one failure tone. A device test deletes only its own random MP4 and confirms both postconditions.

```python
response = await client.post("/api/delete", json={"name": name, "confirmed_name": name}, headers=auth(client))
assert response.status == 202
assert (await (await client.get("/api/file-operation")).json())["running"]
```

- [ ] **Step 2: Run red.** `uv run pytest tests/test_files.py tests/test_server.py -q`; expect synchronous 200 response and no progress stages.
- [ ] **Step 3: Implement the job.** Keep the selected `VideoEntry` and exact name immutable in the background task. Emit `checking` before precheck, `deleting` before the MediaStore or shell removal, and `verifying` before two targeted postchecks. Replace redundant full-folder listing after deletion with a shell check of the exact path and `query_media_row()` for the same name; retain uncertainty on any failed check. Keep the mutation lock until final outcome and tone. Immediately set browser text to “Deleting and checking” before fetch; map every stage in Arabic and English without synthetic percentage or `aria-live`.

```python
progress("deleting")
if row is not None:
    await adb.run("shell", "content", "delete", "--uri", f"content://media/external/video/media/{row.row_id}")
else:
    await adb.run("shell", "rm", "-f", shlex.quote(path))
progress("verifying")
if await remote_exists(adb, path) or await query_media_row(adb, folder, name):
    raise UncertainMutation("Deletion could not be verified")
progress("verified")
```

- [ ] **Step 4: Run green and phone gate.** `uv run pytest tests/test_files.py tests/test_server.py -q`; with `OC_DEVICE_TEST=1` and the exact paired serial, run `uv run pytest tests/device/test_media_index.py -q -s`. Ensure cleanup touches only random test names. Then run full suite.
- [ ] **Step 5: Commit.** `git add src/oc_remote/files.py src/oc_remote/server.py src/oc_remote/web/app.js src/oc_remote/web/index.html tests/test_files.py tests/test_server.py tests/device/test_media_index.py; git commit -m "feat: show verified delete stages"`.

### Task 7: Select all and accessible file feedback

**Files:** Modify `src/oc_remote/web/index.html`, `src/oc_remote/web/app.js`, `tests/test_web_contract.py`, `docs/acceptance-ar.md`, `docs/acceptance-en.md`.

**Interfaces:** One native `<button id="selectAll">` toggles all checkboxes in the currently loaded video list and changes between localized “Select all” and “Clear selection”. It updates copy/move/rename/delete availability without moving focus. A failed/uncertain move explicitly says the PC copy is verified but phone removal is uncertain.

- [ ] **Step 1: Write failing browser checks.** In an agent-browser session with three fake videos, click Select all; expect three checked boxes, enabled Copy, disabled single-video mutations, changed button name, and focus still on Select all. Click again; expect zero checked. Switch languages and repeat. Run `uv run pytest tests/test_web_contract.py -q` for the basic native-control contract.

```javascript
const boxes = [...document.querySelectorAll('#videos input[type="checkbox"]')];
if (boxes.length !== 3 || boxes.some(box => !box.checked)) throw Error('select all failed');
```

- [ ] **Step 2: Confirm red.** Run the browser check before editing; expect the Select all button to be absent.
- [ ] **Step 3: Implement the native button and localized feedback.** Toggle only current visible entries, recompute its label when manual checkbox selections change or a folder refresh replaces the list, and preserve focus. Keep `aria-disabled` rather than removing camera or file buttons. Update acceptance guides with the exact keyboard path using NVDA `B` and `X`.
- [ ] **Step 4: Run green.** Run the browser check in Arabic and English, browser console errors, `uv run pytest tests/test_web_contract.py -q`, and the full suite.
- [ ] **Step 5: Commit.** `git add src/oc_remote/web/index.html src/oc_remote/web/app.js tests/test_web_contract.py docs/acceptance-ar.md docs/acceptance-en.md; git commit -m "feat: select all videos with native controls"`.

### Task 8: Phone timing, NVDA acceptance, and release gate

**Files:** Create `tests/device/test_rapid_controls.py`. Modify `docs/device-test-notes.md`, `docs/acceptance-ar.md`, `docs/acceptance-en.md`; modify affected implementation only for observed failures.

**Interfaces:** No new public API. This gate proves rapid START → STOP, one final tone, completed MP4, camera command priority during an old-video file job, delete progress, and NVDA browse-mode focus on the user's device. It provides evidence for resuming Task 10 of the original plan, then Tasks 11–12 (package and public release).

- [ ] **Step 1: Write the opt-in device test and acceptance checklist.** The test verifies Open Camera starts IDLE, sends START then STOP without awaiting a UI dump between keys, records both key completion times and final verification time, and checks a new stable video. It leaves the recorded video on the phone for user review. File-job concurrency uses only a random test-created video. The checklist asks the user to try immediate stop, select all, and delete progress with NVDA; it does not delete personal media.

```python
start_task = controller.submit(CameraAction.START)
stop_task = controller.submit(CameraAction.STOP)
await controller.wait_until_settled()
assert adb_key_stop_completed_at < final_dump_completed_at
assert controller.status().confirmed_state is CaptureState.IDLE
```

- [ ] **Step 2: Run red against the pre-change behavior.** The earlier phone timing and user report are the failure evidence: ordinary START verification took about 3–4 seconds total, and the second command was disabled until then. The new test must assert that the second key completes before final verification; run `uv run pytest tests/device/test_rapid_controls.py -q -s` with the opt-in environment after confirming the phone is ready.
- [ ] **Step 3: Complete device and NVDA checks.** Run `uv run pytest -q`, `uv run python -m compileall -q src`, the opt-in rapid-control and media-index gates, then a live browser session. Record timing and result without recording private video names in diagnostics. Ask the user for NVDA feedback on rapid control, delete progress, and playback of the USB-C microphone audio; fix observed failures and rerun only affected checks plus the full suite.
- [ ] **Step 4: Update docs and review.** Write actual tested phone, Android/Open Camera/Windows/NVDA versions when known and timing in `docs/device-test-notes.md`; mark any untested configuration as untested. Inspect `git diff --check` and sanitized diagnostics for names, XML, and video bytes. Do self-review because the user prohibited agents, then follow `verification-before-completion`.
- [ ] **Step 5: Commit and return to original plan.** `git add tests/device/test_rapid_controls.py docs/device-test-notes.md docs/acceptance-ar.md docs/acceptance-en.md; git commit -m "test: accept rapid accessible filming workflow"`. Mark this plan complete with `task-done`; resume the original plan's Task 10 completion and then Tasks 11–12.
