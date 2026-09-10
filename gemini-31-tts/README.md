# Gemini 3.1 Flash TTS (Text-to-Speech) 코드 라인별 해설

본 문서는 Google Gemini API의 음성 합성 모델(`gemini-3.1-flash-tts-preview`)을 사용하여 텍스트와 음성 지시어(Audio Tags)를 자연스러운 음성(WAV 파일)으로 변환하는 `gemini-31-tts-example.py` 코드의 **Line-by-Line 상세 해설서**입니다.

---

## 1. 전체 코드 구조 개요

이 코드는 다음과 같은 단계로 동작합니다:
1. **라이브러리 및 환경 변수 로드**: Google GenAI SDK 및 `.env` 설정 로드
2. **WAV 변환 헬퍼 함수 정의**: 모델이 반환하는 Raw PCM(L16) 바이트 스트림에 표준 RIFF WAV 헤더를 생성하여 결합
3. **MIME 타입 파서 정의**: `audio/L16;rate=24000` 형태의 MIME 문자열에서 샘플링 레이트와 비트 심도 추출
4. **`generate()` 메인 로직**:
   - `GEMINI_API_KEY` 검증 및 클라이언트 초기화
   - 모델 지정(`gemini-3.1-flash-tts-preview`) 및 음성 프롬프트(`Scene`, `Context`, `Transcript`) 설정
   - 음성 출력 설정(`response_modalities=["audio"]`, 음성 모델 `voice_name="Kore"`)
   - 스트리밍 응답(`generate_content_stream`)으로부터 오디오 바이트를 누적 버퍼에 수집
   - 최종 누적된 오디오 데이터를 WAV 포맷으로 변환하여 `gemini_4_0_pro_news.wav` 단일 파일로 저장

---

## 2. Line-by-Line 상세 분석

### [Lines 1 ~ 3] 의존성 주석
```python
1: # To run this code you need to install the following dependencies:
2: # pip install google-genai python-dotenv
3: 
```
- **Line 1-3**: 이 코드를 실행하기 위해 필요한 패키지(`google-genai`, `python-dotenv`) 설치 안내 주석입니다.

---

### [Lines 4 ~ 12] 모듈 임포트 및 환경 변수 로드
```python
4: import mimetypes
5: import os
6: import struct
7: from dotenv import load_dotenv
8: from google import genai
9: from google.genai import types
10: 
11: # .env 파일이 있다면 환경 변수 로드
12: load_dotenv()
```
- **Line 4 (`import mimetypes`)**: 파일 확장자 추론 모듈입니다. API 응답의 `mime_type`을 기반으로 적절한 확장자(예: `.wav`)를 유추할 때 사용합니다.
- **Line 5 (`import os`)**: 파일 경로 탐색 및 시스템 환경 변수(`GEMINI_API_KEY`)를 읽기 위한 모듈입니다.
- **Line 6 (`import struct`)**: 파이썬 데이터를 C 구조체 형태의 바이너리 바이트열로 패킹/언패킹하는 모듈입니다. WAV 파일 규격에 맞는 44바이트 헤더를 바이너리로 빌드할 때 사용됩니다.
- **Line 7 (`from dotenv import load_dotenv`)**: 프로젝트 폴더의 `.env` 파일에 기록된 환경 변수를 `os.environ`으로 로드해주는 함수를 가져옵니다.
- **Line 8-9 (`from google import genai`, `from google.genai import types`)**: 구글의 최신 GenAI 파이썬 SDK 및 관련 데이터 타입 클래스를 가져옵니다.
- **Line 12 (`load_dotenv()`)**: 현재 작업 디렉터리의 `.env` 파일을 읽어 시스템 환경 변수로 등록합니다.

---

