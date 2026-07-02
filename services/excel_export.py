import json
from pathlib import Path

import openpyxl


def _load_field_map(field_map_path: str) -> dict:
    with open(field_map_path, encoding="utf-8") as f:
        return json.load(f)


def build_excel_fields(
    summary: dict,
    project_name: str,
    project_phase: str,
    activity_name: str,
    meeting_location: str,
    organizer: str,
) -> dict:
    """Flatten the Claude summary + manually entered project info into the
    free-text fields the company's meeting-minutes template expects."""
    content_parts = []
    if summary.get("agenda"):
        content_parts.append("[안건]\n" + "\n".join(f"- {a}" for a in summary["agenda"]))
    if summary.get("discussion_summary"):
        content_parts.append("[논의 내용]\n" + summary["discussion_summary"])
    if summary.get("decisions"):
        content_parts.append("[결정 사항]\n" + "\n".join(f"- {d}" for d in summary["decisions"]))

    action_items_text = (
        "\n".join(
            f"- {item.get('task', '')} (담당자: {item.get('owner') or '-'}, 기한: {item.get('due_date') or '-'})"
            for item in summary.get("action_items", [])
        )
        or "-"
    )

    return {
        "project_name": project_name,
        "project_phase": project_phase,
        "activity_name": activity_name,
        "meeting_date": summary.get("meeting_date", ""),
        "meeting_location": meeting_location,
        "organizer": organizer,
        "attendees": ", ".join(summary.get("attendees", [])),
        "meeting_title": summary.get("meeting_title", ""),
        "discussion_summary": "\n\n".join(content_parts),
        "action_items_text": action_items_text,
    }


def fill_template(fields: dict, template_path: str, field_map_path: str, output_path: str) -> str:
    """Write flattened field values into the cells described by field_map_path's
    scalar_fields mapping (field name -> cell address)."""
    field_map = _load_field_map(field_map_path)
    wb = openpyxl.load_workbook(template_path)
    ws = wb.active

    for field, cell in field_map.get("scalar_fields", {}).items():
        ws[cell] = fields.get(field, "")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    wb.save(output_path)
    return output_path
