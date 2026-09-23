import asyncio

import pytest

from oc_remote.catalog import VideoEntry
from oc_remote.recording_evidence import finalized_since, snapshot


FOLDER = "/sdcard/DCIM/OpenCamera"


class CatalogAdb:
    def __init__(self, listings):
        self.listings = list(listings)
        self.reads = 0

    async def run(self, *args, **kwargs):
        self.reads += 1
        return self.listings.pop(0) if len(self.listings) > 1 else self.listings[0]


def listing(name, size, modified=1.0):
    return f"{name}\0{size}\0{modified}\0".encode()


async def test_unchanged_old_video_is_not_finalization_evidence():
    old = VideoEntry("old.mp4", 10, 1.0)
    adb = CatalogAdb([listing("old.mp4", 10)])
    assert not await finalized_since(adb, FOLDER, {old.name: old}, 0.05)


async def test_new_video_must_have_two_stable_positive_size_reads():
    adb = CatalogAdb([
        listing("new.mp4", 10), listing("new.mp4", 20),
        listing("new.mp4", 20),
    ])
    assert await finalized_since(adb, FOLDER, {}, 1.2)
    assert adb.reads >= 3


async def test_missing_baseline_is_not_evidence():
    adb = CatalogAdb([listing("new.mp4", 20)])
    assert not await finalized_since(adb, FOLDER, None, 0.05)


async def test_snapshot_uses_catalog_names_and_metadata():
    adb = CatalogAdb([listing("new.mp4", 20)])
    assert await snapshot(adb, FOLDER) == {"new.mp4": VideoEntry("new.mp4", 20, 1.0)}


async def test_stable_new_video_is_found_among_other_changing_videos():
    def pair(growing_size):
        return listing("zzz-growing.mp4", growing_size, 2.0) + listing("aaa-stable.mp4", 30, 2.0)

    adb = CatalogAdb([pair(10), pair(20)])
    assert await finalized_since(adb, FOLDER, {}, 0.8)


async def test_finalization_deadline_interrupts_hung_catalog_read():
    class HungAdb:
        async def run(self, *args, **kwargs):
            await asyncio.Event().wait()

    started = asyncio.get_running_loop().time()
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(finalized_since(HungAdb(), FOLDER, {}, 0.05), 0.2)
    assert asyncio.get_running_loop().time() - started < 0.15