### [Lines 15 ~ 20] 파일 저장 헬퍼 함수
```python
15: def save_binary_file(file_name: str, data: bytes):
16:     """바이너리 데이터를 파일로 저장합니다."""
17:     with open(file_name, "wb") as f:
18:         f.write(data)
19:     print(f"\n[성공] 음성 파일이 성공적으로 저장되었습니다: {os.path.abspath(file_name)}")
```
- **Line 15**: 함수 정의. 파일명(`file_name`)과 바이너리 데이터(`data`)를 매개변수로 받습니다.
- **Line 17-18**: 바이너리 쓰기(`"wb"`) 모드로 파일을 열고 데이터를 기록합니다. `with` 문을 사용하여 작업 완료 후 파일 핸들이 안전하게 닫힙니다.
- **Line 19**: 파일이 저장된 절대 경로(`os.path.abspath`)를 콘솔에 출력합니다.

---

### [Lines 22 ~ 50] PCM을 WAV 파일로 변환하는 함수
```python
22: def convert_to_wav(audio_data: bytes, mime_type: str) -> bytes:
23:     """PCM 오디오 데이터에 WAV 파일 헤더를 생성하여 추가합니다."""
24:     parameters = parse_audio_mime_type(mime_type)
25:     bits_per_sample = parameters["bits_per_sample"] or 16
26:     sample_rate = parameters["rate"] or 24000
27:     num_channels = 1
28:     data_size = len(audio_data)
29:     bytes_per_sample = bits_per_sample // 8
30:     block_align = num_channels * bytes_per_sample
31:     byte_rate = sample_rate * block_align
32:     chunk_size = 36 + data_size  # 36 bytes for header fields before data chunk size
```
- **Line 22**: 생 오디오 바이트열(`audio_data`)과 `mime_type`을 받아 표준 WAV 포맷 바이트를 반환하는 함수입니다.
- **Line 24-26**: `parse_audio_mime_type`을 통해 비트 심도(기본 16bit)와 샘플레이트(기본 24,000Hz)를 추출합니다.
- **Line 27 (`num_channels = 1`)**: Gemini TTS 모델의 기본 오디오 채널은 단일 채널(Mono, 1)입니다.
- **Line 28 (`data_size = len(audio_data)`)**: 실제 전달받은 RAW PCM 오디오 데이터의 전체 바이트 크기입니다.
- **Line 29 (`bytes_per_sample`)**: 샘플당 바이트 수 (16비트 = 2바이트).
- **Line 30 (`block_align`)**: 블록 정렬 단위 (`num_channels * bytes_per_sample` = 1 * 2 = 2바이트).
- **Line 31 (`byte_rate`)**: 초당 전송 바이트 수 (`sample_rate * block_align` = 24000 * 2 = 48,000 bytes/sec).
- **Line 32 (`chunk_size`)**: 전체 파일 크기에서 RIFF 헤더 8바이트를 뺀 크기 (`36 + data_size`).

```python
34:     header = struct.pack(
35:         "<4sI4s4sIHHIIHH4sI",
36:         b"RIFF",          # ChunkID
37:         chunk_size,       # ChunkSize (total file size - 8 bytes)
38:         b"WAVE",          # Format
39:         b"fmt ",          # Subchunk1ID
40:         16,               # Subchunk1Size (16 for PCM)
41:         1,                # AudioFormat (1 for PCM)
42:         num_channels,     # NumChannels
43:         sample_rate,      # SampleRate
44:         byte_rate,        # ByteRate
45:         block_align,      # BlockAlign
46:         bits_per_sample,  # BitsPerSample
47:         b"data",          # Subchunk2ID
48:         data_size         # Subchunk2Size (size of audio data)
49:     )
50:     return header + audio_data
```
- **Line 34-49**: `struct.pack("<4sI4s4sIHHIIHH4sI", ...)`을 사용하여 표준 44바이트 RIFF/WAVE 헤더를 바이너리로 패킹합니다.
  - `<`: 리틀 엔디언(Little-Endian) 바이트 순서 지정
  - `4s`: 4바이트 문자열 (`b"RIFF"`, `b"WAVE"`, `b"fmt "`, `b"data"`)
  - `I`: 부호 없는 32비트 정수 (4바이트)
  - `H`: 부호 없는 16비트 정수 (2바이트)
- **Line 50**: 44바이트 WAV 헤더 뒤에 원본 PCM 오디오 데이터를 결합하여 최종 반환합니다.

---

