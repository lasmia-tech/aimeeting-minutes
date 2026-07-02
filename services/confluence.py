from html import escape

import requests
from requests.auth import HTTPBasicAuth


class ConfluenceClient:
    def __init__(self, base_url: str, email: str, api_token: str):
        self.base_url = base_url.rstrip("/")
        self.auth = HTTPBasicAuth(email, api_token)
        self.headers = {"Content-Type": "application/json"}

    def find_page_id(self, space_key: str, title: str) -> str:
        resp = requests.get(
            f"{self.base_url}/rest/api/content",
            params={"spaceKey": space_key, "title": title},
            auth=self.auth,
            headers=self.headers,
            timeout=30,
        )
        resp.raise_for_status()
        results = resp.json().get("results", [])
        if not results:
            raise ValueError(f"페이지를 찾지 못했습니다: space={space_key} title={title!r}")
        return results[0]["id"]

    def create_child_page(self, space_key: str, parent_title: str, new_title: str, html_body: str) -> dict:
        parent_id = self.find_page_id(space_key, parent_title)
        payload = {
            "type": "page",
            "title": new_title,
            "space": {"key": space_key},
            "ancestors": [{"id": parent_id}],
            "body": {"storage": {"value": html_body, "representation": "storage"}},
        }
        resp = requests.post(
            f"{self.base_url}/rest/api/content",
            json=payload,
            auth=self.auth,
            headers=self.headers,
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()


def _multiline_html(text: str) -> str:
    return "<br/>".join(escape(line) for line in text.splitlines()) or "-"


def build_storage_html(fields: dict) -> str:
    """Render the flattened meeting-minutes fields (same shape as
    excel_export.build_excel_fields) as Confluence storage-format HTML,
    matching the company's meeting-minutes page layout."""
    label = ' style="background-color:#f2f2f2;"'

    return f"""
<table style="width:100%;table-layout:fixed;">
  <colgroup>
    <col style="width:15%;" /><col style="width:18%;" />
    <col style="width:15%;" /><col style="width:18%;" />
    <col style="width:15%;" /><col style="width:19%;" />
  </colgroup>
  <tbody>
    <tr><th colspan="6" style="text-align:center;background-color:#dce6f1;"><strong>회의록</strong></th></tr>
    <tr>
      <th{label}>*프로젝트명</th><td>{escape(fields.get('project_name', ''))}</td>
      <th{label}>*프로젝트 단계</th><td>{escape(fields.get('project_phase', ''))}</td>
      <th{label}>*활동명</th><td>{escape(fields.get('activity_name', ''))}</td>
    </tr>
    <tr>
      <th{label}>*회의일시</th><td>{escape(fields.get('meeting_date', ''))}</td>
      <th{label}>*회의장소</th><td>{escape(fields.get('meeting_location', ''))}</td>
      <th{label}>*주관사</th><td>{escape(fields.get('organizer', ''))}</td>
    </tr>
    <tr><th{label}>*참석자</th><td colspan="5">{escape(fields.get('attendees', ''))}</td></tr>
    <tr><th{label}>*회의제목</th><td colspan="5">{escape(fields.get('meeting_title', ''))}</td></tr>
    <tr><th{label}>*회의내용</th><td colspan="5">{_multiline_html(fields.get('discussion_summary', ''))}</td></tr>
    <tr><th{label}>Action Item</th><td colspan="5">{_multiline_html(fields.get('action_items_text', ''))}</td></tr>
  </tbody>
</table>
"""
