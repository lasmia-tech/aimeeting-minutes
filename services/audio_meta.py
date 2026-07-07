import re
from datetime import datetime

import mutagen

_DATE_RE = re.compile(r"(\d{4})[:\-](\d{2})[:\-](\d{2})")


def extract_recorded_date(file_path: str) -> str | None:
    """Try to read a recording date from the audio file's own metadata tags
    (ID3 TDRC, MP4 ©day, Vorbis DATE, etc.). Returns 'YYYY-MM-DD' or None if
    the file has no such tag."""
    try:
        audio = mutagen.File(file_path, easy=True)
    except Exception:
        return None
    if not audio or not audio.tags:
        return None

    for key in ("date", "originaldate", "creation_time", "year"):
        values = audio.tags.get(key)
        if not values:
            continue
        raw = str(values[0] if isinstance(values, list) else values)
        match = _DATE_RE.search(raw)
        if match:
            year, month, day = match.groups()
            return f"{year}-{month}-{day}"
    return None


def default_meeting_date(file_path: str) -> str:
    """Recording date from file metadata, falling back to today (upload time)
    since browser uploads don't carry the OS file-creation timestamp."""
    return extract_recorded_date(file_path) or datetime.now().strftime("%Y-%m-%d")
