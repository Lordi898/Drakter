"""Screen and hands of the floating mode (docs/floating/CONTRACT.md §5, §8.2 and §9.2).

The backend reaches the desktop only through the helper `hands/helper/main.py` (`client.py`) and the OCR
process `hands/ocr` (`ocr.py`). Everything that comes from the screen is untrusted data.
"""
