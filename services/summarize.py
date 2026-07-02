import json
import re

import anthropic

SUMMARY_PROMPT = """다음은 회의 음성을 그대로 받아쓴 스크립트입니다. 이 내용을 분석해서 회의록에 쓸 수 있도록 요약해줘.

반드시 아래 JSON 스키마 그대로, 다른 설명 없이 JSON 객체 하나만 출력해.

{{
  "meeting_title": "회의명 (스크립트 내용을 바탕으로 추론)",
  "meeting_date": "YYYY-MM-DD (스크립트에 날짜 언급이 없으면 빈 문자열)",
  "attendees": ["참석자1", "참석자2"],
  "agenda": ["안건1", "안건2"],
  "discussion_summary": "회의 논의 내용을 문단으로 요약",
  "decisions": ["결정사항1", "결정사항2"],
  "action_items": [
    {{"task": "액션 아이템 내용", "owner": "담당자", "due_date": "YYYY-MM-DD 또는 빈 문자열"}}
  ]
}}

스크립트:
---
{transcript}
---
"""


def _extract_json(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"Claude 응답에서 JSON을 찾지 못했습니다: {text!r}")
    return json.loads(match.group(0))


def _as_list(value) -> list:
    """Claude sometimes returns a comma-separated string instead of a JSON
    array for list fields; normalize either shape into a list of strings."""
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        return [v.strip() for v in value.split(",") if v.strip()]
    return []


def summarize_meeting(transcript: str, api_key: str, model: str) -> dict:
    """Summarize a meeting transcript into a structured dict using Claude."""
    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model=model,
        max_tokens=4000,
        messages=[{"role": "user", "content": SUMMARY_PROMPT.format(transcript=transcript)}],
    )
    text = "".join(block.text for block in message.content if block.type == "text")
    data = _extract_json(text)

    data["attendees"] = _as_list(data.get("attendees"))
    data["agenda"] = _as_list(data.get("agenda"))
    data["decisions"] = _as_list(data.get("decisions"))
    if not isinstance(data.get("action_items"), list):
        data["action_items"] = []

    return data
