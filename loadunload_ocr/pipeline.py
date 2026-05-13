from __future__ import annotations

import io
import re
import time
from typing import Iterable

from .models import (
    ShortSheetCellValue,
    ShortSheetHeader,
    ShortSheetIssue,
    ShortSheetLineItem,
    ShortSheetResult,
    ShortSheetTemplate,
    TruckSlot,
)
from .preprocess import load_short_sheet_image

try:
    from PIL import Image
except Exception:  # pragma: no cover - optional dependency guard
    Image = None

try:
    import pytesseract
except Exception:  # pragma: no cover - optional dependency guard
    pytesseract = None

try:
    from pytesseract import Output as TesseractOutput
except Exception:  # pragma: no cover - optional dependency guard
    TesseractOutput = None


SCHEMA_VERSION = 1
PROCESSOR_VERSION = "0.1.0"
TRUCK_SHORTAGE_TEMPLATE_ID = "truck_shortage_load_v1"
UNLOAD_BATCHING_TEMPLATE_ID = "unload_batching_sheet_v1"
MANUAL_SHORT_SHEET_TEMPLATE_ID = TRUCK_SHORTAGE_TEMPLATE_ID


MANUAL_SHORT_SHEET_LINE_ITEMS: list[ShortSheetLineItem] = [
    ShortSheetLineItem("3X10", "3X10_ONYX", "3X10 ONYX"),
    ShortSheetLineItem("3X10", "3X10_COPPER", "3X10 COPPER"),
    ShortSheetLineItem("3X10", "3X10_INDIGO", "3X10 INDIGO"),
    ShortSheetLineItem("3X10", "3X10_BLACK", "3X10 BLACK"),
    ShortSheetLineItem("APRONS", "BLACK_APRON_X2873", "BLACK APRON - x2873"),
    ShortSheetLineItem("APRONS", "WHITE_APRON_X2864", "WHITE APRON - x2864"),
    ShortSheetLineItem("APRONS", "RED_APRON_X2861", "RED APRON - x2861"),
    ShortSheetLineItem("TOWELS", "REG_TOWELS_X2720", "REG TOWELS - x2720"),
    ShortSheetLineItem("TOWELS", "PREM_TOWELS_X5857", "PREM TOWELS - x5857"),
    ShortSheetLineItem("TOWELS", "GLASS_TOWELS_X2964", "GLASS TOWELS - x2964"),
    ShortSheetLineItem("MICRO", "MICRO_BLUE_X7432", "MICRO BLUE - x7432"),
    ShortSheetLineItem("MICRO", "MICRO_ORANGE_X7433", "MICRO ORANGE - x7433"),
    ShortSheetLineItem("MICRO", "MICRO_GREY_X7540", "MICRO GREY - x7540"),
    ShortSheetLineItem("MICRO", "MICRO_WHITE_X7717", "MICRO WHITE - x7717"),
    ShortSheetLineItem("MOPS", "GRID_TOWELS_X1936", "GRID TOWELS - x1936"),
    ShortSheetLineItem("MOPS", "WET_MOP_X6913", "WET MOP - x6913"),
    ShortSheetLineItem("MOPS", "MICRO_TUBE_MOP_X8020", "MICRO TUBE MOP - x8020"),
    ShortSheetLineItem("MOPS", "BLUE_MOP_20_X7000", "20\" BLUE MOP - x7000"),
    ShortSheetLineItem("MOPS", "GREY_MOP_20_X7540", "20\" GREY MOP - x7540"),
    ShortSheetLineItem("DUST", "DUST_24_X2570", "24\" DUST - x2570"),
    ShortSheetLineItem("DUST", "DUST_36_X2590", "36\" DUST - x2590"),
    ShortSheetLineItem("DUST", "DUST_48_X2604", "48\" DUST - x2604"),
    ShortSheetLineItem("DUST", "DUST_60_X2610", "60\" DUST - x2610"),
    ShortSheetLineItem("ACCESSORIES", "FENDER_COVERS_X2191", "FENDER COVERS - x2191"),
    ShortSheetLineItem("SHOP", "WHITE_SHOP_TOWELS", "WHITE SHOP TOWELS"),
    ShortSheetLineItem("SHOP", "RED_SHOP_TOWELS", "RED SHOP TOWELS"),
    ShortSheetLineItem("3X5", "3X5_BLACK", "3X5 BLACK"),
    ShortSheetLineItem("3X5", "3X5_ONYX", "3X5 ONYX"),
    ShortSheetLineItem("3X5", "3X5_COPPER", "3X5 COPPER"),
    ShortSheetLineItem("3X5", "3X5_INDIGO", "3X5 INDIGO"),
    ShortSheetLineItem("PAPER", "SIG_SERIES_HW_X20023", "SIG SERIES HW - x20023"),
    ShortSheetLineItem("PAPER", "BROWN_HW_X9173", "BROWN HW - x9173"),
    ShortSheetLineItem("PAPER", "C_PULL_PAPER_X9025", "C-PULL PAPER - x9025"),
    ShortSheetLineItem("PAPER", "DRC_AIRLAID_PAPER_X9511", "DRC AIRLAID PAPER - x9511"),
    ShortSheetLineItem("PAPER", "SIG_SERIES_Z_FOLD_X27012", "SIG SERIES Z-FOLD - x27012"),
    ShortSheetLineItem("PAPER", "B_V_Z_FOLD_X45695", "B&V Z-FOLD - x45695"),
    ShortSheetLineItem("PAPER", "JRT_TOILET_PAPER_X9110", "JRT TOILET PAPER - x9110"),
    ShortSheetLineItem("PAPER", "SIG_SERIES_TP_X27083", "SIG SERIES TP - x27083"),
    ShortSheetLineItem("PAPER", "B_V_TP_X45697", "B&V TP - x45697"),
    ShortSheetLineItem("4X6", "4X6_BLACK", "4X6 BLACK"),
    ShortSheetLineItem("4X6", "4X6_ONYX", "4X6 ONYX"),
    ShortSheetLineItem("4X6", "4X6_COPPER", "4X6 COPPER"),
    ShortSheetLineItem("4X6", "4X6_INDIGO", "4X6 INDIGO"),
    ShortSheetLineItem("MATS", "URINAL_MATS", "URINAL MATS"),
    ShortSheetLineItem("MATS", "TOILET_MATS", "TOILET MATS"),
    ShortSheetLineItem("TRAFFIC", "TRAFFIC_3X10", "3x10 TRAFFIC"),
    ShortSheetLineItem("TRAFFIC", "TRAFFIC_3X5", "3x5 TRAFFIC"),
    ShortSheetLineItem("TRAFFIC", "TRAFFIC_4X6", "4x6 TRAFFIC"),
    ShortSheetLineItem("SPECIAL", "SIG_SOAP_X27070", "SIG SOAP - x27070"),
    ShortSheetLineItem("SPECIAL", "SMALL_INK_TOWELS", "SMALL INK TOWELS"),
    ShortSheetLineItem("SPECIAL", "LARGE_INK_TOWELS", "LARGE INK TOWELS"),
    ShortSheetLineItem("SPECIAL", "RAZ_MATS", "RAZ MATS"),
    ShortSheetLineItem("SPECIAL", "SOAKER_PADS", "SOAKER PADS"),
]


