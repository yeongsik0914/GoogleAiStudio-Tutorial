import os
import mimetypes
from typing import Dict, Any, Generator, Tuple
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()


def get_client(api_key: str = None) -> genai.Client:
    """Gemini 클라이언트를 반환합니다."""
    key = api_key or os.environ.get("GEMINI_API_KEY")
    if not key:
        raise ValueError("GEMINI_API_KEY가 설정되지 않았습니다. .env 파일 또는 UI에서 입력해주세요.")
    return genai.Client(api_key=key)


def transcribe_audio_stream(
    audio_path: str,
    api_key: str = None,
    model_name: str = "gemini-3.5-transcribe",
    prompt: str = "이 오디오의 내용을 한국어로 정확하게 받아쓰기(전사)해줘.",
) -> Generator[str, None, Dict[str, Any]]:
    """
    오디오 파일을 Gemini 모델에 업로드하고 스트리밍 방식으로 텍스트를 생성합니다.
    Generator로 실시간 텍스트 조각을 yield합니다.

    Returns (via Generator return):
        {"full_text": str, "file_name": str}
    """
    client = get_client(api_key)

    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"오디오 파일을 찾을 수 없습니다: {audio_path}")

    # MIME 타입 유추 (기본: audio/m4a 또는 audio/mp3)
    mime_type, _ = mimetypes.guess_type(audio_path)
    if not mime_type:
        mime_type = "audio/m4a"

    # 파일 크기 확인 (20MB 미만이면 빠른 인라인 전송, 초과 시 File API 사용)
    file_size = os.path.getsize(audio_path)
    uploaded_file = None

    try:
        if file_size < 20 * 1024 * 1024:
            # 20MB 미만: Part.from_bytes로 즉시 전송
            with open(audio_path, "rb") as f:
                audio_bytes = f.read()
            audio_part = types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)
        else:
            # 20MB 이상: File API 업로드 (대용량 안전 처리)
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
                    types.Part.from_text(text=prompt),
                ],
            )
        ]

        # STT 모델 설정
        if "transcribe" in model_name:
            config = types.GenerateContentConfig(
                audio_transcription_config=types.AudioTranscriptionConfig(
                    word_timestamp=True,
                    diarization=True,
                )
            )
        else:
            config = types.GenerateContentConfig(
                temperature=0.2,
            )

        full_text = []
        for chunk in client.models.generate_content_stream(
            model=model_name,
            contents=contents,
            config=config,
        ):
            if chunk.text:
                full_text.append(chunk.text)
                yield chunk.text

        return {
            "full_text": "".join(full_text),
        }

    finally:
        # File API에 업로드된 임시 파일이 있다면 삭제 정리
        if uploaded_file:
            try:
                client.files.delete(name=uploaded_file.name)
            except Exception:
                pass


def transcribe_audio_full(
    audio_path: str,
    api_key: str = None,
    model_name: str = "gemini-3.5-transcribe",
    prompt: str = "이 오디오의 내용을 한국어로 정확하게 받아쓰기(전사)해줘.",
) -> Dict[str, Any]:
    """
    단일 호출로 전체 트랜스크립트 및 상세 정보(타임스탬프 포함)를 가져옵니다.
    """
    client = get_client(api_key)

    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"오디오 파일을 찾을 수 없습니다: {audio_path}")

    mime_type, _ = mimetypes.guess_type(audio_path)
    if not mime_type:
        mime_type = "audio/m4a"

    file_size = os.path.getsize(audio_path)
    uploaded_file = None

    try:
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
                    types.Part.from_text(text=prompt),
                ],
            )
        ]

        if "transcribe" in model_name:
            config = types.GenerateContentConfig(
                audio_transcription_config=types.AudioTranscriptionConfig(
                    word_timestamp=True,
                    diarization=True,
                )
            )
        else:
            config = types.GenerateContentConfig(
                temperature=0.2,
            )

        response = client.models.generate_content(
            model=model_name,
            contents=contents,
            config=config,
        )

        # 타임스탬프 정보 추출
        timestamps = []
        full_text = response.text or ""

        try:
            candidates = getattr(response, "candidates", [])
            if candidates:
                for part in candidates[0].content.parts:
                    transcription = getattr(part, "audio_transcription", None)
                    if transcription:
                        speaker = getattr(transcription, "speaker_label", "화자")
                        words = getattr(transcription, "words", [])
                        timestamps.append({
                            "speaker": speaker,
                            "text": getattr(transcription, "text", ""),
                            "words": [
                                {
                                    "word": getattr(w, "word", ""),
                                    "start": getattr(w, "start_offset", ""),
                                    "end": getattr(w, "end_offset", ""),
                                }
                                for w in words
                            ]
                        })
        except Exception:
            pass

        return {
            "text": full_text,
            "timestamps": timestamps,
        }

    finally:
        if uploaded_file:
            try:
                client.files.delete(name=uploaded_file.name)
            except Exception:
                pass
