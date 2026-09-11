"""
UI 및 정적 자산(CSS, JS, HTML 템플릿) 로더 모듈
AGENTS.md 표준 규격에 따라 프론트엔드 자산을 분리 로드하고 렌더링합니다.
"""

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

# static 디렉터리 경로 설정 (OS 독립적)
STATIC_DIR = Path(__file__).resolve().parent / "static"


@lru_cache(maxsize=32)
def load_css(filename: str) -> str:
    """
    static/css/ 경로에서 CSS 파일을 UTF-8로 읽어옵니다.
    lru_cache를 적용하여 디스크 I/O를 최소화합니다.
    """
    file_path = STATIC_DIR / "css" / filename
    if not file_path.exists():
        raise FileNotFoundError(f"CSS 파일을 찾을 수 없습니다: {file_path}")
    return file_path.read_text(encoding="utf-8")


@lru_cache(maxsize=32)
def load_js(filename: str) -> str:
    """
    static/js/ 경로에서 JavaScript 파일을 UTF-8로 읽어옵니다.
    lru_cache를 적용하여 디스크 I/O를 최소화합니다.
    """
    file_path = STATIC_DIR / "js" / filename
    if not file_path.exists():
        raise FileNotFoundError(f"JS 파일을 찾을 수 없습니다: {file_path}")
    return file_path.read_text(encoding="utf-8")


@lru_cache(maxsize=32)
def load_template(filename: str) -> str:
    """
    static/templates/ 경로에서 HTML 템플릿 파일을 UTF-8로 읽어옵니다.
    """
    file_path = STATIC_DIR / "templates" / filename
    if not file_path.exists():
        raise FileNotFoundError(f"HTML 템플릿 파일을 찾을 수 없습니다: {file_path}")
    return file_path.read_text(encoding="utf-8")


def render_template(filename: str, context: Optional[Dict[str, Any]] = None) -> str:
    """
    HTML 템플릿을 로드하고 context 변수들을 치환({{key}} 형태)하여 반환합니다.
    """
    content = load_template(filename)
    if context:
        for key, val in context.items():
            content = content.replace(f"{{{{{key}}}}}", str(val))
    return content


def render_drawer_html(
    saved_count: int,
    cached_cards_html: str,
    clear_btn_html: str,
) -> str:
    """
    사이드 서랍 메뉴 HTML 템플릿을 렌더링합니다.
    """
    context = {
        "saved_count": saved_count,
        "cached_cards_html": cached_cards_html,
        "clear_btn_html": clear_btn_html,
    }
    raw_html = render_template("drawer.html", context)
    return "\n".join(line.strip() for line in raw_html.splitlines() if line.strip())


def render_player_component(
    v_id: str,
    v_title: str,
    uploader_initial: str,
    v_uploader: str,
    v_views: str,
    v_duration_str: str,
    segments_count_val: int,
    audio_size_str: str,
    segments: List[Dict[str, Any]],
    chapters: List[Dict[str, Any]],
    api_key: str,
    safe_title: str,
    audio_b64: str,
) -> str:
    """
    일체형 플레이어 컴포넌트(좌측 비디오/타임라인 + 우측 4대 탭) 전체 HTML 문서를 생성합니다.
    CSS, HTML 마크업, JS 스크립트를 독립 파일에서 조합하고
    동적 구성 객체(window.__PLAYER_CONFIG__)를 안전하게 주입합니다.
    """
    # 1. 컴포넌트 CSS 로드
    player_css = load_css("player_component.css")

    # 2. 마크업 템플릿 렌더링
    markup_context = {
        "v_id": v_id,
        "v_title": v_title,
        "uploader_initial": uploader_initial,
        "v_uploader": v_uploader,
        "v_views": v_views,
        "v_duration_str": v_duration_str,
        "segments_count_val": segments_count_val,
        "audio_size_str": audio_size_str,
    }
    player_markup = render_template("player_component.html", markup_context)

    # 3. 브라우저 스크립트 실행에 필요한 런타임 설정 직렬화 (JSON 주입 방식)
    config_dict = {
        "videoId": v_id,
        "apiKey": api_key,
        "videoTitleSafe": safe_title,
        "segments": segments,
        "chapters": chapters,
        "audioB64": audio_b64,
    }
    config_json = json.dumps(config_dict, ensure_ascii=False)

    # 4. 컴포넌트 JS 로드
    player_js = load_js("player_component.js")

    # 5. 완성된 독립 HTML 문서 조합
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <style>
{player_css}
    </style>
</head>
<body>
{player_markup}
    <script>
        window.__PLAYER_CONFIG__ = {config_json};
    </script>
    <script>
{player_js}
    </script>
</body>
</html>"""
