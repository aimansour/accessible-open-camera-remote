from pathlib import Path

import pytest

from oc_remote.catalog import (
    InvalidListing, InvalidVideoName, VideoEntry, list_videos, parse_listing,
    validate_folder, validate_name,
)


def test_newline_and_arabic_filename_round_trips():
    raw = "فيديو\nأول.mp4\0" + "1024\0" + "1700000000.0\0"
    assert parse_listing(raw.encode("utf-8"))[0].name == "فيديو\nأول.mp4"


def test_listing_sorts_newest_and_ignores_photos():
    raw = b"old.mp4\x001\x0010\x00photo.jpg\x003\x0020\x00new.mkv\x002\x0030\x00"
    assert [entry.name for entry in parse_listing(raw)] == ["new.mkv", "old.mp4"]


@pytest.mark.parametrize("name", ["", ".", "..", "../a.mp4", "a/b.mp4", "a\\b.mp4", "photo.jpg", ".mp4"])
def test_unsafe_or_nonvideo_names_are_rejected(name):
    with pytest.raises(InvalidVideoName):
        validate_name(name)


@pytest.mark.parametrize("raw", [b"a.mp4\x001\x002", b"a.mp4\x001\x00oops\x00", b"a.mp4\x00-1\x002\x00", b"\xff.mp4\x001\x002\x00"])
def test_malformed_listing_is_rejected(raw):
    with pytest.raises(InvalidListing):
        parse_listing(raw)


def test_shell_punctuation_is_data_not_a_command():
    assert validate_name("clip; $(touch nope) 'test'.mp4") == "clip; $(touch nope) 'test'.mp4"


@pytest.mark.parametrize("folder", ["/sdcard/../data", "/data/local/tmp", "/sdcard", "/sdcard/DCIM/..", "/sdcard/DCIM\nevil"])
def test_folder_must_be_bounded_shared_storage(folder):
    with pytest.raises(ValueError):
        validate_folder(folder)


async def test_listing_uses_selected_adb_transport_and_quotes_folder():
    class FakeAdb:
        async def run(self, *args, **kwargs):
            self.args = args
            return b"clip.mp4\x001024\x001700000000.0\x00"

    adb = FakeAdb()
    entries = await list_videos(adb, "/sdcard/DCIM/Open Camera")
    assert entries == [VideoEntry("clip.mp4", 1024, 1700000000.0)]
    assert adb.args[:3] == ("shell", "toybox", "find")
    assert "'/sdcard/DCIM/Open Camera'" in adb.args