### [Lines 53 ~ 75] MIME 타입 파싱 함수
```python
53: def parse_audio_mime_type(mime_type: str) -> dict[str, int | None]:
54:     """MIME 타입 문자열에서 bits_per_sample과 rate(샘플 레이트)를 추출합니다."""
55:     bits_per_sample = 16
56:     rate = 24000
57: 
58:     if not mime_type:
59:         return {"bits_per_sample": bits_per_sample, "rate": rate}
```
- **Line 53-59**: MIME 문자열(예: `audio/L16;rate=24000`)을 파싱하여 기본값(16bit, 24000Hz)을 설정하고 비어있으면 기본값을 반환합니다.

```python
61:     parts = mime_type.split(";")
62:     for param in parts:
63:         param = param.strip()
64:         if param.lower().startswith("rate="):
65:             try:
66:                 rate = int(param.split("=", 1)[1])
67:             except (ValueError, IndexError):
68:                 pass
69:         elif param.lower().startswith("audio/l"):
70:             try:
71:                 bits_per_sample = int(param.split("L", 1)[1])
72:             except (ValueError, IndexError):
73:                 pass
74: 
75:     return {"bits_per_sample": bits_per_sample, "rate": rate}
```
- **Line 61-75**: 세미콜론(`;`)으로 구분된 파라미터들을 순회하며 `rate=` 값과 `audio/L16` 같은 비트 심도 값을 파싱하여 딕셔너리로 반환합니다.

---

### [Lines 78 ~ 86] `generate()`: API 키 확인 및 클라이언트 초기화
```python
78: def generate():
79:     api_key = os.environ.get("GEMINI_API_KEY")
80:     if not api_key:
81:         print("[오류] GEMINI_API_KEY 환경변수가 설정되지 않았습니다.")
82:         print("1. 프로젝트 폴더에 .env 파일을 만들고 GEMINI_API_KEY=your_api_key_here 를 입력하거나,")
83:         print("2. 터미널에서 $env:GEMINI_API_KEY=\"your_key\" (PowerShell 기준) 를 설정해주세요.")
84:         return
85: 
86:     client = genai.Client(api_key=api_key)
```
- **Line 79-84**: 환경 변수 `GEMINI_API_KEY`를 검사하고, 설정되지 않았을 경우 프로그램이 비정상 종료(Crash)되는 대신 친절한 설정 가이드를 출력하고 안전하게 리턴합니다.
- **Line 86**: GenAI SDK 클라이언트를 생성합니다.

---

### [Lines 88 ~ 109] 모델 및 TTS 프롬프트 설정
```python
88:     model = "gemini-3.1-flash-tts-preview"
89:     contents = [
90:         types.Content(
91:             role="user",
92:             parts=[
93:                 types.Part.from_text(text="""## Scene:
94: A professional tech newsroom studio, breaking news broadcast, confident and authoritative anchor tone.
95: 
96: ## Sample Context:
97: The anchor is delivering a sudden breaking news update to the viewers.
98: 
99: ## Transcript:
100: [breaking news] [excited] 긴급 속보입니다! 구글이 차세대 플래그십 모델, '제미나이 4.0 프로'를 전격 공개했습니다. 
...
106: [confident] 지금 바로 구글 AI 스튜디오에서 만나보실 수 있습니다."""),
107:             ],
108:         ),
109:     ]
```
- **Line 88 (`model`)**: Google AI Studio의 TTS 전용 모델인 `gemini-3.1-flash-tts-preview`를 지정합니다.
- **Line 93-106**: 프롬프트 구조화:
  - `## Scene:` : 녹음 환경과 배경 설정(전문 뉴스룸 스튜디오, 뉴스 보도 스타일)
  - `## Sample Context:` : 이전 맥락(시청자에게 긴급 속보를 전달하는 상황)
  - `## Transcript:` : 실제 발화 대사. `[breaking news]`, `[excited]`, `[astonished]`, `[serious]`, `[pause]`, `[confident]` 등의 오디오 감정/억양 태그가 포함되어 음성의 억양과 분위기를 모델이 직접 연출하도록 유도합니다.

---

