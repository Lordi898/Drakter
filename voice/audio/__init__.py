"""Audio I/O of the voice process: capture, sink and queued player. Stdlib + numpy only."""

from voice.audio.backends import open_capture, open_sink
from voice.audio.null import NullCapture, NullSink
from voice.audio.player import Player

__all__ = ["NullCapture", "NullSink", "Player", "open_capture", "open_sink"]