TRUCK_SHORTAGE_TEMPLATE = ShortSheetTemplate(
    template_id=TRUCK_SHORTAGE_TEMPLATE_ID,
    name="Truck Shortage Sheet (Load)",
    line_items=MANUAL_SHORT_SHEET_LINE_ITEMS,
    expected_truck_slots=16,
)


def _build_unload_batching_line_items() -> list[ShortSheetLineItem]:
    items: list[ShortSheetLineItem] = []
    for lot_num in range(1, 7):
        for row_num in range(1, 9):
            for field_name in ("WEARERS", "BATCH", "SWEPT", "LOT"):
                items.append(
                    ShortSheetLineItem(
                        section=f"B{lot_num}",
                        code=f"B{lot_num}_R{row_num}_{field_name}",
                        label=f"B{lot_num} Row {row_num} {field_name.title()}",
                    )
                )

    for dust_route in (80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 92, 93, 94, 95):
        for field_name in ("WEARERS", "SWEPT", "BATCH", "LOT"):
            items.append(
                ShortSheetLineItem(
                    section="DUST_TABLE",
                    code=f"DUST_{int(dust_route)}_{field_name}",
                    label=f"Dust {int(dust_route)} {field_name.title()}",
                )
            )

    items.extend(
        [
            ShortSheetLineItem("NOTES", "NOTES_TEXT", "Notes"),
            ShortSheetLineItem("NOTES", "ROUTES_WEARERS_TEXT", "Routes and (Wearers)"),
            ShortSheetLineItem("NOTES", "OFF_NEXT_DAY_TEXT", "Off Next Day"),
        ]
    )
    return items


