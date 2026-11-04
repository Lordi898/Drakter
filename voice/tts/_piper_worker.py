"""Piper worker. Runs ONLY in a separate process under config.piper_python (Piper is GPL).

Never imported by the voice process. Protocol, all binary on stdin/stdout:
  in : one JSON line per request {"text": str, "length_scale": float}
  out: frames <uint32 LE n><n bytes int16 mono PCM>; n == 0 ends the request.
       A line with {"error": ...} is not used: failures end the process (non-zero exit).
"""

import json
import struct
import sys


def main() -> None:
    model, config = sys.argv[1], sys.argv[2]
    from piper import PiperVoice, SynthesisConfig

    voice = PiperVoice.load(model, config_path=config)
    out = sys.stdout.buffer
    out.write(struct.pack("<I", 0))  # ready marker
    out.flush()
    for line in sys.stdin.buffer:
        req = json.loads(line)
        cfg = SynthesisConfig(length_scale=float(req["length_scale"]))
        for chunk in voice.synthesize(req["text"], cfg):
            data = chunk.audio_int16_bytes
            out.write(struct.pack("<I", len(data)) + data)
            out.flush()
        out.write(struct.pack("<I", 0))
        out.flush()


if __name__ == "__main__":
    main()
