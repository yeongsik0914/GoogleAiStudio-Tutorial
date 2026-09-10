# Gemini 3.5 Transcribe STT (Speech-to-Text) 코드 라인별 해설

본 문서는 Google Gemini API의 음성 인식 모델(`gemini-3.5-transcribe`)을 사용하여 오디오 파일(`output_news.wav`)을 입력받아 한국어 텍스트 및 타임스탬프 정보로 전사(Transcription)하는 `gemini-35-stt-example.py` 코드의 **Line-by-Line 상세 해설서**입니다.

---

## 1. 전체 코드 구조 개요

이 코드는 다음과 같은 단계로 동작합니다:
1. **환경 설정 및 플랫폼 호환성 처리**: Windows 콘솔 한글 깨짐 방지(`utf-8` reconfigure) 및 `.env` 파일 로드
2. **사전 검증**: `GEMINI_API_KEY` 환경 변수 존재 여부 및 대상 오디오 파일(`output_news.wav`) 존재 여부 확인
3. **오디오 바이너리 로드**: WAV 파일을 바이너리 바이트(`rb`)로 읽어 `types.Part.from_bytes()`로 변환
4. **STT 설정 구성**: `AudioTranscriptionConfig`를 통한 단어 단위 타임스탬프(`word_timestamp=True`) 및 화자 분리(`diarization=True`) 옵션 활성화
5. **스트리밍 전사 수행**: `generate_content_stream`을 통해 모델로부터 변환되는 텍스트 청크를 실시간으로 콘솔에 출력

---

## 2. Line-by-Line 상세 분석

### [Lines 1 ~ 3] 의존성 주석
```python
1: # To run this code you need to install the following dependencies:
2: # pip install google-genai python-dotenv
3: 
```
- **Line 1-3**: 코드 실행에 필요한 핵심 라이브러리(`google-genai`, `python-dotenv`) 설치 안내 주석입니다.

---

### [Lines 4 ~ 15] 모듈 임포트 및 윈도우 UTF-8 / .env 설정
```python
4: import os
5: import sys
6: from dotenv import load_dotenv
7: from google import genai
8: from google.genai import types
9: 
10: # Windows 콘솔 한글 인코딩 깨짐 방지
11: if sys.platform == "win32":
12:     sys.stdout.reconfigure(encoding="utf-8")
13: 
14: # .env 파일에서 환경 변수 로드
15: load_dotenv()
```
- **Line 4 (`import os`)**: 파일 경로 검사(`os.path.exists`) 및 환경 변수 접근(`os.environ.get`)에 사용합니다.
- **Line 5 (`import sys`)**: 운영체제 판별 및 표준 출력(`stdout`) 인코딩 재구성에 사용합니다.
- **Line 6 (`from dotenv import load_dotenv`)**: `.env` 파일에 저장된 API 키를 환경 변수로 불러옵니다.
- **Line 7-8 (`from google import genai`, `from google.genai import types`)**: 최신 Google GenAI SDK의 클라이언트 및 전용 데이터 타입 클래스를 가져옵니다.
- **Line 11-12**: Windows OS 환경(`sys.platform == "win32"`)에서 기본 인코딩(CP949)으로 인해 터미널에 한글이 깨져 출력되는 문제를 방지하기 위해 표준 출력을 UTF-8로 재구성합니다.
- **Line 15 (`load_dotenv()`)**: 프로젝트 루트의 `.env` 파일을 찾아 환경 변수로 등록합니다.

---

### [Lines 18 ~ 28] `generate()`: 유효성 검증 및 입력 파일 확인
```python
18: def generate():
19:     api_key = os.environ.get("GEMINI_API_KEY")
20:     if not api_key:
21:         print("[오류] GEMINI_API_KEY 환경변수가 설정되지 않았습니다.")
22:         print(".env 파일 또는 환경 변수에 API 키를 설정해주세요.")
23:         return
24: 
25:     audio_file_path = "output_news.wav"
26:     if not os.path.exists(audio_file_path):
27:         print(f"[오류] 오디오 파일을 찾을 수 없습니다: {audio_file_path}")
28:         return
```
- **Line 19-23**: `GEMINI_API_KEY` 환경 변수가 누락되었을 경우, 오류 메시지를 표시하고 안전하게 종료합니다.
- **Line 25-28**: 전사할 오디오 파일(`output_news.wav`)의 실제 경로를 정의하고, 파일이 없을 경우 친절한 에러 메시지를 출력합니다.

