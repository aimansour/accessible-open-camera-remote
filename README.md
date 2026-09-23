# Accessible Open Camera Remote

[Public repository](https://github.com/aimansour/accessible-open-camera-remote)
· [Download Windows v0.1.2](https://github.com/aimansour/accessible-open-camera-remote/releases/tag/v0.1.2)

A local Windows browser control for [Open Camera](https://opencamera.org.uk/) on
Android. It is designed for ordinary NVDA browse mode: native buttons and
checkboxes, Arabic and English labels, no captured keyboard arrows, no screen
stream, and one PC tone after the final result is checked. It uses wireless
Android Debug Bridge (ADB); it does not install a phone app or change TalkBack.

## What it does

- Start, stop, pause, and resume recording with the Open Camera volume-key
  shortcuts. Button names change when an action is accepted, so a short clip
  can be stopped before the first screen check finishes.
- Verify the latest recording state. After Stop, require a new or changed MP4
  with a positive size stable across two reads before reporting success.
- List phone videos, select one or all, copy with size and SHA-256 checks, move
  after a verified copy, and delete selected videos with a result for each.
  Deletion uses two concurrent file workers. The page shows the percentage of
  files checked and removes each video after its deletion is verified.
  Rename appears for one selected video. Unavailable actions are hidden.
- Run recording controls while a copy of an older selected video is in
  progress. File mutations require a confirmed idle camera state.

## Install and use

Read [Windows installation](docs/install-en.md) or [التثبيت بالعربية](docs/install-ar.md).
The release directory contains `OpenCameraRemote.exe` and ADB; no Python is
needed to run it. Keep the whole directory together. Run the executable while
your phone and PC are on the same Wi-Fi and wireless ADB is paired. It opens a
page on `127.0.0.1` in your usual browser. With NVDA browse mode, use `H` for
headings, `B` for buttons, and `X` for checkboxes.

Open Camera must be in video mode with its volume-up shortcut set to start or
stop and volume-down set to pause or resume. Turn TalkBack off manually while
the program checks the phone screen. Use the page's **Stop verification**
button before using the phone yourself; recording buttons then disappear
until a fresh verification. The program never toggles TalkBack.

The exact Windows and phone checklist is in [acceptance-en.md](docs/acceptance-en.md)
or [acceptance-ar.md](docs/acceptance-ar.md).

## Safety and privacy

The service binds only to the PC loopback address and requires a per-session
token for changing actions. It does not stream or save the phone screen.
Diagnostics store event codes, elapsed time, ADB status, and phone model; they
do not store filenames, screen XML, or video contents. They are local at
`%LOCALAPPDATA%\OpenCameraRemote\diagnostics.jsonl`.

Copy uses a temporary PC file and publishes it only after size and SHA-256
match. Move deletes the phone original only after the copy is verified. Delete
requires confirming the exact full names of all selected files. Uncertain
results do not retry a camera key or claim a successful file mutation.

## Tested scope and current limits

The device workflow was exercised on Windows 10 Pro, Samsung SM-A155F,
Android 16, Open Camera 1.56.2, and ADB 37.0.1. Browser focus and button names
were checked in Arabic and English. The user reported that NVDA interaction
and USB-C microphone sound worked in their session. Batch delete and move
were tested on five disposable files created by the latest device test. Other
phones, Open Camera versions, and nondefault recording folders are unverified.
Recording finalization currently checks `/sdcard/DCIM/OpenCamera`.

See [device-test-notes.md](docs/device-test-notes.md) for measurements and
unverified items. This project is independent of Open Camera and Google.

## Contribute and build

Install Python 3.14, [uv](https://docs.astral.sh/uv/), and Android Platform
Tools. Run `uv sync`, then `uv run pytest -q`. The opt-in phone tests are under
`tests/device` and require `OC_DEVICE_TEST=1` and the exact `OC_DEVICE_SERIAL`.
Build on Windows with `powershell -File tools/build-windows.ps1`. The script
copies the official ADB binaries and their complete `NOTICE.txt` into the
ignored release directory; binaries are not committed to Git.

Original project code is [MIT licensed](LICENSE). Android Platform Tools and
other bundled components retain their own terms; see the notice files in the
release and [platform-tools-notice.md](docs/platform-tools-notice.md).
