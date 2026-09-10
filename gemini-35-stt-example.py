# To run this code you need to install the following dependencies:
# pip install google-genai python-dotenv

import os
import sys
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Windows 콘솔 한글 인코딩 깨짐 방지
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

# .env 파일에서 환경 변수 로드
load_dotenv()


def generate():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("[오류] GEMINI_API_KEY 환경변수가 설정되지 않았습니다.")
        print(".env 파일 또는 환경 변수에 API 키를 설정해주세요.")
        return

    audio_file_path = "output_news.wav"
    if not os.path.exists(audio_file_path):
        print(f"[오류] 오디오 파일을 찾을 수 없습니다: {audio_file_path}")
        return

    # 오디오 바이너리 파일 읽기
    with open(audio_file_path, "rb") as f:
        audio_bytes = f.read()

    client = genai.Client(api_key=api_key)

    model = "gemini-3.5-transcribe"
    contents = [
        types.Content(
            role="user",
            parts=[
                # 오디오 파일을 인라인 바이너리 파트로 전달
                types.Part.from_bytes(
                    data=audio_bytes,
                    mime_type="audio/wav",
                ),
                types.Part.from_text(text="음성을 텍스트로 변환해줘."),
            ],
        ),
    ]

    generate_content_config = types.GenerateContentConfig(
        audio_transcription_config=types.AudioTranscriptionConfig(
            word_timestamp=True,
            diarization=True,
        ),
    )

    print(f"[{audio_file_path}] 음성 텍스트 변환(STT) 진행 중...\n")

    for chunk in client.models.generate_content_stream(
        model=model,
        contents=contents,
        config=generate_content_config,
    ):
        if text := chunk.text:
            print(text, end="", flush=True)

    print("\n\n[완료] 음성 변환이 완료되었습니다.")


if __name__ == "__main__":
    generate()



