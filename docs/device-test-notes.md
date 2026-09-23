# Samsung Galaxy A15 feasibility notes

Date: 2026-09-23. Phone reported ready by the user with TalkBack manually off,
Open Camera in video mode, screen unlocked, and USB-C microphone connected.
Wireless ADB serial was explicitly selected. The test produced two short videos
and left them on the phone for inspection. It did not delete or rename a file.

Tested: Samsung SM-A155F, Android 16, Open Camera 1.56.2, ADB 37.0.1, Windows
10. Both complete recording cycles passed: idle → recording → paused →
recording → idle. UI descriptions observed were:

| State | Capture button | Pause button |
| --- | --- | --- |
| Idle | `Start recording video` | absent |
| Recording | `Stop recording video` | `Pause video recording` |
| Paused | `Stop recording video` | `Resume video recording` |

Second cycle timing (seconds):

| Action | Before key command | ADB key command | Key completion to verified state | Total |
| --- | ---: | ---: | ---: | ---: |
| Start | 0.335 | 1.087 | 2.632 | 4.055 |
| Pause | 0.244 | 0.392 | 2.564 | 3.200 |
| Resume | 0.229 | 0.299 | 2.555 | 3.083 |
| Stop | 0.421 | 1.014 | 2.552 | 3.988 |

The key-command time measures completion of the ADB `input keyevent` process,
not the exact physical instant Open Camera reacted. The initial state dump
took 2.597 seconds. The app sent the key before waiting for the slow UI dump.
The recording test's extra evidence dump is outside the totals above.

Not yet checked: whether the resulting videos contain the intended USB-C
microphone audio, behavior with TalkBack on, and file finalization timing.
Those require later acceptance checks.

## Browser and NVDA check

The local demonstration page was checked in Chromium accessibility snapshots:
one level-1 heading, two level-2 headings, a native language select, and
native recording and verification buttons were exposed. Arabic and English
names appeared correctly. Browser checks found content, no error overlay, and
no console errors. After clicking the verification button, it retained focus.
The user confirmed that NVDA browse-mode navigation and button position worked
normally in their browser. This was a demonstration page with a fake camera
controller, so it did not test result tones or a real phone command through
the browser; those remain for the complete workflow acceptance.

## Verified copy check

The newest video in the configured Open Camera folder was copied to
`Videos/OpenCameraRemote/verification-2026-09-23` on the PC. Its source size
was 6,209,577 bytes. `copy_one` reported verified after comparing local and
phone size and SHA-256, and the destination file existed. The phone source was
not removed. A separate browser demonstration used an Arabic-named fake video
and showed one verified result in a native list; focus stayed on the Copy
button, and the browser reported no console errors. This does not yet prove
NVDA announces transfer progress in the user's preferred way; the page does
not use automatic announcements.
