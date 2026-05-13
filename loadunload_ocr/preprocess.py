from __future__ import annotations

from dataclasses import dataclass, field
from io import BytesIO
from typing import Any

try:
    import cv2
except Exception:  # pragma: no cover - optional dependency guard
    cv2 = None

try:
    import numpy as np
except Exception:  # pragma: no cover - optional dependency guard
    np = None

try:
    from PIL import Image, ImageOps, ImageFilter
except Exception:  # pragma: no cover - optional dependency guard
    Image = None
    ImageOps = None
    ImageFilter = None


@dataclass(slots=True)
class PreparedShortSheetImage:
    original_image: Any
    ocr_ready_image: Any
    width: int
    height: int
    mode: str | None
    rotation_degrees: int | None = None
    notes: list[str] = field(default_factory=list)


def load_short_sheet_image(upload_bytes: bytes) -> PreparedShortSheetImage:
    if Image is None:
        raise RuntimeError("Pillow is required to load uploaded images.")
    if not upload_bytes:
        raise ValueError("No image bytes were provided.")

    image_obj = Image.open(BytesIO(upload_bytes))
    if ImageOps is not None:
        image_obj = ImageOps.exif_transpose(image_obj)
    if str(image_obj.mode or "").upper() != "RGB":
        image_obj = image_obj.convert("RGB")

    notes: list[str] = ["Loaded with Pillow", "Applied EXIF orientation if available"]
    ocr_ready_image = image_obj

    if cv2 is not None and np is not None:
        try:
            rgb_array = np.array(image_obj)
            gray_array = cv2.cvtColor(rgb_array, cv2.COLOR_RGB2GRAY)
            denoised = cv2.GaussianBlur(gray_array, (3, 3), 0)
            thresholded = cv2.adaptiveThreshold(
                denoised,
                255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY,
                31,
                11,
            )
            ocr_ready_image = Image.fromarray(thresholded)
            notes.append("Applied OpenCV grayscale + adaptive threshold")
        except Exception:
            notes.append("OpenCV preprocessing skipped after load failure")
    else:
        try:
            if ImageOps is not None:
                ocr_ready_image = ImageOps.autocontrast(image_obj)
                notes.append("Applied Pillow autocontrast fallback")
        except Exception:
            notes.append("Pillow fallback preprocessing skipped")

    return PreparedShortSheetImage(
        original_image=image_obj,
        ocr_ready_image=ocr_ready_image,
        width=int(getattr(image_obj, "width", 0)),
        height=int(getattr(image_obj, "height", 0)),
        mode=str(getattr(image_obj, "mode", "")) or None,
        rotation_degrees=0,
        notes=notes,
    )
