import os
import mimetypes
from typing import List, Dict, Any, Tuple
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()


def format_seconds(seconds: float) -> str:
    """초를 MM:SS 형식(1시간 이상이면 HH:MM:SS)으로 변환합니다."""
    total_sec = int(seconds)
    hours = total_sec // 3600
    minutes = (total_sec % 3600) // 60
    secs = total_sec % 60
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def parse_offset_seconds(offset_str: str) -> float:
    """'1.200s' 형태의 문자열을 float 초 단위로 변환합니다."""
    if not offset_str:
        return 0.0
    return float(str(offset_str).replace("s", "").strip())


def transcribe_with_timestamps(
    audio_path: str,
    api_key: str = None,
) -> Dict[str, Any]:
    """
    Google Gemini 3.5 Flash Transcribe 모델(gemini-3.5-transcribe)을 사용하여
    오디오에서 전체 텍스트와 세그먼트별 타임스탬프 데이터를 추출합니다.

    Returns:
        {
            "full_text": str,
            "segments": [
                {
                    "start": float,
                    "end": float,
                    "time_str": str,
                    "text": str,
                    "speaker": str
                }, ...
            ],
            "raw_words": [...]
        }
    """
    key = api_key or os.environ.get("GEMINI_API_KEY")
    if not key:
        raise ValueError("GEMINI_API_KEY가 설정되지 않았습니다.")

    client = genai.Client(api_key=key)

    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"오디오 파일을 찾을 수 없습니다: {audio_path}")

    mime_type, _ = mimetypes.guess_type(audio_path)
    if not mime_type:
        mime_type = "audio/m4a"

    file_size = os.path.getsize(audio_path)
    uploaded_file = None

    try:
        # 20MB 기준 분기 (20MB 미만은 빠른 인라인, 초과는 File API)
        if file_size < 20 * 1024 * 1024:
            with open(audio_path, "rb") as f:
                audio_bytes = f.read()
            audio_part = types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)
        else:
            uploaded_file = client.files.upload(file=audio_path)
            audio_part = types.Part.from_uri(
                file_uri=uploaded_file.uri,
                mime_type=uploaded_file.mime_type or mime_type,
            )

        contents = [
            types.Content(
                role="user",
                parts=[
                    audio_part,
                    types.Part.from_text(text="음성을 텍스트로 정확히 전사해줘."),
                ],
            )
        ]

        # gemini-3.5-transcribe 전용 설정
        config = types.GenerateContentConfig(
            audio_transcription_config=types.AudioTranscriptionConfig(
                word_timestamp=True,
                diarization=True,
            )
        )

        response = client.models.generate_content(
            model="gemini-3.5-transcribe",
            contents=contents,
            config=config,
        )

        full_text = response.text or ""
        segments = []
        raw_words = []

        # 타임스탬프 정보 추출 및 세그먼트(문장 단위) 병합
        candidates = getattr(response, "candidates", [])
        if candidates:
            for part in candidates[0].content.parts:
                transcription = getattr(part, "audio_transcription", None)
                if transcription:
                    words = getattr(transcription, "words", [])
                    speaker = getattr(transcription, "speaker_label", "화자")

                    # 단어들을 일정 시간 간격(약 3~5초 또는 구두점)으로 세그먼트화
                    curr_segment_words = []
                    curr_start = 0.0
                    curr_end = 0.0

                    for w in words:
                        word_text = getattr(w, "word", "")
                        start_sec = parse_offset_seconds(getattr(w, "start_offset", "0s"))
                        end_sec = parse_offset_seconds(getattr(w, "end_offset", "0s"))

                        raw_words.append({
                            "word": word_text,
                            "start": start_sec,
                            "end": end_sec,
                        })

                        if not curr_segment_words:
                            curr_start = start_sec

                        curr_segment_words.append(word_text)
                        curr_end = end_sec

                        # 4초 이상 지나거나 문장 부호(?, ., !)로 끝나면 하나의 세그먼트로 확정
                        is_punct = any(word_text.endswith(p) for p in [".", "?", "!"])
                        time_diff = curr_end - curr_start
                        if (is_punct and time_diff >= 1.5) or (time_diff >= 4.5):
                            seg_text = " ".join(curr_segment_words).strip()
                            segments.append({
                                "start": round(curr_start, 2),
                                "end": round(curr_end, 2),
                                "time_str": format_seconds(curr_start),
                                "text": seg_text,
                                "speaker": speaker,
                            })
                            curr_segment_words = []

                    # 남은 단어 처리
                    if curr_segment_words:
                        seg_text = " ".join(curr_segment_words).strip()
                        segments.append({
                            "start": round(curr_start, 2),
                            "end": round(curr_end, 2),
                            "time_str": format_seconds(curr_start),
                            "text": seg_text,
                            "speaker": speaker,
                        })

        # 세그먼트가 비어있을 경우 전체 텍스트로 기본 세그먼트 생성
        if not segments and full_text:
            segments.append({
                "start": 0.0,
                "end": 0.0,
                "time_str": "00:00",
                "text": full_text,
                "speaker": "전체",
            })

        return {
            "full_text": full_text,
            "segments": segments,
            "raw_words": raw_words,
        }

    finally:
        if uploaded_file:
            try:
                client.files.delete(name=uploaded_file.name)
            except Exception:
                pass
