"""Short Windows result tones, sent off the event loop."""

import threading
import winsound


class ToneSink:
    def __init__(self, sound=None):
        self._sound = sound or winsound

    def _play(self, frequency: int, duration: int) -> None:
        threading.Thread(
            target=self._sound.Beep,
            args=(frequency, duration),
            daemon=True,
        ).start()

    def success(self) -> None:
        self._play(880, 120)

    def failure(self) -> None:
        self._play(330, 220)
