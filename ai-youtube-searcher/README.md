# AI 유튜브 검색기 (AI YouTube Searcher) 🔍🎬

유튜브 영상 URL을 입력하면 실시간으로 영상을 로드하고, **Gemini 3.5 Flash Transcribe**를 통해 오디오에서 세부 타임스탬프와 대본을 추출하며, **Gemini 3.8 Flash**를 활용하여 영상 질의응답 및 **검색한 내용의 시간 위치로 즉시 점프하여 영상을 재생(Seek & Play)**하는 차세대 AI 미디어 검색 웹 서비스입니다.

---

## 🌟 핵심 기능

1. **유튜브 상단 검색바 레이아웃**:
   - 불필요한 부가 아이콘(마이크/만들기/알람)을 제거하고, 직관적인 유튜브 링크 입력창과 검색 버튼으로 구성
2. **맞춤형 YouTube IFrame 플레이어**:
   - **음향 크기(Volume) 조절**: 상단 슬라이더(0% ~ 100%)를 통해 영상 음량을 실시간 조절
   - **타임스탬프 원클릭 이동(Seek & Play)**: 검색한 발화 구간 클릭 시 플레이어가 해당 초(second)로 즉시 이동 및 자동 재생
3. **Gemini 3.5 Flash Transcribe (`gemini-3.5-transcribe`)**:
   - `word_timestamp` 및 `diarization`을 활성화하여 정확한 발화 시작 시간(초)과 문장 단위 타임라인 세그먼트 생성
4. **Gemini 3.8 Flash (`gemini-3.8-flash`) 질의응답**:
   - 영상의 전체 시간대별 대본을 바탕으로 사용자 질문에 명쾌하게 답하고, 관련된 영상의 타임스탬프를 함께 추출하여 자동으로 해당 시간대로 이동

---

## 📁 프로젝트 파일 구조

```
ai-youtube-searcher/
├── app.py                # Streamlit 기반 메인 웹 애플리케이션
├── downloader.py         # yt-dlp 기반 유튜브 비디오 정보 및 오디오 추출 모듈
├── transcribe_engine.py  # Gemini 3.5 Transcribe 타임스탬프 파싱 엔진
├── qa_engine.py          # Gemini 3.8 Flash 질의응답 및 타임스탬프 검색 엔진
├── requirements.txt      # 의존성 패키지 목록
└── README.md             # 상세 가이드 문서
```

---

## 🚀 빠른 시작 가이드

### 1. 패키지 설치 확인
기존 가상환경에 필요한 패키지(`streamlit`, `google-genai`, `yt-dlp`, `python-dotenv`)가 설치되어 있습니다.

```bash
pip install -r requirements.txt
```

### 2. 실행 방법
터미널에서 아래 명령어를 실행합니다:

```powershell
streamlit run e:\GoogleAiStudio-Tutorial\ai-youtube-searcher\app.py
```
*(기본 실행 포트: `http://localhost:8501`)*

---

## 💡 사용 시나리오

1. **상단 검색창에 유튜브 영상 주소 입력**
   - 예: `https://www.youtube.com/watch?v=...` 입력 후 **[🔍 검색 및 분석]** 클릭
2. **오디오 다운로드 및 Gemini 3.5 Transcribe가 자동으로 시간대별 대본을 추출**
3. **특정 내용 검색 및 즉시 점프**:
   - 우측의 **[🔎 특정 내용 검색 & 시간 이동]** 탭에서 찾고 싶은 키워드(예: *"사기꾼"*, *"날씨"*, *"가격"*)를 입력
   - 검색된 카드의 **[▶ 이동]** 버튼을 누르면, 좌측 플레이어가 해당 발화 시간대로 즉시 이동하고 재생 시작!
4. **Gemini 3.8 Flash 영상 Q&A**:
   - **[💬 Gemini 3.8 Flash 영상 Q&A]** 탭에서 영상 내용에 대해 질문하면 AI가 답변과 함께 관련 영상 위치를 안내합니다.
5. **음향 조절**:
   - 플레이어 상단의 **[음향 크기]** 슬라이더로 원하는 볼륨으로 조절 가능합니다.
