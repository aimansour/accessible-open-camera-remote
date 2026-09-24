# Whole-repository review remediation implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. The user directed the current agent to implement personally, in the current repository.

**Goal:** Fix every substantiated Critical and Important finding in the whole-repository review and align both READMEs.

**Architecture:** Preserve the local Python/aiohttp service and native browser UI. Bind browser selections and jobs to source file identity, make camera verification generation-safe, reconcile evidence after phone mutations, and express transfer outcomes truthfully.

**Tech Stack:** Python 3.14, aiohttp, Android Debug Bridge, plain HTML/CSS/JavaScript, pytest, agent-browser, PyInstaller.

**Spec:** `docs/superpowers/specs/2026-09-24-whole-repository-review-remediation-design.md`

## Global constraints

- Work in the current repository and implement without subagents. Reviewers may be used only when the execution skill requires a final review.
- Preserve NVDA browse navigation, native controls, and one tone only after final camera or file verification.
- Never mutate a personal phone video in tests. Do not publish until the user personally tests the local platform.
- Camera submission stays independent of file jobs.

## Review focus

- Changing the folder text after selection cannot mutate a same-named file in another folder.
- A newer Start cannot be settled by an older Stop's final awaited baseline refresh.
- Rename or fixture files cannot stand in for a newly recorded clip.
- Stopping verification during a manual dump leaves no pending reader or later state write.
- An uncertain move cannot claim a verified PC copy without a destination.

---

### Task 1: Bind catalog selections to folder and file identity

**Files:** `src/oc_remote/web/app.js`, `src/oc_remote/server.py`, `tests/test_server.py`, executable browser probe under `tests/browser/`.

**Interfaces:** Browser tracks `currentVideosFolder`; browser requests include `expected_entries` with name, size and modified; mutation endpoints compare those against freshly listed entries when supplied; job status includes `folder`.

- [ ] Reproduce the folder-switch request mismatch in the browser and a stale-entry mutation in a server test. Confirm RED.
- [ ] Implement browser catalog invalidation on folder input, bound job reconciliation, and server identity comparison before any change.
- [ ] Run focused browser/API checks, `node --check`, and the full pytest suite; commit locally.

### Task 2: Settle only the current camera generation

**Files:** `src/oc_remote/camera.py`, `tests/test_camera.py`.

**Interfaces:** Every Stop await is followed by a current-generation and enabled check before committing state or tone.

- [ ] Write an event-controlled test that submits Start during Stop's final snapshot and observes the old false idle result. Confirm RED.
- [ ] Recheck generation after that snapshot; rerun focused and full tests; commit locally.

### Task 3: Stop manual verification completely

**Files:** `src/oc_remote/camera.py`, `tests/test_camera.py`, `tests/test_server.py` if needed.

**Interfaces:** A manual verification request is serialized and cancellation-safe; Stop verification awaits its cancellation.

- [ ] Write an event-controlled test holding the manual dump, stop verification, release the dump, and assert no later ADB read or idle write. Confirm RED.
- [ ] Implement lifecycle ownership and serialize overlapping manual checks; rerun focused and full tests; commit locally.

### Task 4: Reconcile recording evidence after file changes

**Files:** `src/oc_remote/camera.py`, `src/oc_remote/server.py`, `tests/test_camera.py`, `tests/test_server.py`, `tests/device/test_batch_files.py`.

**Interfaces:** Camera baseline receives verified catalog/file changes in its default recording folder without blocking camera submission; failure yields uncertain finalization.

- [ ] Write a failing integration test where rename alone falsely satisfies Start → Stop, and one for added fixtures. Confirm RED.
- [ ] Reconcile the baseline at mutation boundaries and correct device-test setup; rerun focused, full, and opt-in phone gates; commit locally.

### Task 5: Copy availability and truthful move outcome

**Files:** `src/oc_remote/web/app.js`, `src/oc_remote/server.py`, `tests/test_server.py`, browser probe.

**Interfaces:** The browser exposes Copy for verified completed catalog rows while verification is off; move results distinguish a verified PC destination from an entirely uncertain result.

- [ ] Reproduce hidden Copy and the false uncertain-move claim in browser probes; create a server exception result test. Confirm RED.
- [ ] Apply minimal UI and result-contract changes; run focused/browser/full checks; commit locally.

### Task 6: Large-transfer timeout and documentation

**Files:** `src/oc_remote/adb.py`, `tests/test_adb.py`, `README.md`, `README.ar.md`, install docs if needed.

**Interfaces:** `AdbClient.pull` uses a transfer-appropriate configurable deadline; timeout still cleans partial output through `copy_one`.

- [ ] Add a deterministic test proving pull does not use the old 300-second cap; confirm RED.
- [ ] Implement the deadline, align both READMEs, run focused and full suites; commit locally.

### Task 7: Real device and local package acceptance

**Files:** `docs/device-test-notes.md` and tests only if a gate exposes a defect.

- [ ] Run relevant opt-in phone gate using random test files, full pytest, JS syntax, and whitespace checks.
- [ ] Rebuild Windows locally, verify package assets and browser controls, and run a final whole-repository review.
- [ ] Leave commits and build local for the user's NVDA acceptance; do not publish.
