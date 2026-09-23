# Catalog synchronization and measured transfers implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. The user explicitly requested that the current agent do the work without subagents.

**Goal:** Show finalized recordings automatically, remove verified moved videos immediately, and use measured concurrency for copy and move.

**Architecture:** Keep the local HTML page and native controls. Add a transfer job kind and incremental per-file results. Reconcile the browser catalog from confirmed camera and transfer state with stable DOM nodes and stale-response protection.

**Tech Stack:** Python 3.14, aiohttp, ADB over Wi-Fi, plain HTML/CSS/JavaScript, pytest, agent-browser.

**Spec:** `docs/superpowers/specs/2026-09-24-catalog-sync-and-transfer-speed-design.md`

## Global constraints

- Do not push, tag, create a release, or otherwise publish until the user says all changes and their platform test are finished.
- Work in the current repository; do not create a worktree or dispatch subagents.
- Preserve NVDA browse navigation and native controls, with no synthetic speech, focus trap, intercepted arrows, or action-click tone.
- Never modify a personal video during tests; only random test-created names may be moved or deleted.
- Recording commands remain independent of file jobs. One outcome tone per completed batch.

## Review focus

- A recorded clip is verified before the catalog request: the resulting entry appears without reload and the request is made only once for a settled camera generation.
- A copy result must leave its phone source visible; a verified move must remove it; an uncertain move must remain explicit and require deliberate reselection.
- A stale catalog response started before a move or delete must never reinsert a verified removed item.
- A focused checkbox for a different video must keep its node and selection through catalog refresh.
- Camera submission during a four-worker move must proceed before the move batch finishes, even if ADB command latency rises under load.

---

### Task 1: Incremental transfer job contract

**Files:** `src/oc_remote/server.py`, `src/oc_remote/transfer.py`, `tests/test_server.py`, `tests/test_transfer.py`.

**Interfaces:** Transfer jobs returned by `/api/transfers` include `kind` (`copy` or `move`), `stages`, `results`, `completed`, `total`, `running`; `copy_many(..., on_result=None, max_workers=2)` returns results in input order and calls `on_result(result)` at completion of each file.

- [ ] Write a failing server test: hold one copied file while another completes and assert `/api/transfers` reports `kind: copy`, one result and `completed: 1` before the batch ends. Assert one tone only after all finish.
- [ ] Run the focused test and confirm it fails for the missing incremental result and kind.
- [ ] Implement the minimal contract in `post_copy`; preserve failure outcomes and the file lock.
- [ ] Run focused tests, then `uv run pytest -q`; confirm all pass before moving on.
- [ ] Commit the task locally; do not push.

### Task 2: Bounded concurrent transfers

**Files:** `src/oc_remote/transfer.py`, `src/oc_remote/server.py`, `tests/test_transfer.py`, `tests/test_server.py`.

**Interfaces:** `copy_many` runs at most two `copy_one` calls concurrently, returns results in request order, and reports each completion. `post_move` runs at most four `move_one` calls concurrently, tracks independent outcomes, and retains one final tone.

- [ ] Write failing event-controlled tests: two copies enter together while a third waits; four moves enter together while a fifth waits. Release one worker and assert only one waiting item starts. Assert partial results and final aggregate outcomes.
- [ ] Run each focused test to see the expected sequential behavior fail.
- [ ] Implement bounded worker pools without weakening per-file size, SHA-256, filesystem, or MediaStore checks. Keep camera submissions outside the file lock.
- [ ] Run focused tests and the whole suite; verify the camera-during-transfer test still passes.
- [ ] Commit the task locally; do not push.

### Task 3: Catalog reconciliation in the browser

**Files:** `src/oc_remote/web/app.js`, `tests/test_web_contract.py` only where a meaningful stable accessibility contract is needed.

**Interfaces:** A confirmed camera transition to settled idle calls `refreshVideos` once. A verified result in a `kind: move` job removes the matching phone row and selection immediately; a verified `kind: copy` does not. `renderVideos` reuses unchanged checkbox/label nodes. Existing stale-response revision protection covers moves and deletes.

- [ ] Reproduce the current failures in agent-browser with synthetic responses: zero catalog requests on confirmed stop; moved video and controls remain after verified move. Record the red results.
- [ ] Add the smallest state reconciliation functions and transfer-kind handling. Clear selection of nonverified move results at job completion. Update action visibility immediately.
- [ ] In agent-browser, test automatic stop refresh, move versus copy, stale listing, retained checkbox focus/selection, Arabic and English, and no console errors. Compare against the red reproductions.
- [ ] Run `node --check src/oc_remote/web/app.js` and `uv run pytest -q`.
- [ ] Commit the task locally; do not push.

### Task 4: Device and packaged acceptance

**Files:** `tests/device/test_batch_files.py`, `docs/device-test-notes.md`, installation/acceptance documents only as needed.

**Interfaces:** Device tests create uniquely named MP4s, check the copied PC bytes, and inspect phone-file and MediaStore results. The built Windows executable serves the updated page; no public release artifact is created.

- [ ] Extend the opt-in test to exercise multiple copy and move files and camera submission during an active move. Keep all destructive actions limited to test names.
- [ ] Run the device gate, full suite, Windows build, package suite, and agent-browser visual/accessibility checks. Record measured transfer times and ADB preflight latency.
- [ ] Review the whole diff for focus, stale responses, uncertain outcomes, and accidental personal-file operations. Correct any important finding with a new red-green test.
- [ ] Leave the work as local commits and a local test build for the user's NVDA acceptance. Do not publish.
