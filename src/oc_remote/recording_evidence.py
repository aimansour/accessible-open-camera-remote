"""Check that Open Camera finished writing a video without reading its bytes."""

import asyncio

from .catalog import VideoEntry, list_videos


async def snapshot(adb, folder: str) -> dict[str, VideoEntry]:
    return {entry.name: entry for entry in await list_videos(adb, folder)}


async def finalized_since(
    adb, folder: str, baseline: dict[str, VideoEntry] | None, deadline: float,
) -> bool:
    """Require a changed video with positive, stable size before the time budget ends."""
    if baseline is None:
        return False
    loop = asyncio.get_running_loop()
    end = loop.time() + deadline
    seen: dict[str, tuple[VideoEntry, float]] = {}
    async with asyncio.timeout(deadline):
        while True:
            current = await snapshot(adb, folder)
            now = loop.time()
            candidates = (
                entry for entry in current.values()
                if entry.name.lower().endswith(".mp4") and entry.size > 0
                and baseline.get(entry.name) != entry
            )
            next_seen: dict[str, tuple[VideoEntry, float]] = {}
            for entry in candidates:
                previous = seen.get(entry.name)
                if previous is not None and previous[0] == entry:
                    if now - previous[1] >= 0.5:
                        return True
                    next_seen[entry.name] = previous
                else:
                    next_seen[entry.name] = (entry, now)
            seen = next_seen
            if end - now < 0.5:
                return False
            await asyncio.sleep(0.5)
