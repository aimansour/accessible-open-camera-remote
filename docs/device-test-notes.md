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

The early cycles did not check the USB-C microphone audio or file
finalization timing. Later rapid-control results are recorded below.

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

## Media index rename and delete check

With the user's approval, an opt-in test created a one-second black MP4 with a
random `oc_remote_index_test_` name in `/sdcard/DCIM/OpenCamera`. Android's
video MediaStore indexed it. The test renamed that file and confirmed the old
name was absent and the new name was present in both the filesystem and
MediaStore. It then deleted the same file and confirmed absence from both.
Finally it cleaned up only the two random names it had created. The passing
device gate took about 16 seconds.

On this Android 16 build, `content update` returned empty stdout despite
performing the rename. The implementation therefore uses the two independent
postcondition checks instead of relying on a particular command message.
The browser demonstration exposed the selected-video actions and an inline
confirmation with the exact filename. Clicking Delete kept focus on that
button, and the browser reported no console errors. It did not send a delete
request to the phone; that server path is covered by automated API tests.

## Responsive workflow gate on the same phone

On 2026-09-23, Samsung SM-A155F with Android 16 and Open Camera 1.56.2 was
still in the foreground with TalkBack manually off. Windows 10 Pro and an
installed NVDA 2026.1.1 were present. The new opt-in rapid-control test ran
three times. It sent Start, waited 0.7 seconds after the first key command finished,
then accepted Stop without waiting for the first UI dump. It left the new
recordings on the phone for review. All three runs ended in confirmed idle with one
result tone and a new positive-size, stable MP4. Times are measured from the
Start submission:

| Run | Both key commands completed | Final UI dump completed | Final video verified |
| --- | ---: | ---: | ---: |
| 1 | 3.287 s | 7.936 s | 8.798 s |
| 2 | 3.634 s | 8.339 s | 9.271 s |
| 3 | 3.386 s | 8.099 s | 8.994 s |

The second key completed before the final UI dump in each run. A separate
phone test held the copy of a random test-created old video, sent both camera
keys during that hold, then released and verified the PC copy. It removed only
its own random test source. The media-index device gate also passed again:
its random test video was renamed and deleted, and targeted filesystem and
MediaStore checks both showed absence after deletion.

With the rebuilt service and a live browser page, two clicks 0.7 seconds
apart changed the focused button name immediately from Start to Stop and back.
The final API status was confirmed idle with generation 2; browser errors were
empty and the local diagnostics recorded one `camera_verified` outcome for
the burst. Fake-video browser checks in Arabic and English covered Select all,
manual checkbox changes, and the checking/deleting/verifying text. The real
delete API was exercised only on a random test-created phone file, not on a
personal video.

The user previously confirmed ordinary NVDA browse navigation and stable
button position on the earlier page. The updated rapid-button and delete
progress interactions have browser focus and accessibility-tree evidence,
but have not yet been heard with NVDA by the user. USB-C microphone audio has
not been listened to or attributed to that microphone. These two sensory
checks remain for the user's acceptance session; the automated phone and
browser checks do not establish them.
