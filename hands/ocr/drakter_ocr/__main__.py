"""`python -I -m drakter_ocr`: one request per process (docs/floating/CONTRACT.md §5).

Reads `OcrRequest` JSON from stdin, writes `OcrResult` JSON to stdout. Models come from
`~/.local/share/drakter/models/ocr/` and nothing is downloaded at run time. Never logs recognised text.
`--install-models` (used only by `hands/ocr/install.sh`) fetches them once and copies them there.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import time
from pathlib import Path

MODEL_DIR = Path.home() / ".local" / "share" / "drakter" / "models" / "ocr"
DET = "ch_PP-OCRv5_det_mobile.onnx"
REC = "latin_PP-OCRv5_rec_mobile.onnx"
CLS = "ch_ppocr_mobile_v2.0_cls_mobile.onnx"
MODEL = "rapidocr-3.10.0 PP-OCRv5 mobile latin"
MAX_BOXES = 2000


def _engine(threads: int, *, local: bool = True):
    from rapidocr import LangRec, ModelType, OCRVersion, RapidOCR

    params = {
        "Global.log_level": "critical",
        "Rec.lang_type": LangRec.LATIN, "Rec.model_type": ModelType.MOBILE, "Rec.ocr_version": OCRVersion.PPOCRV5,
        "Det.model_type": ModelType.MOBILE, "Det.ocr_version": OCRVersion.PPOCRV5,
        "EngineConfig.onnxruntime.intra_op_num_threads": threads,
        "EngineConfig.onnxruntime.inter_op_num_threads": 1,
    }
    if local:
        for key, name in (("Det", DET), ("Rec", REC), ("Cls", CLS)):
            path = MODEL_DIR / name
            if not path.is_file():
                raise FileNotFoundError(name)
            params[f"{key}.model_path"] = str(path)
    return RapidOCR(params=params)


_BASE = "https://www.modelscope.cn/models/RapidAI/RapidOCR/resolve/v3.10.0/onnx"
# URL and SHA256 pinned from rapidocr 3.10.0 `default_models.yaml`.
PINNED = {
    DET: (f"{_BASE}/PP-OCRv5/det/{DET}", "4d97c44a20d30a81aad087d6a396b08f786c4635742afc391f6621f5c6ae78ae"),
    REC: (f"{_BASE}/PP-OCRv5/rec/{REC}", "b20bd37c168a570f583afbc8cd7925603890efbcdc000a59e22c269d160b5f5a"),
    CLS: (f"{_BASE}/PP-OCRv4/cls/{CLS}", "e47acedf663230f8863ff1ab0e64dd2d82b838fceb5957146dab185a89d6215c"),
}


def _sha256(path: Path) -> str:
    import hashlib

    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def install_models() -> int:
    """Download the three models once (or copy them from `DRAKTER_OCR_MODELS_FROM`), checking SHA256."""
    import urllib.request

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    os.chmod(MODEL_DIR, 0o700)
    local = os.environ.get("DRAKTER_OCR_MODELS_FROM")
    for name, (url, digest) in PINNED.items():
        dest = MODEL_DIR / name
        if dest.is_file() and _sha256(dest) == digest:
            continue
        tmp = dest.with_suffix(".part")
        if local and (Path(local) / name).is_file():
            shutil.copyfile(Path(local) / name, tmp)
        else:
            with urllib.request.urlopen(url, timeout=60) as resp, open(tmp, "wb") as out:  # noqa: S310 - pinned https
                shutil.copyfileobj(resp, out)
        if _sha256(tmp) != digest:
            tmp.unlink()
            print(f"SHA256 distinto en {name}", file=sys.stderr)
            return 1
        os.replace(tmp, dest)
    print(json.dumps({"models": str(MODEL_DIR)}))
    return 0


def _fail(msg: str, t0: float) -> int:
    print(json.dumps({"boxes": [], "ms": int((time.perf_counter() - t0) * 1000), "model": MODEL, "error": msg}))
    return 0


def main() -> int:
    if sys.argv[1:] == ["--install-models"]:
        return install_models()
    t0 = time.perf_counter()
    try:
        req = json.loads(sys.stdin.read(65536))
        image = str(req["image"])
        region = req.get("region")
        threads = max(1, min(8, int(req.get("threads", 4))))
        if req.get("lang", "latin") != "latin" or not os.path.isabs(image):
            return _fail("bad_request", t0)
    except (ValueError, KeyError, TypeError):
        return _fail("bad_request", t0)
    try:
        import cv2

        img = cv2.imread(image, cv2.IMREAD_COLOR)
        if img is None:
            return _fail("unreadable_image", t0)
        ox = oy = 0
        if region:
            x, y, w, h = (max(0, int(v)) for v in region)
            img = img[y : y + h, x : x + w]
            ox, oy = x, y
            if img.size == 0:
                return _fail("empty_region", t0)
        engine = _engine(threads)
        result = engine(img)
    except FileNotFoundError:
        return _fail("models_missing", t0)
    except Exception as exc:  # noqa: BLE001 - the backend gets a clean error, never a traceback
        return _fail(type(exc).__name__, t0)
    boxes = []
    if result.boxes is not None:
        for box, txt, score in zip(result.boxes, result.txts, result.scores):
            xs, ys = box[:, 0], box[:, 1]
            x0, y0 = int(xs.min()) + ox, int(ys.min()) + oy
            boxes.append({"text": str(txt)[:500], "score": round(min(1.0, max(0.0, float(score))), 3),
                          "rect": [x0, y0, int(xs.max()) + ox - x0, int(ys.max()) + oy - y0]})
            if len(boxes) >= MAX_BOXES:
                break
    print(json.dumps({"boxes": boxes, "ms": int((time.perf_counter() - t0) * 1000), "model": MODEL},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
