from __future__ import annotations

import json
from io import BytesIO
from typing import Any

import pandas as pd

from .models import ShortSheetResult, ShortSheetTemplate
from .pipeline import get_manual_short_sheet_template


def build_header_review_frame(result: ShortSheetResult) -> pd.DataFrame:
    header = result.header
    return pd.DataFrame(
        [
            {
                "date_text": header.date_text or "",
                "route_day_text": header.route_day_text or "",
                "special_requests_text": header.special_requests_text or "",
            }
        ]
    )


def build_truck_slot_review_frame(result: ShortSheetResult) -> pd.DataFrame:
    slots = result.header.truck_slots or []
    rows = []
    for slot in slots:
        rows.append(
            {
                "column_index": slot.column_index,
                "truck": slot.truck or "",
                "route": slot.route or "",
                "initials": slot.initials or "",
                "confidence": slot.confidence,
            }
        )
    if not rows:
        return pd.DataFrame(columns=["column_index", "truck", "route", "initials", "confidence"])
    return pd.DataFrame(rows)


def build_line_item_review_grid(result: ShortSheetResult, template: ShortSheetTemplate | None = None) -> pd.DataFrame:
    template = template or get_manual_short_sheet_template()
    if int(template.expected_truck_slots or 0) <= 0:
        return pd.DataFrame(
            [
                {
                    "section": line_item.section,
                    "line_item_code": line_item.code,
                    "line_item_label": line_item.label,
                    "value_text": "",
                }
                for line_item in template.line_items
            ]
        )

    truck_slots = result.header.truck_slots or []
    slot_labels = [
        f"Truck {slot.column_index}" if not str(slot.truck or "").strip() else str(slot.truck)
        for slot in truck_slots
    ]
    if not slot_labels:
        slot_labels = [f"Truck {index + 1}" for index in range(template.expected_truck_slots)]

    rows: list[dict[str, Any]] = []
    for line_item in template.line_items:
        row: dict[str, Any] = {
            "section": line_item.section,
            "line_item_code": line_item.code,
            "line_item_label": line_item.label,
        }
        for label in slot_labels:
            row[label] = ""
        rows.append(row)

    return pd.DataFrame(rows)


def build_summary_frame(result: ShortSheetResult) -> pd.DataFrame:
    header = result.header
    summary = {
        "schema_version": result.schema_version,
        "processor_version": result.processor_version,
        "status": result.status,
        "template_id": result.template_id,
        "source_filename": result.source_filename or "",
        "image_width": result.image_size[0] if result.image_size else None,
        "image_height": result.image_size[1] if result.image_size else None,
        "image_mode": result.image_mode or "",
        "rotation_degrees": result.rotation_degrees,
        "template_matched": result.template_matched,
        "processing_ms": result.processing_ms,
        "date_text": header.date_text or "",
        "route_day_text": header.route_day_text or "",
        "special_requests_text": header.special_requests_text or "",
        "truck_slots_detected": len(header.truck_slots or []),
        "issue_count": len(result.issues or []),
    }
    return pd.DataFrame([summary])


def build_issues_frame(result: ShortSheetResult) -> pd.DataFrame:
    return pd.DataFrame([issue.to_dict() for issue in result.issues])


def build_raw_ocr_frame(result: ShortSheetResult) -> pd.DataFrame:
    lines = [line.strip() for line in (result.raw_ocr_text or "").splitlines() if line.strip()]
    if not lines:
        lines = [""]
    return pd.DataFrame({"raw_ocr_text": lines})


def build_excel_bytes(
    result: ShortSheetResult,
    review_grid: pd.DataFrame | None = None,
    header_review: pd.DataFrame | None = None,
    truck_slot_review: pd.DataFrame | None = None,
) -> bytes:
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        build_summary_frame(result).to_excel(writer, index=False, sheet_name="Summary")
        (header_review if header_review is not None else build_header_review_frame(result)).to_excel(
            writer,
            index=False,
            sheet_name="Header Review",
        )
        (truck_slot_review if truck_slot_review is not None else build_truck_slot_review_frame(result)).to_excel(
            writer,
            index=False,
            sheet_name="Truck Slot Review",
        )
        build_issues_frame(result).to_excel(writer, index=False, sheet_name="Issues")
        build_raw_ocr_frame(result).to_excel(writer, index=False, sheet_name="OCR Text")
        review_df = review_grid if review_grid is not None else build_line_item_review_grid(result)
        review_df.to_excel(writer, index=False, sheet_name="Line Item Grid")
        pd.DataFrame([cell.to_dict() for cell in result.cells]).to_excel(writer, index=False, sheet_name="Cells")
    return buffer.getvalue()


def build_json_bytes(
    result: ShortSheetResult,
    review_grid: pd.DataFrame | None = None,
    header_review: pd.DataFrame | None = None,
    truck_slot_review: pd.DataFrame | None = None,
) -> bytes:
    payload = result.to_dict()
    if review_grid is not None:
        payload["line_item_grid"] = review_grid.to_dict(orient="records")
    if header_review is not None:
        payload["header_review"] = header_review.to_dict(orient="records")
    if truck_slot_review is not None:
        payload["truck_slot_review"] = truck_slot_review.to_dict(orient="records")
    return json.dumps(payload, indent=2, ensure_ascii=False, default=str).encode("utf-8")