### [Lines 111 ~ 121] 음성 생성 설정(Config)
```python
111:     generate_content_config = types.GenerateContentConfig(
112:         temperature=1,
113:         response_modalities=["audio"],
114:         speech_config=types.SpeechConfig(
115:             voice_config=types.VoiceConfig(
116:                 prebuilt_voice_config=types.PrebuiltVoiceConfig(
117:                     voice_name="Kore"
118:                 )
119:             )
120:         ),
121:     )
```
- **Line 113 (`response_modalities=["audio"]`)**: 모델에게 텍스트가 아닌 **오디오(음성 바이너리)** 형태로 응답을 생성하도록 지정합니다.
- **Line 114-120 (`speech_config`)**: TTS 보이스(목소리) 설정. 사전 정의된 음성 중 `"Kore"` 보이스를 선택합니다.

---

### [Lines 123 ~ 151] 오디오 스트리밍 수신 및 버퍼링
```python
123:     print("음성 생성 중... 잠시만 기다려주세요.")
124:     
125:     audio_buffer = bytearray()
126:     detected_mime_type = "audio/L16;rate=24000"
127:     
128:     for chunk in client.models.generate_content_stream(
129:         model=model,
130:         contents=contents,
131:         config=generate_content_config,
132:     ):
133:         if not chunk.parts:
134:             continue
135:             
136:         for part in chunk.parts:
137:             # 텍스트 응답이 올 경우 출력
138:             if getattr(part, "text", None):
139:                 print(part.text, end="", flush=True)
140: 
141:             # 오디오 데이터가 올 경우 버퍼에 모으기
142:             inline_data = getattr(part, "inline_data", None)
143:             if inline_data and inline_data.data:
144:                 audio_buffer.extend(inline_data.data)
145:                 if inline_data.mime_type:
146:                     detected_mime_type = inline_data.mime_type
147:                 print(".", end="", flush=True)
```
- **Line 125 (`audio_buffer = bytearray()`)**: 스트리밍으로 전달되는 여러 개의 조각 데이터(청크)를 하나로 합치기 위한 가변 바이트 버퍼입니다.
- **Line 128 (`generate_content_stream`)**: 음성을 실시간 스트리밍으로 수신합니다.
- **Line 133-134**: 청크에 파트가 없을 경우 `IndexError`를 방지하기 위해 안전하게 건너뜁니다.
- **Line 142-147**: `part.inline_data.data`에 도착한 RAW PCM 바이트 조각들을 `audio_buffer.extend()`로 계속 이어붙이고, 진행 표시 점(`.`)을 찍습니다.

---

### [Lines 153 ~ 166] 최종 단일 파일 변환 및 저장
```python
153:     # 파일명 지정 및 최종 WAV 변환 저장
154:     output_filename = "gemini_4_0_pro_news.wav"
155:     file_ext = mimetypes.guess_extension(detected_mime_type)
156:     
157:     if file_ext == ".wav" or "audio/l" in detected_mime_type.lower() or file_ext is None:
158:         # PCM RAW 스트림에 WAV 헤더를 붙여 온전한 파일 1개로 생성
159:         final_audio = convert_to_wav(bytes(audio_buffer), detected_mime_type)
160:         output_filename = "gemini_4_0_pro_news.wav"
161:     else:
162:         final_audio = bytes(audio_buffer)
163:         output_filename = f"gemini_4_0_pro_news{file_ext}"
164: 
165:     save_binary_file(output_filename, final_audio)
```
- **Line 157-160**: 모아둔 전체 오디오 데이터에 대해 단 **한 번만** `convert_to_wav()`를 호출하여 완성된 44바이트 WAV 헤더를 씌웁니다. 이를 통해 조각난 파일이 아닌 **온전한 단 하나의 `gemini_4_0_pro_news.wav` 파일**이 완성됩니다.
- **Line 165**: `save_binary_file`을 통해 디스크에 파일을 씁니다.

---

### [Lines 168 ~ 170] 스크립트 실행 진입점
```python
168: if __name__ == "__main__":
169:     generate()
```
- **Line 168-169**: 파이썬 인터프리터에서 직접 실행되었을 때 `generate()` 함수를 호출합니다.
