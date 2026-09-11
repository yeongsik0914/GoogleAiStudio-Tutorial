# 🤖 Repository Guidelines & Agent Standards (AGENTS.md)

> **Universal Coding & Architecture Standards for AI Agents**  
> 이 문서는 본 저장소(`GoogleAiStudio-Tutorial`)에서 작업하는 모든 AI 코딩 에이전트(Antigravity, Cursor, Copilot, Codex, Claude 등)와 개발자를 위한 공식 아키텍처 및 코딩 표준 규격서입니다.

---

## 1. 프로젝트 개요 (Overview)

본 저장소는 **Google AI Studio 및 Gemini API 최신 모델**(Gemini 3.5 Transcribe, Gemini 2.5 Flash, Gemini 3.1 TTS 등)을 활용한 오디오/비디오 처리 및 AI 웹 애플리케이션 모음입니다.
- **주요 서브 프로젝트**:
  - `ai-youtube-searcher/`: 고도화된 유튜브 오디오 추출, 실시간 자막 싱크, 타임라인 인터랙션, Q&A 및 검색 웹 앱 (Streamlit + Custom Component)
  - `youtube-stt-service/`: 초고속 유튜브 오디오 다운로드 및 트랜스크립트 변환/요약 서비스 (Streamlit)
  - `gemini-31-tts/`: Gemini 3.1 음성 합성(TTS) CLI 예제
  - `gemini-35-stt/`: Gemini 3.5 음성 전사(STT) CLI 예제

---

## 2. 핵심 원칙: 관심사 분리 (Separation of Concerns)

> [!IMPORTANT]
> **다중 언어 혼재 금지 (No Inline Multi-language Blobs)**  
> Python 파일(`.py`) 내부에 수십~수천 줄에 달하는 HTML, CSS, JavaScript 코드를 다중행 문자열(`"""`) 형태로 하드코딩하는 것을 엄격히 금지합니다.

### 언어별 분리 기준 (Thresholds)
1. **CSS (Cascading Style Sheets)**:
   - **30줄 이상**의 스타일 또는 전역 테마 정의는 반드시 `static/css/*.css` 파일로 분리합니다.
   - Python 코드에서는 `ui_loader.py`를 통해 로드하여 주입합니다.
2. **JavaScript (JS)**:
   - **20줄 이상**의 스크립트 또는 브라우저 DOM 제어, 이벤트 리스너, IFrame 통신 로직은 반드시 `static/js/*.js` 파일로 분리합니다.
   - f-string 내부에서 자바스크립트 중괄호를 `{{}}`로 이중 이스케이프하는 행위를 전면 금지합니다.
3. **HTML / 템플릿**:
   - 구조적 UI 레이아웃 및 컴포넌트 마크업은 `static/templates/*.html` 파일로 분리합니다.
   - 동적 변수는 안전한 템플릿 치환 방식(`render_template` 또는 JSON config injection)을 사용합니다.
4. **Python (Backend & App Logic)**:
   - Python 코드는 API 연동, 데이터 파이프라인, 비즈니스 로직, 그리고 정적 자산 로드 및 Streamlit 컴포넌트 마운트 역할에 집중합니다.

---

## 3. 표준 프로젝트 디렉터리 레이아웃 (Standard Directory Layout)

각 웹 애플리케이션 프로젝트는 다음의 표준 디렉터리 구조를 엄격히 준수합니다:

```text
[project-root]/
├── static/                         # 프론트엔드 정적 자산 전용 디렉터리
│   ├── css/                        # 스타일시트 (.css)
│   │   ├── global_theme.css        # 전역 레이아웃 및 테마 스타일
│   │   └── [component].css         # 컴포넌트별 개별 스타일
│   ├── js/                         # 프론트엔드 스크립트 (.js)
│   │   ├── [feature].js            # 기능별 JavaScript 모듈
│   │   └── [component].js          # 컴포넌트 인터랙션 스크립트
│   └── templates/                  # HTML 마크업 템플릿 (.html)
│       └── [component].html        # 컴포넌트 구조 템플릿
├── assets/                         # 정적 이미지, 아이콘, 폰트 등 미디어 파일
├── downloads/                      # 임시 다운로드 오디오/비디오 저장소 (git 미포함)
├── ui_loader.py                    # CSS, JS, HTML 템플릿 로딩 & 렌더링 헬퍼 모듈
├── app.py                          # Streamlit 메인 진입점 (순수 Python 로직)
├── [service_engines].py            # 비즈니스 로직 / AI 연동 엔진 모듈
├── requirements.txt                # 프로젝트 의존성 목록
└── README.md                       # 프로젝트 문서화
```

---

## 4. 자산 로딩 표준 패턴 (`ui_loader.py`)

Python에서 정적 파일(CSS, JS, HTML)을 주입할 때는 반드시 `ui_loader.py` 표준 헬퍼를 경유합니다.