---

### [Lines 30 ~ 34] 오디오 파일 로드 및 클라이언트 생성
```python
30:     # 오디오 바이너리 파일 읽기
31:     with open(audio_file_path, "rb") as f:
32:         audio_bytes = f.read()
33: 
34:     client = genai.Client(api_key=api_key)
```
- **Line 31-32**: `with open(..., "rb")`를 사용하여 WAV 오디오 파일을 순수 바이너리 바이트열(`bytes`)로 메모리에 로드합니다.
- **Line 34**: API 키를 기반으로 `genai.Client` 인스턴스를 생성합니다.

---

### [Lines 36 ~ 49] 모델 선택 및 멀티모달 컨텐츠 구성
```python
36:     model = "gemini-3.5-transcribe"
37:     contents = [
38:         types.Content(
39:             role="user",
40:             parts=[
41:                 # 오디오 파일을 인라인 바이너리 파트로 전달
42:                 types.Part.from_bytes(
43:                     data=audio_bytes,
44:                     mime_type="audio/wav",
45:                 ),
46:                 types.Part.from_text(text="음성을 텍스트로 변환해줘."),
47:             ],
48:         ),
49:     ]
```
- **Line 36 (`model = "gemini-3.5-transcribe"`)**: Google AI Studio의 전용 오디오 전사(STT) 모델을 지정합니다.
- **Line 42-45 (`types.Part.from_bytes(...)`)**: **핵심 입력 부분**입니다.
  - 읽어온 오디오 바이트(`audio_bytes`)와 포맷 정보(`mime_type="audio/wav"`)를 인라인 바이너리 Blob 파트로 패킹하여 모델에 직접 전달합니다.
- **Line 46 (`types.Part.from_text(...)`)**: 오디오와 함께 수행할 작업에 대한 텍스트 지시어(프롬프트)를 추가합니다.

---

### [Lines 51 ~ 56] 오디오 전사 상세 설정 (AudioTranscriptionConfig)
```python
51:     generate_content_config = types.GenerateContentConfig(
52:         audio_transcription_config=types.AudioTranscriptionConfig(
53:             word_timestamp=True,
54:             diarization=True,
55:         ),
56:     )
```
- **Line 52-55**: STT 전용 고급 설정을 활성화합니다.
  - `word_timestamp=True`: 각 단어가 오디오의 몇 초(start_offset ~ end_offset)에 발화되었는지 단어별 타임스탬프를 계산하도록 요청합니다.
  - `diarization=True`: 화자 분리(Speaker Diarization)를 켜서 발화자가 여러 명일 때 누가 말했는지(예: `spk:0`, `spk:1`)를 식별하도록 지시합니다.

---

### [Lines 58 ~ 68] 스트리밍 수신 및 실시간 출력
```python
58:     print(f"[{audio_file_path}] 음성 텍스트 변환(STT) 진행 중...\n")
59: 
60:     for chunk in client.models.generate_content_stream(
61:         model=model,
62:         contents=contents,
63:         config=generate_content_config,
64:     ):
65:         if text := chunk.text:
66:             print(text, end="", flush=True)
67: 
68:     print("\n\n[완료] 음성 변환이 완료되었습니다.")
```
- **Line 60-64**: `generate_content_stream`을 호출하여 변환 결과를 실시간 스트리밍으로 전달받습니다.
- **Line 65-66**: `chunk.text`에 들어오는 텍스트 조각들을 버퍼 없이 즉시 콘솔에 스트리밍 출력(`flush=True`)합니다.
- **Line 68**: 전사가 끝나면 완료 메시지를 출력합니다.

---

### [Lines 71 ~ 73] 스크립트 실행 진입점
```python
71: if __name__ == "__main__":
72:     generate()
```
- **Line 71-72**: 스크립트가 직접 실행될 때 `generate()` 함수를 호출합니다.
