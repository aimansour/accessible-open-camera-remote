# Accessible Open Camera Remote v0.1.3

Download `OpenCameraRemote-v0.1.3.zip`, extract the whole `OpenCameraRemote` folder, and run `OpenCameraRemote.exe`. Keep the bundled `adb` folder beside the executable. Follow the [Arabic installation guide](https://github.com/aimansour/accessible-open-camera-remote/blob/main/docs/install-ar.md) or [English installation guide](https://github.com/aimansour/accessible-open-camera-remote/blob/main/docs/install-en.md).

SHA-256 of the ZIP: `5252C882391F1C822E32831EB446505FA786CBF3104C1189D1D4A495E336986E`.

## Changes

- New recordings appear automatically after verified Stop. Verified moves and deletes remove their video rows; copies leave phone videos visible.
- Batch copy and move use measured concurrent workers. Camera keys remain responsive during file transfers.
- A changed phone folder clears the old selection, and file actions check the selected video's name, size, and modified time before changing it.
- Camera verification ignores stale results from older commands and stops pending manual checks when verification is switched off. File changes cannot be mistaken for a new recording.
- A verified completed video can still be copied while camera verification is off. Uncertain moves no longer claim a PC copy unless a destination was verified.
- The default ADB pull deadline is one hour instead of five minutes.

## Verification and limits

The Windows package was built locally and its suite reported 144 passed, 5 skipped. The optional Samsung SM-A155F / Android 16 phone gate passed with random test videos: three deleted, four copied and moved, with SHA-256, phone-file, and MediaStore checks. A short camera recording was started and stopped during the move. No personal phone video was changed by that gate.

The user confirmed that NVDA works correctly with this release. USB-C microphone audio was confirmed in an earlier session. Other phones, save folders, and Open Camera versions remain unverified. If a camera or file result is uncertain, inspect it before acting again; toggle keys are not retried automatically.
