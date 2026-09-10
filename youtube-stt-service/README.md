# YouTube Audio Downloader & Gemini STT Web Service 🎙️

유튜브 영상 URL을 입력하면 원본 오디오 스트림(m4a)을 추출/다운로드하고, Google Gemini API의 최신 음성 인식 모델(`gemini-3.5-transcribe` / `gemini-3.6-flash`)을 통해 정확한 한국어/다국어 텍스트 트랜스크립트를 추출하는 웹 서비스입니다.

---

## 🌟 주요 기능

1. **유튜브 고음질 오디오 추출 (`yt-dlp`)**:
   - 별도의 FFmpeg 설치 없이도 유튜브의 원본 m4a 오디오 스트림을 손실 없이 빠르게 다운로드합니다.
2. **Gemini 음성 인식 (STT)**:
   - 최신 전용 모델인 `gemini-3.5-transcribe` 및 `gemini-3.6-flash` 지원
   - 대용량 오디오(수십 분 이상의 긴 영상)도 Gemini File API를 통해 안정적으로 처리
3. **인터랙티브 웹 대시보드 (`Streamlit`)**:
   - 원본 유튜브 영상 임베드 및 다운로드된 오디오 실시간 웹 재생기(`st.audio`)
   - 진행 상태 시각화 (다운로드 ➔ AI 전사 ➔ 결과 생성)
   - 트랜스크립트 텍스트 파일(`.txt`) 1클릭 다운로드
   - **AI 3줄 핵심 요약** 기능 내장

---

## 📁 프로젝트 구조

```
youtube-stt-service/
├── app.py              # Streamlit 메인 웹 애플리케이션
├── downloader.py       # yt-dlp 기반 유튜브 오디오 다운로더 모듈
├── transcriber.py      # Google GenAI SDK 기반 음성 전사 모듈
├── requirements.txt    # 의존성 패키지 목록
├── README.md           # 사용 설명서
└── downloads/          # 다운로드된 오디오 임시 저장 디렉터리
```

---

## 🚀 빠른 시작 가이드

### 1. 패키지 설치
프로젝트 루트 또는 현재 가상환경에서 의존성 패키지를 설치합니다:

```bash
pip install -r requirements.txt
```

### 2. API 키 설정
루트 디렉터리의 `.env` 파일에 Gemini API 키가 설정되어 있으면 자동으로 불러옵니다:
```text
GEMINI_API_KEY=AIzaSy...본인의_API_키
```
*(웹 브라우저의 사이드바 메뉴에서도 직접 API 키를 입력하거나 변경할 수 있습니다.)*

### 3. 웹 서비스 실행
터미널에서 아래 명령어를 실행하면 브라우저에서 서비스가 열립니다:

```bash
streamlit run app.py
```
*(기본 주소: `http://localhost:8501`)*

---

## 💡 사용 방법

1. 브라우저가 열리면 상단 입력창에 유튜브 영상 링크(예: `https://www.youtube.com/watch?v=...`)를 붙여넣습니다.
2. 사이드바에서 원하는 모델(`gemini-3.5-transcribe` 추천)과 프롬프트를 확인합니다.
3. **[🚀 변환 시작]** 버튼을 클릭합니다.
4. 다운로드가 완료되면 왼쪽에서 영상을 보고 추출된 오디오를 재생할 수 있으며, 오른쪽 텍스트 박스에 AI가 받아쓴 전체 스크립트가 나타납니다.
5. **[💾 텍스트 파일 다운로드]** 버튼을 눌러 소장하거나, **[⚡ AI 3줄 핵심 요약]**을 눌러 요약본을 확인할 수 있습니다.
