"""Opt-in Android media index gate using only files created by this test."""

import asyncio
import os
import shlex
import shutil
import subprocess
import time
from pathlib import Path
from uuid import uuid4

import pytest

from oc_remote.adb import AdbClient
from oc_remote.catalog import DEFAULT_PHONE_FOLDER, list_videos
from oc_remote.files import delete_one, media_path, query_media_row, rename_one


@pytest.mark.skipif(os.getenv("OC_DEVICE_TEST") != "1", reason="device test is opt-in")
async def test_rename_and_delete_update_android_media_index(tmp_path):
    serial = os.getenv("OC_DEVICE_SERIAL")
    if not serial:
        pytest.fail("Set OC_DEVICE_SERIAL to the exact connected ADB serial")
    adb_exe = shutil.which("adb")
    ffmpeg = shutil.which("ffmpeg")
    if not adb_exe or not ffmpeg:
        pytest.fail("ADB and ffmpeg are required for this gated test")
    adb = AdbClient(serial, Path(adb_exe))
    marker = f"oc_remote_index_test_{uuid4().hex}"
    original_name = marker + ".mp4"
    renamed_name = marker + "_renamed.mp4"
    local = tmp_path / original_name
    subprocess.run([ffmpeg, "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
                    "color=c=black:s=32x32:d=1", "-c:v", "mpeg4", "-t", "1", "-y", str(local)],
                   check=True, capture_output=True, timeout=30)
    assert local.stat().st_size > 0
    remote = f"{DEFAULT_PHONE_FOLDER}/{original_name}"

    async def scan(name):
        uri = "file://" + media_path(DEFAULT_PHONE_FOLDER, name)
        await adb.run("shell", "am", "broadcast", "-a", "android.intent.action.MEDIA_SCANNER_SCAN_FILE",
                      "-d", shlex.quote(uri), timeout=10)

    try:
        await adb.run("push", str(local), remote, timeout=30)
        await scan(original_name)
        for _ in range(10):
            if await query_media_row(adb, DEFAULT_PHONE_FOLDER, original_name) is not None:
                break
            await asyncio.sleep(0.5)
        else:
            pytest.fail("Android did not index the test video after a scan request")

        original = next(item for item in await list_videos(adb, DEFAULT_PHONE_FOLDER)
                        if item.name == original_name)
        renamed = await rename_one(adb, original, DEFAULT_PHONE_FOLDER, marker + "_renamed")
        assert renamed.name == renamed_name
        assert await query_media_row(adb, DEFAULT_PHONE_FOLDER, original_name) is None
        assert await query_media_row(adb, DEFAULT_PHONE_FOLDER, renamed_name) is not None
        print("Test video rename exists in both filesystem and MediaStore")

        await delete_one(adb, renamed, DEFAULT_PHONE_FOLDER, renamed_name)
        assert await query_media_row(adb, DEFAULT_PHONE_FOLDER, renamed_name) is None
        assert all(item.name != renamed_name for item in await list_videos(adb, DEFAULT_PHONE_FOLDER))
        print("Test video deletion is absent from both filesystem and MediaStore")
    finally:
        # Only the two random names created by this test may be cleaned up.
        for name in (original_name, renamed_name):
            await adb.run("shell", "rm", "-f", shlex.quote(f"{DEFAULT_PHONE_FOLDER}/{name}"), timeout=10)
            await scan(name)
