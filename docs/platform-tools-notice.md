# Android Platform Tools notice

The Windows build copies `adb.exe`, `AdbWinApi.dll`, and `AdbWinUsbApi.dll`
from an installed official Android SDK Platform Tools directory. It also
copies that directory's unmodified `NOTICE.txt` and `source.properties` into
the release's `adb` folder. The tested directory reports version 37.0.1.
No ADB binary is committed to this Git repository.

Google's [Platform Tools release page](https://developer.android.com/tools/releases/platform-tools)
provides the official downloads. Google's [SDK terms](https://developer.android.com/studio/terms)
restrict redistribution of the SDK generally and state that open-source
components follow their own open-source licenses. The [ADB source build
metadata](https://android.googlesource.com/platform/packages/modules/adb/+/refs/heads/main/Android.bp)
identifies the ADB module as Apache-2.0, and the Windows USB API source is
also [Apache-2.0](https://android.googlesource.com/platform/development/+/refs/heads/main/host/windows/usb/api/adb_winusb_api.h).
The release includes the complete official `NOTICE.txt` so recipients get
the component attributions and license texts shipped with the binaries.

Open Camera itself is not redistributed. Android, Google, and Open Camera
names identify compatible software; they do not imply sponsorship.