UNLOAD_BATCHING_TEMPLATE = ShortSheetTemplate(
    template_id=UNLOAD_BATCHING_TEMPLATE_ID,
    name="Unloads Batching Sheet",
    line_items=_build_unload_batching_line_items(),
    expected_truck_slots=0,
)


SUPPORTED_TEMPLATES: dict[str, ShortSheetTemplate] = {
    TRUCK_SHORTAGE_TEMPLATE_ID: TRUCK_SHORTAGE_TEMPLATE,
    UNLOAD_BATCHING_TEMPLATE_ID: UNLOAD_BATCHING_TEMPLATE,
}


_DATE_RE = re.compile(r"\b(\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?)\b")
_NUM_RE = re.compile(r"\b\d{1,3}\b")
_TOKEN_RE = re.compile(r"[A-Za-z0-9]+")


def get_manual_short_sheet_template() -> ShortSheetTemplate:
    return TRUCK_SHORTAGE_TEMPLATE


def get_supported_templates() -> list[ShortSheetTemplate]:
    return [SUPPORTED_TEMPLATES[key] for key in (TRUCK_SHORTAGE_TEMPLATE_ID, UNLOAD_BATCHING_TEMPLATE_ID)]


def get_template(template_id: str | None) -> ShortSheetTemplate:
    template_key = str(template_id or "").strip()
    return SUPPORTED_TEMPLATES.get(template_key, TRUCK_SHORTAGE_TEMPLATE)


def detect_template_id(raw_text: str, filename: str | None = None) -> str:
    template_id, _confidence = detect_template_with_confidence(raw_text, filename)
    return template_id


def detect_template_with_confidence(raw_text: str, filename: str | None = None) -> tuple[str, float]:
    haystack = f"{str(filename or '').lower()}\n{str(raw_text or '').lower()}"

    batching_markers = (
        "unloading day",
        "garments to unload",
        "batch size",
        "b1 lots",
        "off next day",
        "routes and (wearers)",
    )
    shortage_markers = (
        "special requests",
        "dust routes w/ uniforms",
        "soaker pads needed",
        "ink towels needed",
        "3x10 black",
        "micro tube mop",
    )

    batching_score = sum(1 for marker in batching_markers if marker in haystack)
    shortage_score = sum(1 for marker in shortage_markers if marker in haystack)

    if batching_score > shortage_score:
        confidence = min(1.0, 0.35 + 0.12 * float(batching_score - shortage_score))
        return UNLOAD_BATCHING_TEMPLATE_ID, confidence
    if shortage_score > batching_score:
        confidence = min(1.0, 0.35 + 0.12 * float(shortage_score - batching_score))
        return TRUCK_SHORTAGE_TEMPLATE_ID, confidence

    if "batch" in haystack or "unloading" in haystack:
        return UNLOAD_BATCHING_TEMPLATE_ID, 0.45
    return TRUCK_SHORTAGE_TEMPLATE_ID, 0.40