### 로더 구현 가이드라인
```python
# ui_loader.py 표준 인터페이스
import os
from pathlib import Path
from typing import Dict, Any

STATIC_DIR = Path(__file__).resolve().parent / "static"

def load_css(filename: str) -> str:
    """static/css/ 하위의 CSS 파일을 UTF-8로 안전하게 읽어옵니다."""
    path = STATIC_DIR / "css" / filename
    return path.read_text(encoding="utf-8")

def load_js(filename: str) -> str:
    """static/js/ 하위의 JS 파일을 UTF-8로 안전하게 읽어옵니다."""
    path = STATIC_DIR / "js" / filename
    return path.read_text(encoding="utf-8")

def render_template(filename: str, context: Dict[str, Any] = None) -> str:
    """static/templates/ 하위의 HTML 템플릿을 읽고 context 변수를 치환합니다."""
    path = STATIC_DIR / "templates" / filename
    template = path.read_text(encoding="utf-8")
    if context:
        for k, v in context.items():
            template = template.replace(f"{{{{{k}}}}}", str(v))
    return template
```

### `app.py`에서의 적용 표준
```python
import streamlit as st
import streamlit.components.v1 as components
from ui_loader import load_css, load_js, render_template

# 1. 전역 스타일 주입
st.markdown(f"<style>{load_css('global_theme.css')}</style>", unsafe_allow_html=True)

# 2. 브라우저 스크립트 주입
components.html(f"<script>{load_js('drawer.js')}</script>", height=0)

# 3. 일체형 컴포넌트 렌더링
html_output = render_template("player_component.html", context={"v_id": video_id})
components.html(html_output, height=645)
```

---

## 5. 언어별 코딩 및 품질 규칙

### 🐍 Python
- **모듈 탐색 경로 (`sys.path`) 보장**: 서브 프로젝트 진입점(`app.py`) 최상단에는 실행 위치(CWD)와 무관하게 로컬 모듈(`ui_loader`, 엔진 파일 등)을 안전하게 임포트할 수 있도록 `APP_DIR = os.path.dirname(os.path.abspath(__file__)); if APP_DIR not in sys.path: sys.path.insert(0, APP_DIR)`을 반드시 선언합니다.
- **인코딩**: Windows 환경 호환성을 위해 모든 파일 open 및 텍스트 입출력에 반드시 `encoding="utf-8"`을 명시합니다.
- **경로 처리**: OS 독립적인 `pathlib.Path` 또는 `os.path.join`을 사용하여 경로 구분자 역슬래시(`\`) 하드코딩 문제를 방지합니다.
- **모듈화**: 비즈니스 로직(다운로더, STT 엔진, QA 엔진, 캐시 매니저)은 단일 책임 원칙(SRP)에 따라 개별 `.py` 파일로 분리합니다.
- **예외 처리**: AI API 호출, 파일 I/O, 네트워크 작업 시 명확한 try-except 블록 및 사용자 친화적인 에러 메시지를 제공합니다.

### 🎨 CSS
- **순수 CSS 작성**: Python 문자열이 아니므로 모든 블록은 표준 CSS 중괄호 `{ ... }`를 단독 사용합니다.
- **변수 및 테마**: 색상, 폰트, 여백 등 반복되는 스타일 속성은 `:root` CSS 커스텀 속성(`--yt-spec-text-primary`, `--yt-brand-red`)으로 관리합니다.
- **클래스 네이밍**: BEM(Block Element Modifier) 또는 직관적인 케밥 케이스(`video-card`, `chat-bubble-user`)를 준수합니다.

### ⚡ JavaScript
- **엄격 모드 (Strict Mode)**: 모든 스크립트 모듈은 즉시 실행 함수(IIFE) 또는 `use strict;`로 래핑하여 전역 네임스페이스 오염을 방지합니다.
- **방어적 DOM 접근**: IFrame 간 통신(`window.parent`)이나 DOM 탐색 시 `try { ... } catch(e) { ... }` 및 null 체크를 필수로 적용합니다.
- **파라미터 주입**: 동적 데이터는 HTML의 `data-*` 속성이나 정형화된 JSON script 태그(`<script type="application/json">`) 또는 템플릿 치환 토큰을 통해 안전하게 파싱합니다.

---

## 6. AI 에이전트 행동 지침 (Agent Operating Rules)

1. **사전 영향도 파악**:
   - 기존의 작동 중인 비즈니스 로직, 변수명, 이벤트 핸들러, 세션 상태(`st.session_state`)를 파괴하지 않습니다.
2. **코드 생성 및 편집 원칙**:
   - 임의로 파일 내용을 축약(`// TODO: 기존 코드 유지`)하거나 생략하지 않고, 완전하고 동작 가능한 코드를 작성합니다.
3. **리팩토링 시 기능 무결성 보장**:
   - 인라인 코드를 분리할 때 기존에 적용되어 있던 스타일과 스크립트 이벤트가 100% 동일하게 동작하도록 토큰 및 셀렉터를 완벽히 일치시킵니다.
4. **검증 절차 준수**:
   - 변경 사항 적용 후 반드시 AST 컴파일(`py_compile`) 및 스크립트 실행 테스트를 거쳐 오류가 없음을 입증한 뒤 작업을 종료합니다.

---

*최종 개정일: 2026-09-11*  
*관리: Antigravity AI Coding Agent Standards Committee*
