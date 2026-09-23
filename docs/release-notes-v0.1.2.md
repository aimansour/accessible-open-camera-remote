# Accessible Open Camera Remote v0.1.2

Download `OpenCameraRemote-v0.1.2.zip` and extract the whole folder. Keep
`adb` and the other files beside `OpenCameraRemote.exe`; Python is not needed.
The phone and PC must be on the same Wi-Fi with wireless ADB paired. Follow the
[Arabic installation guide](https://github.com/aimansour/accessible-open-camera-remote/blob/main/docs/install-ar.md)
or [English guide](https://github.com/aimansour/accessible-open-camera-remote/blob/main/docs/install-en.md).

SHA-256: `A5E6BAFD6BBAAD654378179CE44D948F836913D593C45585B4D2794CFBF355F2`.

## Changes

- Each video disappears from the list as soon as its phone file and Android
  media index deletion are verified. An uncertain result remains visible for
  inspection.
- An inline progress bar shows the percentage of files whose deletion checks
  have finished, plus verified and uncertain counts. It does not estimate
  bytes or time remaining. The result list updates without replacing every
  item on each poll, and the page does not interrupt NVDA with announcements.
- Group deletion runs at most two files concurrently. A direct two-file phone
  probe took 8.300 seconds sequentially and 4.134 seconds concurrently. One
  result tone still plays after the whole group finishes.
- Older list responses can no longer reinsert a video already verified deleted.

## Verification and limits

The Windows package suite passed 135 tests; five opt-in device checks were
skipped in that run. An opt-in test on Samsung SM-A155F, Android 16, Open
Camera 1.56.2, and ADB 37.0.1 created five random small MP4s. It deleted
three in a group and moved two, checking phone files and MediaStore afterward.
No personal recording was touched by that test. The packaged executable
opened its local browser page, and browser probes checked 50% progress,
immediate removal, uncertain-item retention, a stale-list response, and both
languages without browser errors.

The updated progress view has not yet been evaluated by the user with NVDA.
Other save folders, phone models, and Open Camera versions remain untested.
If a file result is uncertain, inspect it on the phone before acting on it
again. The app does not automatically retry camera toggle keys.
