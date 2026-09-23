# Windows and phone acceptance check

These steps cover the tested Samsung SM-A155F, Android 16, and Open Camera
1.56.2 on the same Wi-Fi network as Windows with wireless ADB. Other phones
need their own device check. Use only short disposable videos for move and
delete checks.

## Setup

1. Connect the microphone to the phone and the headset and keyboard to the
   PC. Put the phone on its stand, unlock it, and open Open Camera in video
   mode.
2. Turn TalkBack off manually for the remote filming session. Keep Open
   Camera in the foreground while verification or camera control runs.
3. Confirm the phone appears as `device` in `adb devices`. Start the program
   using the README command, then open its printed `http://127.0.0.1` address
   in your usual browser.
4. Use ordinary NVDA browse mode: `H` for headings, `B` for buttons, and
   `X` for checkboxes. The page does not require custom arrow navigation.

## Recording and verification

1. Read “Ready to record.” Press “Start recording.” The button becomes
   “Stop recording” immediately and can be pressed again for a short clip.
   One tone follows verification of the final state and completed video;
   pressing a button alone makes no tone.
2. Press “Pause,” then “Resume.” Check the button names and recording state
   after each result tone. A click alone does not play a tone.
3. Press “Stop recording” and wait for the result tone. Show videos and find
   the new file. Play it on the phone or PC and listen for the USB-C microphone
   audio. Recording state alone cannot confirm sound quality.
4. Press “Stop verification.” Camera controls stay in place but become
   unavailable. Use the phone manually and turn TalkBack on if needed. To
   return, open Open Camera in video mode, turn TalkBack off manually, and
   press “Start verification.” Wait for a fresh confirmed state.
5. While copying an older disposable video, press “Start recording.” The
   button name must change immediately and recording must begin before the
   copy finishes. Check the copy and recording outcomes in their sections.

## Files and recovery

1. Copy one disposable video to a PC folder. Wait for “Verified copy” and
   the success tone. Play the PC file and confirm the phone source remains.
2. Select several disposable videos and use “Copy selected.” Check each
   result in the list.
3. Rename a disposable video using “New name without extension.” Confirm
   `.mp4` remains and the renamed video appears in the phone gallery.
4. Move a different disposable video. Its phone source may be removed only
   after PC size and SHA-256 match. Check PC presence and phone absence.
5. In NVDA browse mode, use `B` to reach “Select all” and press it. Use `X`
   to visit the checkboxes and check that every visible video is selected.
   The button becomes “Clear selection” and keeps the reading position.
   Press it again to clear, or change individual boxes. Group copy remains
   available; single-video actions are unavailable for multiple selections.
6. For a disposable video intended for deletion, press “Delete video.” Read
   the exact full filename in the inline confirmation. Try Cancel first and
   confirm it stays; then confirm deletion. The confirmation button becomes
   “Deleting and checking” immediately. Read the checking, deleting, and
   verifying stages; a result tone follows the filesystem and MediaStore
   postchecks.
7. If ADB disconnects after a command, expect an unknown camera state or an
   uncertain file result. Do not repeat a camera key. Reconnect and start
   verification for a fresh state. Never treat a partial copy as verified.

## Record results

Record Windows, NVDA, Android, and Open Camera versions, phone model, each
step's result, and approximate button-to-result-tone timing. Local diagnostics
are in `%LOCALAPPDATA%\OpenCameraRemote\diagnostics.jsonl`; they contain no
video names, screen dumps, or video bytes.
