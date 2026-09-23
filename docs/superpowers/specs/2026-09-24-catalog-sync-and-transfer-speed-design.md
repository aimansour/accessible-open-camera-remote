# Automatic video catalog updates and measured transfers

Date: 2026-09-24. This extends the approved Open Camera Remote design. The
user requested implementation and testing in the current repository, with no
further public release until all changes have been reviewed and tested.

## Observed defects and intended result

After a recording is stopped and its file has been verified, the new video
must appear in the browser list without reloading the page or pressing Show
videos. A verified move must remove that video's checkbox and label as soon as
the server confirms both PC copy and phone deletion. Actions for a removed
video must disappear. A failed or uncertain move must remain explicit in the
results and must not be presented as verified.

The current page reproduces both defects: it sends no catalog request after
an accepted recording status changes to confirmed idle, and it leaves a moved
video selected with Move and Delete visible after the transfer ends. The
server has no `kind` field on transfer jobs, so a verified copy and a verified
move look identical to the page. The current `renderVideos` also replaces all
checkboxes on every refresh, which can disturb NVDA browse position.

## Technology decision

Keep the local HTML, CSS and JavaScript interface. Native buttons,
checkboxes, labels and progress elements are supported browser features and
already give the intended NVDA browse behavior. The failure is in when and
how application state is synchronized, not in a missing framework feature.
Consolidate catalog reconciliation into focused functions in the existing
page rather than adding a framework or rebuilding the UI.

## Camera and catalog flow

On the first page load, read the phone catalog once. After an accepted camera
status transitions from busy/recording/paused to confirmed idle with no work
pending, request the catalog once more. The camera controller already verifies
that the finalized MP4 has a stable positive size before reporting success;
the page must wait for that result before asking for the new list. Repeated
status polls for the same settled result must not trigger repeated catalog
reads. If the read fails, show an error and leave the prior list available;
the Show videos button remains a manual retry.

Catalog rendering reuses each unchanged checkbox and its label node, retains
selection and browser focus where possible, adds newly recorded items, and
removes only entries absent from an authoritative refresh or explicitly
verified as removed. A request started before a verified removal may not
restore that item when it returns late.

## Copy and move flow

Every transfer job includes `kind: copy` or `kind: move`. Only a verified
**move** removes a phone video from the list. A verified copy keeps it there.
Job results arrive per file, so progress and catalog changes appear while a
batch is still running. Final tone behavior stays one tone per batch.
Uncertain moves remain in the result list for inspection; on completion their
selection is cleared, making any retry a deliberate new selection.

The Windows destination uses a unique partial file per copy. Each worker
checks the phone file's size and modification time before and after transfer,
checks SHA-256 on both devices, and publishes the PC file only after matching.
Move deletes a phone original only after this verified copy, then checks both
the phone path and Android MediaStore. Different files may be processed
concurrently; each file's checks stay independent.

## Measured concurrency choice

The same Samsung SM-A155F on wireless ADB copied four valid 8.44 MB test MP4s
in 8.32/7.90 seconds sequentially, 5.51/5.87 seconds with two workers, and
5.32/5.42 seconds with four. Two workers capture most of the speed gain for
copying; four gave little additional benefit and a larger ADB command latency
in a concurrent preflight probe. Use **two** copy workers.

Four other test MP4s moved in 22.85 seconds sequentially, 14.70 seconds with
two workers, and 10.52 seconds with four. A second run with a simultaneous
ADB preflight probe took 22.09/13.98/9.85 seconds respectively; probe latency
varied from 0.44 to 1.36 seconds for moves. Use **four** move workers, and
test that camera commands are still submitted before the move batch finishes.
Do not extrapolate these measurements to other phones or network conditions.

## Validation and boundaries

First create failing tests for the browser's missing refresh and stale move
selection, and for bounded copy/move concurrency and per-file results. Run
the full suite. Exercise the built Windows app in a browser with synthetic
catalog and job responses, then run an opt-in phone test that touches only
randomly named videos created by that test. Preserve NVDA browse behavior:
no focus trap, synthetic announcements, arrow interception, or extra tones.
The user will test the changed page with NVDA before any public release.
