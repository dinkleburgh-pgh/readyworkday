from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from loadunload_ocr import get_supported_templates, get_template, process_short_sheet
from loadunload_ocr.export import (
    build_excel_bytes,
    build_header_review_frame,
    build_json_bytes,
    build_line_item_review_grid,
    build_truck_slot_review_frame,
)


st.set_page_config(page_title="Short Sheet OCR", page_icon="📄", layout="wide")

st.title("Short Sheet OCR")
st.caption("Standalone review-first upload flow for manual short sheets.")

template_catalog = get_supported_templates()
template_labels = [template.name for template in template_catalog]
template_lookup = {template.name: template for template in template_catalog}
AUTO_TEMPLATE_LABEL = "Auto-detect from image"

with st.sidebar:
    st.header("Template")
    selected_template_label = st.selectbox(
        "Sheet Type",
        options=[AUTO_TEMPLATE_LABEL, *template_labels],
        index=0,
        key="short_sheet_template_picker",
    )
    selected_template = template_lookup.get(selected_template_label)
    if selected_template is None:
        st.write("Using parser auto-detection")
    else:
        st.write(selected_template.name)
        st.write(f"{len(selected_template.line_items)} line items")
        st.write(f"{selected_template.expected_truck_slots} truck slots")
    st.divider()
    st.markdown(
        "Upload a short-sheet photo, inspect the parsed result, edit the review grid, then export to Excel or JSON.",
    )

uploaded_file = st.file_uploader(
    "Upload a short sheet image",
    type=["png", "jpg", "jpeg", "webp", "heic", "tif", "tiff"],
    accept_multiple_files=False,
)

if uploaded_file is not None:
    selected_template_id = selected_template.template_id if selected_template is not None else "AUTO"
    upload_signature = f"{selected_template_id}:{uploaded_file.name}:{int(getattr(uploaded_file, 'size', 0) or 0)}"
    previous_signature = str(st.session_state.get("short_sheet_upload_signature") or "")

    result = process_short_sheet(
        uploaded_file.getvalue(),
        uploaded_file.name,
        template_id=selected_template_id if selected_template_id != "AUTO" else None,
    )
    active_template = get_template(result.template_id)

    header_review_key = "short_sheet_header_review"
    truck_slot_review_key = "short_sheet_truck_slot_review"
    line_item_review_key = "short_sheet_line_item_review"

    if previous_signature != upload_signature:
        st.session_state["short_sheet_upload_signature"] = upload_signature
        st.session_state.pop(header_review_key, None)
        st.session_state.pop(truck_slot_review_key, None)
        st.session_state.pop(line_item_review_key, None)

    if header_review_key not in st.session_state:
        st.session_state[header_review_key] = build_header_review_frame(result)
    if truck_slot_review_key not in st.session_state:
        st.session_state[truck_slot_review_key] = build_truck_slot_review_frame(result)
    if line_item_review_key not in st.session_state:
        st.session_state[line_item_review_key] = build_line_item_review_grid(result, active_template)

    header_review = st.session_state[header_review_key]
    truck_slot_review = st.session_state[truck_slot_review_key]
    line_item_review = st.session_state[line_item_review_key]

    st.subheader("Parse Status")
    status_columns = st.columns(4)
    status_columns[0].metric("Status", result.status)
    status_columns[1].metric("Issues", len(result.issues))
    status_columns[2].metric("Parse Confidence", f"{float(result.parse_confidence or 0.0):.2f}")
    status_columns[3].metric("OCR Confidence", f"{float(result.ocr_token_confidence or 0.0):.2f}")
    st.caption(f"Schema {result.schema_version} | Processor {result.processor_version}")
    st.caption(f"Detected sheet type: {active_template.name}")

    if result.issues:
        st.warning("The first pass needs review before export.")
        issues_frame = pd.DataFrame([issue.to_dict() for issue in result.issues])
        st.dataframe(issues_frame, use_container_width=True, hide_index=True)
    else:
        st.success("No blocking issues detected.")

    low_confidence = any(str(issue.code or "") == "LOW_PARSE_CONFIDENCE" for issue in (result.issues or []))
    if low_confidence:
        st.error("This photo parsed with low confidence. Please upload another photo before exporting.")
        st.info("Tips: keep the page flat, capture the full sheet, use brighter light, and avoid blur.")

    with st.expander("Parsed header", expanded=False):
        st.caption("Top sheet metadata. Edit this first.")
        edited_header = st.data_editor(
            header_review,
            use_container_width=True,
            hide_index=True,
            num_rows="fixed",
            key="short_sheet_header_review_editor",
        )
        st.session_state[header_review_key] = edited_header

    with st.expander("Truck slots", expanded=False):
        st.caption("One row per truck column with truck, route, and initials.")
        edited_slots = st.data_editor(
            truck_slot_review,
            use_container_width=True,
            hide_index=True,
            num_rows="fixed",
            key="short_sheet_truck_slot_review_editor",
        )
        st.session_state[truck_slot_review_key] = edited_slots

    st.subheader("Line Item Grid")
    st.caption("Edit the cells below. This is the draft output for the product matrix.")
    edited_grid = st.data_editor(
        line_item_review,
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
        key="short_sheet_line_item_review_editor",
    )
    st.session_state[line_item_review_key] = edited_grid

    with st.expander("Raw OCR text", expanded=False):
        st.text(result.raw_ocr_text or "No OCR text extracted yet.")

    export_columns = st.columns(3)
    excel_bytes = build_excel_bytes(result, edited_grid, edited_header, edited_slots)
    json_bytes = build_json_bytes(result, edited_grid, edited_header, edited_slots)
    export_columns[0].download_button(
        "Download Excel",
        data=excel_bytes,
        file_name=f"{Path(uploaded_file.name).stem}_short_sheet.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
        disabled=low_confidence,
    )
    export_columns[1].download_button(
        "Download JSON",
        data=json_bytes,
        file_name=f"{Path(uploaded_file.name).stem}_short_sheet.json",
        mime="application/json",
        use_container_width=True,
        disabled=low_confidence,
    )
    export_columns[2].download_button(
        "Download CSV",
        data=edited_grid.to_csv(index=False).encode("utf-8"),
        file_name=f"{Path(uploaded_file.name).stem}_short_sheet_review.csv",
        mime="text/csv",
        use_container_width=True,
        disabled=low_confidence,
    )

    with st.expander("Line item catalog", expanded=False):
        st.dataframe(pd.DataFrame([item.to_dict() for item in active_template.line_items]), use_container_width=True, hide_index=True)

else:
    st.info("Upload a short sheet photo to begin parsing.")
    st.markdown(
        "This page is intentionally separate from the main app so OCR can be improved without risking live workflow logic.",
    )
