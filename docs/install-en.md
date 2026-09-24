# Windows installation and keyboard use

## Requirements

- Windows PC and Android phone on the same Wi-Fi network. The tested setup is
  Windows 10 Pro, Samsung SM-A155F, Android 16, and Open Camera 1.56.2.
- [Open Camera](https://opencamera.org.uk/) installed and set to video mode.
  Configure volume up to start/stop recording and volume down to pause/resume.
- Wireless debugging in Android Developer options. Pair the phone with ADB.
  The phone's USB-C port can remain connected to the microphone.
- The release directory extracted in full. Do not move the executable away
  from its `adb`, `oc_remote`, and other companion files.

## Pair wireless ADB

1. On the phone, enable Developer options and Wireless debugging. Pair using
   the Android pairing code. On the PC, use the bundled `adb\adb.exe` from a
   terminal, or an existing Android Platform Tools installation:
   `adb pair PHONE_IP:PAIRING_PORT`. Enter the code shown by Android.
2. Use the connection address and port shown on the Wireless debugging page:
   `adb connect PHONE_IP:CONNECT_PORT`. The pairing port and connection port
   can differ. `adb devices` must show the phone as `device`. Android may also
   discover a previously paired phone automatically.
3. If more than one device is listed, run the program with `--serial` and the
   exact serial from `adb devices`. Wireless debugging addresses can change
   after a network or phone restart; reconnect if needed.

The software talks to the phone through ADB. The browser page itself is local
to the PC. No remote browser service or internet account is used.

## Start a recording session

1. Connect the USB-C microphone to the phone and the headset and keyboard to
   the PC. Put the unlocked phone on its stand with Open Camera in video mode.
2. Turn TalkBack off manually for the remote session. Open Camera must remain
   in the foreground while state verification runs. The program does not
   change TalkBack.
3. Run `OpenCameraRemote.exe`. It opens its page in the default browser and
   prints the local `http://127.0.0.1` address in the console. Keep the
   program running while using the page.
4. In NVDA browse mode, use `H` for headings, `B` for buttons, and `X` for
   checkboxes. Press Enter or Space on a button. A recording button changes
   name immediately after a click. A tone comes only after checking the final
   result; two quick actions produce one final result tone.
5. Before touching the phone manually, press **Stop verification** in the
   page. Camera buttons disappear. When returning, put Open Camera
   in video mode, turn TalkBack off manually, and press **Start verification**.

Use **Select all** for the currently shown videos, or choose individual
checkboxes. Copy, move, and delete work on all selected videos; rename appears
only for one. Actions that cannot be used are hidden. Copy publishes a PC file
only after size and SHA-256 match. Move removes the phone source only after a
verified copy. Delete confirms every full name and shows each file's stage.
Changing the phone-folder field clears the previous selection; refresh the
list before choosing files in the new folder. A previously verified completed
video can still be copied while verification is off.
During deletion, the progress bar shows the percentage of files checked and
the number verified deleted. Each verified video disappears from the list;
uncertain files remain for inspection. This is file count progress, not bytes.

## Recovery

If the result is uncertain, do not press the same camera key blindly: it is
a toggle. Check the phone, reconnect ADB if necessary, then start verification
to read its actual state. A partial PC copy is removed automatically and is
never presented as verified. If a move says the copy is verified but phone
removal is uncertain, inspect both devices before another move.
The default ADB pull deadline is 60 minutes. A failed or timed-out pull does
not publish a partial PC file.

The program assumes Open Camera writes recording files in
`/sdcard/DCIM/OpenCamera` for finalization evidence. The file-list field can
show another shared-storage folder, but recording finalization in that folder
is not yet supported. See [the tested checklist](acceptance-en.md).

## Updates, privacy, and notices

The service listens only on `127.0.0.1`. Diagnostics are local at
`%LOCALAPPDATA%\OpenCameraRemote\diagnostics.jsonl` and omit video names,
screen XML, and video bytes. The package contains ADB 37.0.1 and its complete
`NOTICE.txt` in `adb`. See [platform-tools-notice.md](platform-tools-notice.md)
and the release's other license files. Open Camera is not bundled.
