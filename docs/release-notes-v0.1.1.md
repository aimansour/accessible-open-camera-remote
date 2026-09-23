# Accessible Open Camera Remote v0.1.1

Download `OpenCameraRemote-v0.1.1.zip` and extract the whole folder. Keep its
`adb` and other files beside `OpenCameraRemote.exe`; Python is not required.
The phone and PC must be on the same Wi-Fi with wireless ADB paired. Follow the
[Arabic installation guide](https://github.com/aimansour/accessible-open-camera-remote/blob/main/docs/install-ar.md)
or [English guide](https://github.com/aimansour/accessible-open-camera-remote/blob/main/docs/install-en.md).

SHA-256: `3062A6BFEEBB3B0B722F9FE320AC7BF1E5A6310ED8F2C6A0119744DBC54C8CD1`.

## Changes

- **Select all** now offers copy, move, and delete for the selected group.
  Rename appears only when exactly one video is selected. Actions that cannot
  be used are hidden from the page and NVDA browse navigation.
- Group deletion requires an inline confirmation listing every exact full
  name, then shows a stage and final outcome for each video. One result tone
  plays after the whole group finishes. Each phone file and Android MediaStore
  row is checked before deletion is marked verified.
- Group move copies and checks each selected video before removing its phone
  original. A failed item has its own result; other selected items continue.
- The user reported that NVDA interaction and USB-C microphone audio worked
  in their filming session.

## Verification and limits

The Windows suite passed 133 tests with 6 opt-in checks skipped. With the
built package present, 134 passed and 5 device checks were skipped. An opt-in
test on Samsung SM-A155F, Android 16, Open Camera 1.56.2, and ADB 37.0.1
created four random small MP4s: batch delete removed two, batch move copied
and removed two, and each phone filesystem and MediaStore postcondition passed.
The built executable opened the local page; browser checks found no page errors
and showed the expected hidden and visible actions in Arabic and English.
No personal video was moved or deleted during these checks.

Recording finalization is verified in `/sdcard/DCIM/OpenCamera`. Other save
folders, phone models, Android versions, and Open Camera versions remain
untested. If a file result is uncertain, inspect phone and PC before acting
on that file again. The app does not automatically retry camera toggle keys.
