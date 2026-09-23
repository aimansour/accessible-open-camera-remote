import threading

from oc_remote.audio import ToneSink


class FakeWinsound:
    def __init__(self):
        self.calls = []
        self.called = threading.Event()

    def Beep(self, frequency, duration):
        self.calls.append((frequency, duration))
        self.called.set()


def test_tone_only_when_explicit_result_method_is_called():
    sound = FakeWinsound()
    tones = ToneSink(sound)
    assert sound.calls == []
    tones.success()
    assert sound.called.wait(1)
    assert sound.calls == [(880, 120)]
    sound.called.clear()
    tones.failure()
    assert sound.called.wait(1)
    assert sound.calls == [(880, 120), (330, 220)]
