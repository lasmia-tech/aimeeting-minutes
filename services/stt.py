from pathlib import Path

from openai import OpenAI


def transcribe_audio(file_path: str | Path, api_key: str, language: str = "ko") -> str:
    """Transcribe an audio file to text using OpenAI's Whisper API."""
    client = OpenAI(api_key=api_key)
    with open(file_path, "rb") as f:
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=f,
            language=language,
        )
    return transcript.text
