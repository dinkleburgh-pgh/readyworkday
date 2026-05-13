from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


IssueSeverity = Literal["info", "warn", "error"]
ResultStatus = Literal["ok", "needs_review", "failed"]


@dataclass(slots=True)
class ShortSheetIssue:
    code: str
    severity: IssueSeverity
    message: str
    row_index: int | None = None
    field: str | None = None
    suggestion: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class TruckSlot:
    column_index: int
    truck: str | None = None
    route: str | None = None
    initials: str | None = None
    confidence: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ShortSheetHeader:
    date_text: str | None = None
    route_day_text: str | None = None
    special_requests_text: str | None = None
    truck_slots: list[TruckSlot] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["truck_slots"] = [slot.to_dict() for slot in self.truck_slots]
        return payload


@dataclass(slots=True)
class ShortSheetLineItem:
    section: str
    code: str
    label: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ShortSheetCellValue:
    column_index: int
    line_item_code: str
    line_item_label: str
    section: str
    value_text: str | None = None
    numeric_value: int | float | None = None
    truck: str | None = None
    route: str | None = None
    initials: str | None = None
    confidence: float = 0.0
    needs_review: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ShortSheetTemplate:
    template_id: str
    name: str
    line_items: list[ShortSheetLineItem]
    expected_truck_slots: int = 0

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["line_items"] = [item.to_dict() for item in self.line_items]
        return payload


@dataclass(slots=True)
class ShortSheetResult:
    schema_version: int
    processor_version: str
    status: ResultStatus
    template_id: str
    source_filename: str | None
    image_size: tuple[int, int] | None
    header: ShortSheetHeader
    cells: list[ShortSheetCellValue]
    issues: list[ShortSheetIssue]
    raw_ocr_text: str = ""
    image_mode: str | None = None
    rotation_degrees: int | None = None
    template_matched: bool = False
    template_detection_confidence: float | None = None
    ocr_token_confidence: float | None = None
    parse_confidence: float | None = None
    processing_ms: int | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["header"] = self.header.to_dict()
        payload["cells"] = [cell.to_dict() for cell in self.cells]
        payload["issues"] = [issue.to_dict() for issue in self.issues]
        return payload

    def to_frames(self):
        import pandas as pd

        header_frame = pd.DataFrame([self.header.to_dict()])
        cells_frame = pd.DataFrame([cell.to_dict() for cell in self.cells])
        issues_frame = pd.DataFrame([issue.to_dict() for issue in self.issues])
        return header_frame, cells_frame, issues_frame