def _estimate_parse_confidence(
    *,
    raw_text: str,
    template: ShortSheetTemplate,
    date_text: str | None,
    route_day_text: str | None,
    truck_slots: list[TruckSlot],
    template_detection_confidence: float,
    ocr_token_confidence: float,
) -> float:
    confidence = 0.0
    if str(raw_text or "").strip():
        confidence += 0.10

    # Token-level OCR confidence from image_to_data tends to be a strong quality signal.
    confidence += min(0.35, max(0.0, float(ocr_token_confidence)) * 0.35)

    lowered = str(raw_text or "").lower()
    if template.template_id == UNLOAD_BATCHING_TEMPLATE_ID:
        anchor_hits = 0
        for marker in ("unloading day", "garments to unload", "batch size", "b1 lots", "off next day", "routes and (wearers)"):
            if marker in lowered:
                anchor_hits += 1
        confidence += min(0.20, 0.04 * float(anchor_hits))
    else:
        anchor_hits = 0
        for marker in ("truck", "route", "initials", "special requests", "dust routes", "micro tube mop", "red shop towels"):
            if marker in lowered:
                anchor_hits += 1
        confidence += min(0.20, 0.03 * float(anchor_hits))

    if date_text:
        confidence += 0.15
    if route_day_text:
        confidence += 0.10

    expected_slots = int(template.expected_truck_slots or 0)
    if expected_slots > 0:
        filled_trucks = sum(1 for slot in truck_slots if str(slot.truck or "").strip())
        slot_ratio = float(filled_trucks) / float(expected_slots)
        confidence += min(0.15, max(0.0, slot_ratio) * 0.15)
    else:
        marker_hits = 0
        for marker in ("unloading day", "garments to unload", "batch", "wearers", "off next day"):
            if marker in lowered:
                marker_hits += 1
        confidence += min(0.15, 0.03 * float(marker_hits))

    confidence += min(0.20, max(0.0, float(template_detection_confidence)) * 0.20)
    return max(0.0, min(1.0, confidence))


def _load_image(raw_bytes: bytes):
    if Image is None:
        raise RuntimeError("Pillow is required to inspect short-sheet images.")

    prepared = load_short_sheet_image(raw_bytes)
    return prepared


def _ocr_image(image_obj) -> tuple[str, float]:
    if pytesseract is None:
        return "", 0.0

    text_out = ""
    token_confidences: list[float] = []
    try:
        text_out = str(pytesseract.image_to_string(image_obj, config="--psm 6"))
    except Exception:
        text_out = ""

    if TesseractOutput is not None:
        try:
            ocr_data = pytesseract.image_to_data(image_obj, output_type=TesseractOutput.DICT, config="--psm 6")
            for idx in range(len(ocr_data.get("text", []))):
                token = str(ocr_data.get("text", [""])[idx] or "").strip()
                conf_raw = str(ocr_data.get("conf", ["-1"])[idx] or "-1").strip()
                if not token:
                    continue
                try:
                    conf_val = float(conf_raw)
                except Exception:
                    continue
                if conf_val >= 0.0:
                    token_confidences.append(max(0.0, min(100.0, conf_val)) / 100.0)
        except Exception:
            pass

    avg_token_conf = float(sum(token_confidences) / len(token_confidences)) if token_confidences else 0.0
    return text_out, avg_token_conf


def _extract_date_text(text: str) -> str | None:
    match = _DATE_RE.search(text or "")
    return match.group(1) if match else None


def _extract_numeric_candidates(text: str) -> list[str]:
    return _NUM_RE.findall(text or "")


def _looks_like_initials(token: str) -> bool:
    token = str(token or "").strip()
    return 1 <= len(token) <= 3 and token.isalpha() and token.upper() == token


def _extract_route_day_text(text: str) -> str | None:
    lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
    for line in lines[:8]:
        numbers = _extract_numeric_candidates(line)
        tokens = _TOKEN_RE.findall(line)
        if len(numbers) == 1 and len(tokens) == 1:
            return numbers[0]
    for line in lines[:8]:
        numbers = _extract_numeric_candidates(line)
        if len(numbers) == 1:
            return numbers[0]
    return None


