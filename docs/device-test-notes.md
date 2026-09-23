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
microphone audio, NVDA behavior in the browser, behavior with TalkBack on,
and file finalization timing. Those require later acceptance checks.
