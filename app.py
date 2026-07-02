from pathlib import Path
from tempfile import NamedTemporaryFile

import streamlit as st

from config import settings
from services.confluence import ConfluenceClient, build_storage_html
from services.excel_export import build_excel_fields, fill_template
from services.stt import transcribe_audio
from services.summarize import summarize_meeting

st.set_page_config(page_title="회의록 자동화", layout="wide")
st.title("회의록 자동화")

if "transcript" not in st.session_state:
    st.session_state.transcript = ""
if "summary" not in st.session_state:
    st.session_state.summary = None

st.header("1. 음성 업로드 → 텍스트 변환 + 요약")
audio_file = st.file_uploader("회의 음성 파일", type=["mp3", "wav", "m4a", "mp4", "webm"])

if st.button("텍스트 변환 + 요약 실행", disabled=audio_file is None):
    if not settings.openai_api_key or not settings.anthropic_api_key:
        st.error("OPENAI_API_KEY / ANTHROPIC_API_KEY가 .env에 설정되어 있어야 합니다.")
    else:
        with NamedTemporaryFile(delete=False, suffix=Path(audio_file.name).suffix) as tmp:
            tmp.write(audio_file.getvalue())
            tmp_path = tmp.name
        with st.spinner("음성을 텍스트로 변환하는 중..."):
            st.session_state.transcript = transcribe_audio(tmp_path, settings.openai_api_key)
        with st.spinner("회의 내용을 요약하는 중..."):
            st.session_state.summary = summarize_meeting(
                st.session_state.transcript, settings.anthropic_api_key, settings.anthropic_model
            )
        st.success("변환 및 요약이 완료되었습니다.")

if st.session_state.transcript:
    with st.expander("전체 스크립트 보기 / 직접 수정", expanded=True):
        st.session_state.transcript = st.text_area(
            "스크립트", st.session_state.transcript, height=200, label_visibility="collapsed"
        )
        if st.button("이 텍스트로 다시 요약"):
            if not settings.anthropic_api_key:
                st.error("ANTHROPIC_API_KEY가 .env에 설정되어 있어야 합니다.")
            else:
                with st.spinner("회의 내용을 요약하는 중..."):
                    st.session_state.summary = summarize_meeting(
                        st.session_state.transcript, settings.anthropic_api_key, settings.anthropic_model
                    )
                st.success("수정한 텍스트로 다시 요약했습니다.")

summary = st.session_state.summary
if summary:
    st.header("2. 요약 내용 확인/수정")
    summary["meeting_title"] = st.text_input("회의명", summary.get("meeting_title", ""))
    summary["meeting_date"] = st.text_input("일시 (YYYY-MM-DD)", summary.get("meeting_date", ""))
    attendees_text = st.text_area("참석자 (쉼표로 구분)", ", ".join(summary.get("attendees", [])))
    summary["attendees"] = [a.strip() for a in attendees_text.split(",") if a.strip()]

    agenda_text = st.text_area("안건 (한 줄에 하나씩)", "\n".join(summary.get("agenda", [])))
    summary["agenda"] = [a.strip() for a in agenda_text.splitlines() if a.strip()]

    summary["discussion_summary"] = st.text_area(
        "논의 내용 요약", summary.get("discussion_summary", ""), height=150
    )

    decisions_text = st.text_area("결정 사항 (한 줄에 하나씩)", "\n".join(summary.get("decisions", [])))
    summary["decisions"] = [d.strip() for d in decisions_text.splitlines() if d.strip()]

    action_items = st.data_editor(
        summary.get("action_items", []),
        num_rows="dynamic",
        column_config={
            "task": "내용",
            "owner": "담당자",
            "due_date": "기한",
        },
    )
    summary["action_items"] = action_items

    st.header("3. 회의 기본 정보 입력")
    col1, col2, col3 = st.columns(3)
    project_name = col1.text_input("프로젝트명", "차세대 프로젝트")
    project_phase = col2.text_input("프로젝트단계", "")
    activity_name = col3.text_input("활동명", "")
    col4, col5 = st.columns(2)
    meeting_location = col4.text_input("회의장소", "")
    organizer = col5.text_input("주관사", "")

    fields = build_excel_fields(summary, project_name, project_phase, activity_name, meeting_location, organizer)

    st.header("4. 엑셀 회의록 생성")
    if st.button("엑셀 파일 생성"):
        try:
            output_path = fill_template(
                fields,
                settings.excel_template_path,
                settings.excel_field_map_path,
                f"output/{summary['meeting_title'] or 'meeting'}_{summary['meeting_date'] or ''}.xlsx",
            )
            with open(output_path, "rb") as f:
                st.download_button("엑셀 파일 다운로드", f, file_name=Path(output_path).name)
        except FileNotFoundError as e:
            st.error(
                f"엑셀 양식 파일 또는 필드 매핑 파일을 찾을 수 없습니다: {e}. "
                f"templates/ 폴더에 회의록 양식 파일과 field_map.json을 준비해주세요."
            )

    st.header("5. 컨플루언스에 회의록 페이지 생성")
    if st.button("컨플루언스에 게시"):
        required = [
            settings.confluence_base_url,
            settings.confluence_email,
            settings.confluence_api_token,
            settings.confluence_space_key,
        ]
        if not all(required):
            st.error("컨플루언스 접속 정보(.env의 CONFLUENCE_* 값)가 모두 설정되어야 합니다.")
        elif not fields["meeting_date"].strip() or not fields["meeting_title"].strip():
            st.error("페이지 제목은 '회의일시_회의명'으로 생성됩니다. 위의 '일시'와 '회의명' 항목을 먼저 채워주세요.")
        else:
            try:
                client = ConfluenceClient(
                    settings.confluence_base_url, settings.confluence_email, settings.confluence_api_token
                )
                title = f"{fields['meeting_date'].strip()}_{fields['meeting_title'].strip()}"
                html_body = build_storage_html(fields)
                result = client.create_child_page(
                    settings.confluence_space_key,
                    settings.confluence_parent_page_title,
                    title,
                    html_body,
                )
                page_link = f"{settings.confluence_base_url}{result['_links']['webui']}"
                st.success(f"페이지가 생성되었습니다: {page_link}")
            except Exception as e:
                st.error(f"컨플루언스 페이지 생성에 실패했습니다: {e}")