def _extract_truck_slots_from_text(text: str, expected_slots: int) -> list[TruckSlot]:
    if int(expected_slots or 0) <= 0:
        return []

    lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
    candidate_lines: list[tuple[str, list[str], list[str]]] = []
    for line in lines[:12]:
        tokens = _TOKEN_RE.findall(line)
        if not tokens:
            continue
        numeric_tokens = [token for token in tokens if token.isdigit()]
        alpha_tokens = [token for token in tokens if token.isalpha()]
        if len(numeric_tokens) >= 2:
            candidate_lines.append(("numeric", tokens, numeric_tokens))
        elif len(alpha_tokens) >= 2 and all(_looks_like_initials(token) for token in alpha_tokens):
            candidate_lines.append(("alpha", tokens, alpha_tokens))

    truck_tokens: list[str] = []
    route_tokens: list[str] = []
    initials_tokens: list[str] = []
    for category, tokens, extracted_tokens in candidate_lines:
        if category == "numeric" and not truck_tokens:
            truck_tokens = extracted_tokens[:expected_slots]
            continue
        if category == "numeric" and not route_tokens:
            route_tokens = extracted_tokens[:expected_slots]
            continue
        if category == "alpha" and not initials_tokens:
            initials_tokens = extracted_tokens[:expected_slots]
            continue

    slots = [TruckSlot(column_index=index + 1) for index in range(int(expected_slots))]
    for index, slot in enumerate(slots):
        if index < len(truck_tokens):
            slot.truck = truck_tokens[index]
            slot.confidence = 0.55
        if index < len(route_tokens):
            slot.route = route_tokens[index]
            slot.confidence = max(slot.confidence, 0.5)
        if index < len(initials_tokens):
            slot.initials = initials_tokens[index]
            slot.confidence = max(slot.confidence, 0.45)
    return slots


def _build_empty_slots(template: ShortSheetTemplate) -> list[TruckSlot]:
    return [TruckSlot(column_index=index + 1) for index in range(template.expected_truck_slots)]


def _build_empty_cells(template: ShortSheetTemplate, truck_slots: Iterable[TruckSlot]) -> list[ShortSheetCellValue]:
    slots = list(truck_slots)
    cells: list[ShortSheetCellValue] = []
    if not slots:
        for line_item in template.line_items:
            cells.append(
                ShortSheetCellValue(
                    column_index=0,
                    line_item_code=line_item.code,
                    line_item_label=line_item.label,
                    section=line_item.section,
                    confidence=0.0,
                    needs_review=True,
                )
            )
        return cells

    for slot in slots:
        for line_item in template.line_items:
            cells.append(
                ShortSheetCellValue(
                    column_index=slot.column_index,
                    line_item_code=line_item.code,
                    line_item_label=line_item.label,
                    section=line_item.section,
                    truck=slot.truck,
                    route=slot.route,
                    initials=slot.initials,
                    confidence=0.0,
                    needs_review=True,
                )
            )
    return cells


def _make_issue(code: str, severity: str, message: str, *, suggestion: str | None = None) -> ShortSheetIssue:
    return ShortSheetIssue(code=code, severity=severity, message=message, suggestion=suggestion)


