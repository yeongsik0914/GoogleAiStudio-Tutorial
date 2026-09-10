# To run this code you need to install the following dependencies:
# pip install google-genai python-dotenv

import mimetypes
import os
import struct
from dotenv import load_dotenv
from google import genai
from google.genai import types

# .env 파일이 있다면 환경 변수 로드
load_dotenv()


def save_binary_file(file_name: str, data: bytes):
    """바이너리 데이터를 파일로 저장합니다."""
    with open(file_name, "wb") as f:
        f.write(data)
    print(f"\n[성공] 음성 파일이 성공적으로 저장되었습니다: {os.path.abspath(file_name)}")


def convert_to_wav(audio_data: bytes, mime_type: str) -> bytes:
    """PCM 오디오 데이터에 WAV 파일 헤더를 생성하여 추가합니다."""
    parameters = parse_audio_mime_type(mime_type)
    bits_per_sample = parameters["bits_per_sample"] or 16
    sample_rate = parameters["rate"] or 24000
    num_channels = 1
    data_size = len(audio_data)
    bytes_per_sample = bits_per_sample // 8
    block_align = num_channels * bytes_per_sample
    byte_rate = sample_rate * block_align
    chunk_size = 36 + data_size  # 36 bytes for header fields before data chunk size

    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",          # ChunkID
        chunk_size,       # ChunkSize (total file size - 8 bytes)
        b"WAVE",          # Format
        b"fmt ",          # Subchunk1ID
        16,               # Subchunk1Size (16 for PCM)
        1,                # AudioFormat (1 for PCM)
        num_channels,     # NumChannels
        sample_rate,      # SampleRate
        byte_rate,        # ByteRate
        block_align,      # BlockAlign
        bits_per_sample,  # BitsPerSample
        b"data",          # Subchunk2ID
        data_size         # Subchunk2Size (size of audio data)
    )
    return header + audio_data


def parse_audio_mime_type(mime_type: str) -> dict[str, int | None]:
    """MIME 타입 문자열에서 bits_per_sample과 rate(샘플 레이트)를 추출합니다."""
    bits_per_sample = 16
    rate = 24000

    if not mime_type:
        return {"bits_per_sample": bits_per_sample, "rate": rate}

    parts = mime_type.split(";")
    for param in parts:
        param = param.strip()
        if param.lower().startswith("rate="):
            try:
                rate = int(param.split("=", 1)[1])
            except (ValueError, IndexError):
                pass
        elif param.lower().startswith("audio/l"):
            try:
                bits_per_sample = int(param.split("L", 1)[1])
            except (ValueError, IndexError):
                pass

    return {"bits_per_sample": bits_per_sample, "rate": rate}


def generate():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("[오류] GEMINI_API_KEY 환경변수가 설정되지 않았습니다.")
        print("1. 프로젝트 폴더에 .env 파일을 만들고 GEMINI_API_KEY=your_api_key_here 를 입력하거나,")
        print("2. 터미널에서 $env:GEMINI_API_KEY=\"your_key\" (PowerShell 기준) 를 설정해주세요.")
        return

    client = genai.Client(api_key=api_key)

    model = "gemini-3.1-flash-tts-preview"
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text="""## Scene:
A professional tech newsroom studio, breaking news broadcast, confident and authoritative anchor tone.

## Sample Context:
The anchor is delivering a sudden breaking news update to the viewers.

## Transcript:
[breaking news] [excited] 긴급 속보입니다! 구글이 차세대 플래그십 모델, '제미나이 4.0 프로'를 전격 공개했습니다. 

[astonished] 놀라운 건 성능뿐만이 아닙니다. 이번 공개와 함께 발표된 이용 요금이 그야말로 AI 업계 전체를 충격에 빠뜨렸는데요. 

[serious] 기존 모델 대비 처리 속도는 열 배 이상 빨라졌음에도, API 가격은 거의 10분의 1 수준으로 폭락했습니다. [pause] 사실상 '공짜에 가깝다'는 평가까지 나오고 있습니다. 

[confident] 지금 바로 구글 AI 스튜디오에서 만나보실 수 있습니다."""),
            ],
        ),
    ]

    generate_content_config = types.GenerateContentConfig(
        temperature=1,
        response_modalities=["audio"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                    voice_name="Kore"
                )
            )
        ),
    )

    print("음성 생성 중... 잠시만 기다려주세요.")
    
    audio_buffer = bytearray()
    detected_mime_type = "audio/L16;rate=24000"
    
    for chunk in client.models.generate_content_stream(
        model=model,
        contents=contents,
        config=generate_content_config,
    ):
        if not chunk.parts:
            continue
            
        for part in chunk.parts:
            # 텍스트 응답이 올 경우 출력
            if getattr(part, "text", None):
                print(part.text, end="", flush=True)

            # 오디오 데이터가 올 경우 버퍼에 모으기
            inline_data = getattr(part, "inline_data", None)
            if inline_data and inline_data.data:
                audio_buffer.extend(inline_data.data)
                if inline_data.mime_type:
                    detected_mime_type = inline_data.mime_type
                print(".", end="", flush=True)

    if not audio_buffer:
        print("\n[알림] 생성된 오디오 데이터가 없습니다.")
        return

    # 파일명 지정 및 최종 WAV 변환 저장
    output_filename = "gemini_4_0_pro_news.wav"
    file_ext = mimetypes.guess_extension(detected_mime_type)
    
    if file_ext == ".wav" or "audio/l" in detected_mime_type.lower() or file_ext is None:
        # PCM RAW 스트림에 WAV 헤더를 붙여 온전한 파일 1개로 생성
        final_audio = convert_to_wav(bytes(audio_buffer), detected_mime_type)
        output_filename = "gemini_4_0_pro_news.wav"
    else:
        final_audio = bytes(audio_buffer)
        output_filename = f"gemini_4_0_pro_news{file_ext}"

    save_binary_file(output_filename, final_audio)


if __name__ == "__main__":
    generate()
