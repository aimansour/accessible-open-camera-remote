# Accessible Open Camera Remote v0.1.0

First Windows release of the local Arabic and English control page for Open
Camera. Download `OpenCameraRemote.zip`, extract the whole folder, pair Android
wireless ADB, turn TalkBack off manually for the remote filming session, and
run `OpenCameraRemote.exe`. Python is not required to run the packaged app.

`OpenCameraRemote.zip` SHA-256:
`0E1990FEE639CB642CD310289283670722C19DB8FAA6F41435614C7A166EBD12`.

Installation: [English](https://github.com/aimansour/accessible-open-camera-remote/blob/main/docs/install-en.md)
· [العربية](https://github.com/aimansour/accessible-open-camera-remote/blob/main/docs/install-ar.md)

## Included

- Native browser buttons and checkboxes for NVDA browse navigation; Arabic
  and English labels; no captured arrow keys, screen stream, click tone, or
  automatic TalkBack change.
- Ordered recording controls. Start, stop, pause, and resume update button
  names immediately; one result tone follows verification of the final
  action. A short recording is accepted only after a stable MP4 is found.
- Verified copy and batch copy with size and SHA-256 checks, move after a
  verified copy, guarded rename, and asynchronous delete with truthful stages.
- Recording controls continue while a previously selected old video is
  being copied. Phone file mutations require a confirmed idle camera state.
- A bundled ADB 37.0.1 with its complete official `NOTICE.txt`, plus bundled
  Python and dependency license texts.

## Tested scope

Tested on Windows 10 Pro, Samsung SM-A155F, Android 16, Open Camera 1.56.2,
and wireless ADB 37.0.1. The Windows executable opened the local page and
completed a rapid Start → Stop cycle on the phone. Three opt-in phone tests
passed in the final gated run: short recording, camera commands during an old
file copy, and Android MediaStore rename/delete on a random test-created file.
The normal suite passed 129 tests with 5 optional checks skipped; the built
package check passed all 4 distribution tests. A prior user check confirmed
ordinary NVDA browse navigation and stable button position on the earlier
page; browser checks covered focus and names for the new controls.

## Known limits

- Updated rapid-button and delete-stage speech has not yet been heard by the
  user with NVDA. USB-C microphone audio has not been listened to. These are
  human acceptance checks, not claims made from automated tests.
- The verified recording folder is `/sdcard/DCIM/OpenCamera`. Other Open
  Camera save folders, phone models, Android versions, and Open Camera
  versions are unverified.
- ADB wireless debugging must remain paired and connected. An uncertain
  camera result requires a fresh state verification; toggle keys are never
  retried automatically.

The app is independent of Open Camera and Google. Original code is MIT
licensed; Android Platform Tools and bundled dependencies retain their own
notices in the release directory.