def process_short_sheet(
    upload_bytes: bytes,
    filename: str | None = None,
    *,
    template_id: str | None = None,
) -> ShortSheetResult:
    started_at = time.perf_counter()
    issues: list[ShortSheetIssue] = []
    requested_template_id = str(template_id or "").strip() or None
    template = get_template(requested_template_id)

    if not upload_bytes:
        header = ShortSheetHeader(truck_slots=_build_empty_slots(template))
        return ShortSheetResult(
            schema_version=SCHEMA_VERSION,
            processor_version=PROCESSOR_VERSION,
            status="failed",
            template_id=template.template_id,
            source_filename=filename,
            image_size=None,
            header=header,
            cells=[],
            issues=[_make_issue("EMPTY_UPLOAD", "error", "No file bytes were provided.")],
            raw_ocr_text="",
            template_matched=False,
            processing_ms=int((time.perf_counter() - started_at) * 1000),
        )

    try:
        prepared = _load_image(upload_bytes)
    except Exception as exc:
        header = ShortSheetHeader(truck_slots=_build_empty_slots(template))
        return ShortSheetResult(
            schema_version=SCHEMA_VERSION,
            processor_version=PROCESSOR_VERSION,
            status="failed",
            template_id=template.template_id,
            source_filename=filename,
            image_size=None,
            header=header,
            cells=[],
            issues=[_make_issue("IMAGE_LOAD_FAILED", "error", f"Could not read image: {exc}")],
            raw_ocr_text="",
            template_matched=False,
            processing_ms=int((time.perf_counter() - started_at) * 1000),
        )

    raw_text, ocr_token_confidence = _ocr_image(prepared.ocr_ready_image)
    template_detection_confidence = 1.0 if requested_template_id else 0.0
    if requested_template_id is None:
        guessed_template_id, template_detection_confidence = detect_template_with_confidence(raw_text, filename)
        template = get_template(guessed_template_id)
        issues.append(
            _make_issue(
                "TEMPLATE_AUTO_DETECTED",
                "info",
                f"Auto-detected sheet type: {template.name} (confidence {template_detection_confidence:.2f})",
            )
        )

    header_text = raw_text[:1200]
    date_text = _extract_date_text(header_text)
    route_day_text = _extract_route_day_text(header_text)
    truck_slots = _extract_truck_slots_from_text(header_text, template.expected_truck_slots)

    if pytesseract is None:
        issues.append(
            _make_issue(
                "TESSERACT_UNAVAILABLE",
                "warn",
                "Pytesseract is not installed yet, so only the image can be staged right now.",
                suggestion="Install pytesseract and a Tesseract OCR binary to enable text extraction.",
            )
        )
    if not raw_text.strip():
        issues.append(
            _make_issue(
                "NO_OCR_TEXT",
                "warn",
                "No OCR text was extracted from the image.",
                suggestion="Use a clearer photo or add OCR dependencies.",
            )
        )

    header = ShortSheetHeader(
        date_text=date_text,
        route_day_text=route_day_text,
        special_requests_text=None,
        truck_slots=truck_slots,
    )

    parse_confidence = _estimate_parse_confidence(
        raw_text=raw_text,
        template=template,
        date_text=date_text,
        route_day_text=route_day_text,
        truck_slots=truck_slots,
        template_detection_confidence=template_detection_confidence,
        ocr_token_confidence=ocr_token_confidence,
    )

    issues.append(
        _make_issue(
            "PARSE_CONFIDENCE",
            "info",
            f"Parse confidence: {parse_confidence:.2f} (OCR token confidence: {ocr_token_confidence:.2f})",
        )
    )

    if parse_confidence < 0.45:
        issues.append(
            _make_issue(
                "LOW_PARSE_CONFIDENCE",
                "warn",
                f"Parse confidence is low ({parse_confidence:.2f}). Please upload another photo.",
                suggestion="Retake with better lighting, straight alignment, and full page visible.",
            )
        )

    cells = _build_empty_cells(template, header.truck_slots)
    if not raw_text.strip():
        status: str = "needs_review"
    else:
        status = "needs_review"

    if not header.date_text:
        issues.append(
            _make_issue(
                "DATE_NOT_FOUND",
                "info",
                "Could not confidently detect the date field.",
                suggestion="Fill the date manually in the review screen.",
            )
        )

    return ShortSheetResult(
        schema_version=SCHEMA_VERSION,
        processor_version=PROCESSOR_VERSION,
        status=status,
        template_id=template.template_id,
        source_filename=filename,
        image_size=(int(getattr(prepared.original_image, "width", 0)), int(getattr(prepared.original_image, "height", 0))),
        header=header,
        cells=cells,
        issues=issues,
        raw_ocr_text=raw_text,
        image_mode=str(getattr(prepared.original_image, "mode", "")) or None,
        rotation_degrees=int(getattr(prepared, "rotation_degrees", 0) or 0),
        template_matched=True,
        template_detection_confidence=float(template_detection_confidence),
        ocr_token_confidence=float(ocr_token_confidence),
        parse_confidence=float(parse_confidence),
        processing_ms=int((time.perf_counter() - started_at) * 1000),
    )
