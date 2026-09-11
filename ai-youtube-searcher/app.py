import os
import sys
import json
import base64
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

# 로컬 엔진 모듈 임포트
from downloader import extract_video_id, get_video_info, download_audio
from transcribe_engine import transcribe_with_timestamps, format_seconds
from qa_engine import answer_question_with_timestamps, extract_video_chapters
from cache_manager import (
    save_to_cache,
    load_from_cache,
    has_cache,
    get_all_cached_videos,
    delete_from_cache,
    clear_all_cache,
)

# Windows 환경 한글 출력 인코딩 대응
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

load_dotenv()

# --- 페이지 설정 (와이드 모드, 사이드바 기본 축소) ---
st.set_page_config(
    page_title="AI 유튜브 검색기",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# --- 구글 유튜브 공식 다크 테마 UI CSS ---
st.markdown("""
<style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap');
    
    * {
        font-family: 'Pretendard', 'Roboto', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* [이중 스크롤바 완전 제거] html, body, .stApp의 스크롤바를 숨기고 stAppViewContainer 단 하나에서만 스크롤 처리 */
    html, body {
        background-color: #0f0f0f !important;
        color: #f1f1f1 !important;
        overflow: hidden !important;
        height: 100% !important;
        margin: 0 !important;
        padding: 0 !important;
        scrollbar-width: none !important;
        -ms-overflow-style: none !important;
    }
    html::-webkit-scrollbar, body::-webkit-scrollbar {
        display: none !important;
        width: 0 !important;
        height: 0 !important;
    }
    .stApp {
        background-color: #0f0f0f !important;
        color: #f1f1f1 !important;
        overflow: hidden !important;
        height: 100% !important;
    }
    [data-testid="stAppViewContainer"] {
        background-color: #0f0f0f !important;
        color: #f1f1f1 !important;
        overflow-x: hidden !important;
        overflow-y: auto !important;
        height: 100% !important;
        scroll-behavior: smooth !important;
    }
    
    /* 앱 전체 부드럽고 얇은 단일 유튜브 다크 스크롤바 */
    [data-testid="stAppViewContainer"]::-webkit-scrollbar {
        width: 8px;
    }
    [data-testid="stAppViewContainer"]::-webkit-scrollbar-track {
        background: #0f0f0f;
    }
    [data-testid="stAppViewContainer"]::-webkit-scrollbar-thumb {
        background: #27272c;
        border-radius: 4px;
    }
    [data-testid="stAppViewContainer"]::-webkit-scrollbar-thumb:hover {
        background: #3ea6ff;
    }

    /* iframe 요소의 불필요한 스크롤바 및 테두리 차단 */
    iframe {
        border: none !important;
        outline: none !important;
    }
    
    /* Streamlit 기본 헤더 비활성화 - 상단 검색창 클릭 및 호버 방해 완전 차단 */
    header[data-testid="stHeader"] {
        background: transparent !important;
        height: 0px !important;
        min-height: 0px !important;
        padding: 0 !important;
        margin: 0 !important;
        overflow: hidden !important;
        pointer-events: none !important;
        z-index: 0 !important;
    }
    
    /* Deploy 버튼 및 우측 툴바 완전 숨김 (헤더 겹침 및 클릭 가로채기 방지) */
    header[data-testid="stHeader"] [data-testid="stToolbar"],
    div[data-testid="stToolbar"] {
        display: none !important;
    }
    
    /* 사이드바 열기 버튼(필요 시) 기능 보존 */
    [data-testid="stSidebarCollapsedControl"] {
        pointer-events: auto !important;
        z-index: 999999 !important;
        top: 8px !important;
        left: 8px !important;
    }
    
    /* 메인 앱 컨테이너 및 뷰포트 레이어 상위 배치 */
    [data-testid="stAppViewContainer"] {
        z-index: 10 !important;
        position: relative !important;
    }
    
    /* 한 화면 여백 최적화 (상단 UI 잘림 방지) */
    .block-container {
        padding-top: 0.6rem !important;
        padding-bottom: 0.4rem !important;
        padding-left: 1.2rem !important;
        padding-right: 1.2rem !important;
        max-width: 100% !important;
        position: relative !important;
        z-index: 20 !important;
    }
    
    /* [상단 헤더 & 검색바] 최상위 레이어 인터랙션 보장 */
    .yt-nav-header-left {
        display: flex;
        align-items: center;
        height: 38px;
        position: relative !important;
        z-index: 100 !important;
    }
    /* 유튜브 공식 상단 네비바 헤더 좌측 (메뉴 아이콘 + 유튜브 로고) */
    .yt-nav-header-left {
        display: flex;
        align-items: center;
        gap: 16px;
        height: 40px;
    }
    .yt-menu-icon {
        width: 38px;
        height: 38px;
        min-width: 38px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        transition: background-color 0.15s ease;
        text-decoration: none !important;
        color: #ffffff !important;
    }
    .yt-menu-icon:hover {
        background-color: #272727;
    }
    .yt-logo-link {
        display: flex;
        align-items: center;
        text-decoration: none !important;
        cursor: pointer;
        user-select: none;
    }
    .yt-wordmark {
        font-family: 'Roboto', 'Pretendard', sans-serif;
        font-weight: 700;
        font-size: 1.25rem;
        color: #ffffff;
        letter-spacing: -0.8px;
        margin-left: 4px;
    }
    .yt-country-code {
        font-size: 0.65rem;
        color: #aaaaaa;
        font-weight: 400;
        vertical-align: top;
        margin-top: -6px;
        margin-left: 3px;
    }
    
    /* 상단 우측 퀵 버튼 및 유저 아바타 */
    .yt-nav-header-right {
        display: flex;
        align-items: center;
        justify-content: flex-end;
        gap: 10px;
        height: 40px;
    }
    .yt-create-btn {
        display: flex;
        align-items: center;
        gap: 6px;
        background: #272727;
        border-radius: 20px;
        padding: 0 14px;
        height: 36px;
        color: #f1f1f1;
        font-size: 0.86rem;
        font-weight: 600;
        cursor: pointer;
        transition: background 0.15s ease;
        user-select: none;
    }
    .yt-create-btn:hover {
        background: #383838;
    }
    .yt-icon-round-btn {
        width: 38px;
        height: 38px;
        min-width: 38px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        transition: background 0.15s ease;
        color: #f1f1f1;
    }
    .yt-icon-round-btn:hover {
        background: #272727;
    }
    .yt-avatar-circle {
        width: 32px;
        height: 32px;
        min-width: 32px;
        border-radius: 50%;
        background: #7c4dff;
        color: #ffffff;
        font-size: 0.85rem;
        font-weight: 700;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        user-select: none;
        margin-left: 4px;
    }
    
    /* 유튜브 공식 일체형 검색창 & 마이크 버튼 (상단 헤더 전용) */
    div[data-testid="stForm"]:has(input[aria-label="유튜브 링크 주소"]),
    div[data-testid="stForm"]:has(input[id*="yt_url_input_box"]) {
        border: none !important;
        padding: 0 !important;
        margin: 0 !important;
        background: transparent !important;
        position: relative !important;
        z-index: 100 !important;
    }
    div[data-testid="stForm"]:has(input[aria-label="유튜브 링크 주소"]) [data-testid="stHorizontalBlock"],
    div[data-testid="stForm"]:has(input[id*="yt_url_input_box"]) [data-testid="stHorizontalBlock"] {
        gap: 0px !important;
        align-items: center !important;
    }
    
    /* 헤더 검색 인풋창 (좌측 둥근 알약 + 우측 직각 연결) */
    div[data-testid="stForm"]:has(input[aria-label="유튜브 링크 주소"]) .stTextInput,
    div[data-testid="stForm"]:has(input[id*="yt_url_input_box"]) .stTextInput {
        margin: 0 !important;
        padding: 0 !important;
        position: relative !important;
        z-index: 101 !important;
    }
    div[data-testid="stForm"]:has(input[aria-label="유튜브 링크 주소"]) .stTextInput > div,
    div[data-testid="stForm"]:has(input[id*="yt_url_input_box"]) .stTextInput > div {
        margin: 0 !important;
        padding: 0 !important;
    }
    div[data-testid="stForm"]:has(input[aria-label="유튜브 링크 주소"]) .stTextInput > div > div,
    div[data-testid="stForm"]:has(input[id*="yt_url_input_box"]) .stTextInput > div > div {
        background-color: #121212 !important;
        border: 1px solid #303030 !important;
        border-right: none !important;
        border-radius: 40px 0 0 40px !important;
        height: 40px !important;
        min-height: 40px !important;
        padding: 0 !important;
        box-shadow: inset 0 1px 2px rgba(0, 0, 0, 0.2) !important;
        transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
    }
    div[data-testid="stForm"]:has(input[aria-label="유튜브 링크 주소"]) .stTextInput > div > div:hover,
    div[data-testid="stForm"]:has(input[id*="yt_url_input_box"]) .stTextInput > div > div:hover {
        border-color: #444444 !important;
    }
    div[data-testid="stForm"]:has(input[aria-label="유튜브 링크 주소"]) .stTextInput > div > div:focus-within,
    div[data-testid="stForm"]:has(input[id*="yt_url_input_box"]) .stTextInput > div > div:focus-within {
        border-color: #1c62b9 !important;
        box-shadow: inset 0 1px 2px rgba(0, 0, 0, 0.5) !important;
    }
    div[data-testid="stForm"]:has(input[aria-label="유튜브 링크 주소"]) .stTextInput input,
    div[data-testid="stForm"]:has(input[id*="yt_url_input_box"]) .stTextInput input {
        background-color: transparent !important;
        color: #f1f1f1 !important;
        border: none !important;
        border-radius: 40px 0 0 40px !important;
        height: 38px !important;
        padding: 0 18px !important;
        font-size: 0.92rem !important;
        box-shadow: none !important;
        outline: none !important;
    }
    
    /* 헤더 검색 제출 버튼 (좌측 직각 + 우측 둥근 알약 다크 그레이) */
    div[data-testid="stForm"]:has(input[aria-label="유튜브 링크 주소"]) div[data-testid="stFormSubmitButton"],
    div[data-testid="stForm"]:has(input[id*="yt_url_input_box"]) div[data-testid="stFormSubmitButton"] {
        margin: 0 !important;
        padding: 0 !important;
        height: 40px !important;
        display: flex !important;
        align-items: center !important;
        width: 100% !important;
        position: relative !important;
        z-index: 101 !important;
    }
    div[data-testid="stForm"]:has(input[aria-label="유튜브 링크 주소"]) div[data-testid="stFormSubmitButton"] button,
    div[data-testid="stForm"]:has(input[id*="yt_url_input_box"]) div[data-testid="stFormSubmitButton"] button {
        width: 100% !important;
        height: 40px !important;
        min-height: 40px !important;
        background-color: #222222 !important;
        border: 1px solid #303030 !important;
        border-radius: 0 40px 40px 0 !important;
        color: #f1f1f1 !important;
        box-shadow: none !important;
        transition: background-color 0.15s ease, border-color 0.15s ease !important;
        cursor: pointer !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }
    div[data-testid="stForm"]:has(input[aria-label="유튜브 링크 주소"]) div[data-testid="stFormSubmitButton"] button:hover,
    div[data-testid="stForm"]:has(input[id*="yt_url_input_box"]) div[data-testid="stFormSubmitButton"] button:hover {
        background-color: #272727 !important;
        border-color: #383838 !important;
        color: #ffffff !important;
    }
    div[data-testid="stForm"]:has(input[aria-label="유튜브 링크 주소"]) div[data-testid="stFormSubmitButton"] button:active,
    div[data-testid="stForm"]:has(input[id*="yt_url_input_box"]) div[data-testid="stFormSubmitButton"] button:active {
        background-color: #333333 !important;
    }
    div[data-testid="stForm"]:has(input[aria-label="유튜브 링크 주소"]) div[data-testid="stFormSubmitButton"] button p,
    div[data-testid="stForm"]:has(input[id*="yt_url_input_box"]) div[data-testid="stFormSubmitButton"] button p {
        margin: 0 !important;
        padding: 0 !important;
        font-size: 1.1rem !important;
        color: #f1f1f1 !important;
        line-height: 1 !important;
    }
    
    /* 음성 마이크 버튼 */
    .yt-mic-btn {
        width: 40px;
        height: 40px;
        min-width: 40px;
        border-radius: 50%;
        background: #222222;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        transition: background-color 0.15s ease;
        margin-left: 8px;
    }
    .yt-mic-btn:hover {
        background: #2e2e2e;
    }
    
    /* 반응형 사이드 드로어 (분석 보관함 및 카테고리 메뉴) */
    .yt-drawer-backdrop {
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        background: rgba(0, 0, 0, 0.72);
        backdrop-filter: blur(4px);
        z-index: 99998 !important;
        opacity: 0;
        pointer-events: none;
        transition: opacity 0.25s cubic-bezier(0.1, 0.9, 0.2, 1);
        cursor: pointer;
    }
    .yt-drawer-backdrop.open {
        opacity: 1 !important;
        pointer-events: auto !important;
    }
    .yt-drawer-panel {
        position: fixed;
        top: 0;
        left: 0;
        width: 390px;
        max-width: 88vw;
        height: 100vh;
        background: #0f0f0f;
        border-right: 1px solid #282828;
        box-shadow: 8px 0 32px rgba(0, 0, 0, 0.9);
        z-index: 99999 !important;
        transform: translateX(-100%);
        transition: transform 0.28s cubic-bezier(0.1, 0.9, 0.2, 1);
        display: flex;
        flex-direction: column;
        box-sizing: border-box;
    }
    .yt-drawer-panel.open,
    body:has(#yt-drawer-toggle:checked) .yt-drawer-panel {
        transform: translateX(0) !important;
    }
    .d-category-section {
        margin-bottom: 12px;
    }
    .d-category-title {
        font-size: 0.78rem;
        font-weight: 700;
        color: #aaaaaa;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 8px;
        padding-left: 2px;
    }
    .d-category-chips {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
    }
    .d-cat-chip {
        background: #1e1e1e;
        color: #f1f1f1;
        border: 1px solid #2d2d2d;
        border-radius: 16px;
        padding: 4px 10px;
        font-size: 0.75rem;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.15s ease;
        user-select: none;
    }
    .d-cat-chip:hover, .d-cat-chip.active {
        background: #ffffff;
        color: #0f0f0f;
        border-color: #ffffff;
        font-weight: 700;
    }
    .d-search-box {
        margin-bottom: 10px;
    }
    .d-search-input {
        width: 100%;
        box-sizing: border-box;
        background: #141414;
        border: 1px solid #2a2a2a;
        border-radius: 8px;
        color: #f1f1f1;
        padding: 7px 10px;
        font-size: 0.78rem;
        outline: none;
        transition: border-color 0.2s;
    }
    .d-search-input:focus {
        border-color: #3ea6ff;
        background: #181818;
    }
    .d-panel-header {
        display: flex;
        align-items: center;
        padding: 0 16px;
        height: 56px;
        min-height: 56px;
        border-bottom: 1px solid #202020;
    }
    .d-panel-body {
        flex: 1;
        display: flex;
        flex-direction: column;
        overflow: hidden;
        padding: 12px 14px;
    }
    .d-menu-btn {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 10px 14px;
        background: #181818;
        border-radius: 10px;
        color: #f1f1f1 !important;
        font-weight: 600;
        font-size: 0.92rem;
        text-decoration: none !important;
        transition: background 0.15s ease;
        border: 1px solid #262626;
        margin-bottom: 10px;
    }
    .d-menu-btn:hover {
        background: #242424;
        border-color: #383838;
    }
    .d-section-divider {
        height: 1px;
        background: #202020;
        margin: 6px 0 12px 0;
    }
    .d-section-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 10px;
        padding: 0 4px;
    }
    .d-count-pill {
        background: #222222;
        color: #3ea6ff;
        border: 1px solid #303030;
        border-radius: 12px;
        padding: 2px 8px;
        font-size: 0.72rem;
        font-weight: 700;
    }
    .d-scroll-area {
        flex: 1;
        overflow-y: auto;
        display: flex;
        flex-direction: column;
        gap: 8px;
        padding-right: 4px;
    }
    .d-scroll-area::-webkit-scrollbar {
        width: 5px;
    }
    .d-scroll-area::-webkit-scrollbar-thumb {
        background: #2a2a2a;
        border-radius: 3px;
    }
    .d-video-card {
        display: flex;
        align-items: center;
        background: #161616;
        border: 1px solid #262626;
        border-radius: 10px;
        padding: 10px 12px;
        gap: 10px;
        transition: all 0.18s ease;
        position: relative;
    }
    .d-video-card:hover {
        background: #202020;
        border-color: #3ea6ff;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
    }
    .d-card-link {
        display: flex;
        align-items: center;
        gap: 10px;
        text-decoration: none !important;
        flex: 1;
        min-width: 0;
    }
    .d-dur-tag-inline {
        background: #242424;
        color: #aaaaaa;
        font-size: 0.68rem;
        font-weight: 600;
        padding: 1px 6px;
        border-radius: 4px;
        border: 1px solid #333333;
    }
    .d-info-box {
        flex: 1;
        min-width: 0;
        display: flex;
        flex-direction: column;
        gap: 4px;
    }
    .d-title {
        color: #f1f1f1;
        font-size: 0.82rem;
        font-weight: 600;
        line-height: 1.3;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .d-uploader {
        color: #888888;
        font-size: 0.72rem;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .d-footer-row {
        display: flex;
        align-items: center;
        gap: 6px;
        margin-top: 1px;
    }
    .d-token-tag {
        background: #0e2a47;
        color: #3ea6ff;
        border: 1px solid #1c4a75;
        border-radius: 8px;
        padding: 1px 5px;
        font-size: 0.65rem;
        font-weight: 700;
    }
    .d-date-tag {
        color: #666;
        font-size: 0.68rem;
    }
    .d-del-btn {
        width: 28px;
        height: 28px;
        min-width: 28px;
        border-radius: 6px;
        display: flex;
        align-items: center;
        justify-content: center;
        text-decoration: none !important;
        opacity: 0.5;
        transition: all 0.15s ease;
    }
    .d-del-btn:hover {
        opacity: 1;
        background: rgba(255, 0, 0, 0.15);
    }
    .d-empty-box {
        text-align: center;
        padding: 40px 16px;
        color: #777;
    }
    .d-panel-footer {
        padding-top: 10px;
        border-top: 1px solid #202020;
        margin-top: 8px;
    }
    .d-clear-all-btn {
        display: block;
        text-align: center;
        padding: 7px;
        font-size: 0.76rem;
        color: #999 !important;
        text-decoration: none !important;
        border-radius: 6px;
        transition: all 0.15s ease;
    }
    .d-clear-all-btn:hover {
        color: #ff5555 !important;
        background: #1f1414;
    }
    
    /* 홈 화면 분석 보관함 그리드 카드 */
    .home-cache-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
        gap: 16px;
        margin-top: 14px;
    }
    .home-cache-card {
        background: #181818;
        border: 1px solid #282828;
        border-radius: 12px;
        overflow: hidden;
        text-decoration: none !important;
        transition: transform 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease;
        display: flex;
        flex-direction: column;
    }
    .home-cache-card:hover {
        transform: translateY(-2px);
        border-color: #3ea6ff;
        box-shadow: 0 6px 20px rgba(0,0,0,0.6);
    }
    .home-card-thumb {
        position: relative;
        width: 100%;
        aspect-ratio: 16/9;
        background: #000;
    }
    .home-card-thumb img {
        width: 100%;
        height: 100%;
        object-fit: cover;
    }
    .home-card-dur {
        position: absolute;
        bottom: 6px;
        right: 6px;
        background: rgba(0,0,0,0.85);
        color: #fff;
        font-size: 0.7rem;
        font-weight: 700;
        padding: 2px 5px;
        border-radius: 4px;
    }
    .home-card-body {
        padding: 10px 12px;
        display: flex;
        flex-direction: column;
        gap: 4px;
        flex: 1;
    }
    .home-card-title {
        color: #f1f1f1;
        font-size: 0.88rem;
        font-weight: 700;
        line-height: 1.35;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }
    .home-card-uploader {
        color: #aaaaaa;
        font-size: 0.76rem;
    }
    .home-card-footer {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-top: 6px;
        padding-top: 6px;
        border-top: 1px solid #242424;
    }

    /* 모바일 및 좁은 화면에서도 상단 헤더 3대 칼럼을 1줄(가로 flex)로 완벽 유지 */
    [data-testid="stHorizontalBlock"]:has(.yt-nav-header-left) {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        align-items: center !important;
        gap: 6px !important;
    }
    [data-testid="stHorizontalBlock"]:has(.yt-nav-header-left) > [data-testid="column"]:nth-child(1) {
        width: auto !important;
        min-width: fit-content !important;
        flex: 0 0 auto !important;
    }
    [data-testid="stHorizontalBlock"]:has(.yt-nav-header-left) > [data-testid="column"]:nth-child(2) {
        flex: 1 1 auto !important;
        min-width: 0 !important;
    }
    [data-testid="stHorizontalBlock"]:has(.yt-nav-header-left) > [data-testid="column"]:nth-child(3) {
        width: auto !important;
        min-width: fit-content !important;
        flex: 0 0 auto !important;
    }

    /* ==================================================== */
    /*  실시간 대본 AI / Chrome New Tab 스타일 홈 UI     */
    /* ==================================================== */
    .google-home-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        width: 100%;
        max-width: 800px;
        margin: clamp(30px, 8vh, 75px) auto 0 auto;
        padding: 0 16px;
        box-sizing: border-box;
    }
    .google-logo-text {
        font-family: 'Pretendard', 'Google Sans', 'Roboto', -apple-system, sans-serif;
        font-size: clamp(38px, 5.5vw, 58px);
        font-weight: 800;
        color: #ffffff;
        letter-spacing: -1.5px;
        text-align: center;
        margin-bottom: 24px;
        user-select: none;
        line-height: 1.15;
        text-shadow: 0 2px 12px rgba(0, 0, 0, 0.6);
    }
    
    /* Google / 실시간 대본 AI 화이트 필 검색창 컨테이너 */
    div[data-testid="stForm"]:has(input[id*="home_url_input_box"]),
    div[data-testid="stForm"]:has(input[aria-label="유튜브 링크를 입력하세요."]) {
        width: 100% !important;
        max-width: 680px !important;
        margin: 0 auto !important;
        background: #ffffff !important;
        border-radius: 28px !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.35) !important;
        padding: 4px 6px 4px 10px !important;
        border: none !important;
        display: flex !important;
        align-items: center !important;
        transition: box-shadow 0.2s ease !important;
        box-sizing: border-box !important;
    }
    div[data-testid="stForm"]:has(input[id*="home_url_input_box"]):hover,
    div[data-testid="stForm"]:has(input[id*="home_url_input_box"]):focus-within,
    div[data-testid="stForm"]:has(input[aria-label="유튜브 링크를 입력하세요."]):hover,
    div[data-testid="stForm"]:has(input[aria-label="유튜브 링크를 입력하세요."]):focus-within {
        box-shadow: 0 4px 18px rgba(0, 0, 0, 0.55) !important;
    }
    div[data-testid="stForm"]:has(input[id*="home_url_input_box"]) [data-testid="stHorizontalBlock"],
    div[data-testid="stForm"]:has(input[aria-label="유튜브 링크를 입력하세요."]) [data-testid="stHorizontalBlock"] {
        gap: 6px !important;
        align-items: center !important;
        width: 100% !important;
        background: transparent !important;
    }
    div[data-testid="stForm"]:has(input[id*="home_url_input_box"]) [data-testid="column"],
    div[data-testid="stForm"]:has(input[aria-label="유튜브 링크를 입력하세요."]) [data-testid="column"] {
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        padding: 0 !important;
    }
    div[data-testid="stForm"]:has(input[id*="home_url_input_box"]) .stTextInput,
    div[data-testid="stForm"]:has(input[aria-label="유튜브 링크를 입력하세요."]) .stTextInput {
        flex: 1 1 auto !important;
        margin: 0 !important;
        padding: 0 !important;
        width: 100% !important;
    }
    div[data-testid="stForm"]:has(input[id*="home_url_input_box"]) .stTextInput > div,
    div[data-testid="stForm"]:has(input[aria-label="유튜브 링크를 입력하세요."]) .stTextInput > div {
        padding: 0 !important;
        margin: 0 !important;
    }
    div[data-testid="stForm"]:has(input[id*="home_url_input_box"]) .stTextInput > div > div,
    div[data-testid="stForm"]:has(input[aria-label="유튜브 링크를 입력하세요."]) .stTextInput > div > div {
        background: transparent !important;
        border: none !important;
        border-radius: 0 !important;
        box-shadow: none !important;
        height: 44px !important;
        min-height: 44px !important;
        padding: 0 !important;
    }
    div[data-testid="stForm"]:has(input[id*="home_url_input_box"]) .stTextInput input,
    div[data-testid="stForm"]:has(input[aria-label="유튜브 링크를 입력하세요."]) .stTextInput input {
        color: #202124 !important;
        font-size: 1.02rem !important;
        background: transparent !important;
        padding: 0 16px 0 16px !important;
        height: 44px !important;
        box-shadow: none !important;
        border: none !important;
        outline: none !important;
    }
    div[data-testid="stForm"]:has(input[id*="home_url_input_box"]) .stTextInput input::placeholder,
    div[data-testid="stForm"]:has(input[aria-label="유튜브 링크를 입력하세요."]) .stTextInput input::placeholder {
        color: #5f6368 !important;
        opacity: 1 !important;
        font-size: 0.98rem !important;
    }
    div[data-testid="stForm"]:has(input[id*="home_url_input_box"]) div[data-testid="stFormSubmitButton"],
    div[data-testid="stForm"]:has(input[aria-label="유튜브 링크를 입력하세요."]) div[data-testid="stFormSubmitButton"] {
        width: auto !important;
        margin: 0 !important;
        padding: 0 !important;
        flex: 0 0 auto !important;
        height: 38px !important;
    }
    div[data-testid="stForm"]:has(input[id*="home_url_input_box"]) div[data-testid="stFormSubmitButton"] button,
    div[data-testid="stForm"]:has(input[aria-label="유튜브 링크를 입력하세요."]) div[data-testid="stFormSubmitButton"] button {
        background: #0f0f0f !important;
        border: none !important;
        border-radius: 20px !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        font-size: 0.92rem !important;
        height: 38px !important;
        min-height: 38px !important;
        padding: 0 22px !important;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.2) !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        cursor: pointer !important;
        transition: all 0.15s ease !important;
        white-space: nowrap !important;
    }
    div[data-testid="stForm"]:has(input[id*="home_url_input_box"]) div[data-testid="stFormSubmitButton"] button:hover,
    div[data-testid="stForm"]:has(input[aria-label="유튜브 링크를 입력하세요."]) div[data-testid="stFormSubmitButton"] button:hover {
        background: #272727 !important;
        color: #ffffff !important;
        box-shadow: 0 3px 10px rgba(0, 0, 0, 0.35) !important;
    }
    div[data-testid="stForm"]:has(input[id*="home_url_input_box"]) div[data-testid="stFormSubmitButton"] button p,
    div[data-testid="stForm"]:has(input[aria-label="유튜브 링크를 입력하세요."]) div[data-testid="stFormSubmitButton"] button p {
        color: #ffffff !important;
        font-size: 0.92rem !important;
        font-weight: 700 !important;
        margin: 0 !important;
        padding: 0 !important;
    }

    /* Google Chrome New Tab 원형 바로가기 그리드 */
    .google-shortcuts-grid {
        display: flex;
        justify-content: center;
        align-items: flex-start;
        gap: 16px;
        flex-wrap: wrap;
        margin-top: 32px;
        max-width: 680px;
        margin-left: auto;
        margin-right: auto;
    }
    .google-shortcut-item {
        display: flex;
        flex-direction: column;
        align-items: center;
        width: 86px;
        text-decoration: none !important;
        cursor: pointer;
        border-radius: 8px;
        padding: 8px 4px;
        transition: background 0.15s ease;
    }
    .google-shortcut-item:hover {
        background: rgba(255, 255, 255, 0.08);
    }
    .google-shortcut-circle {
        width: 48px;
        height: 48px;
        border-radius: 50%;
        background: #303134;
        display: flex;
        align-items: center;
        justify-content: center;
        margin-bottom: 8px;
        box-shadow: 0 1px 4px rgba(0, 0, 0, 0.3);
        transition: background 0.15s ease, transform 0.15s ease;
        overflow: hidden;
    }
    .google-shortcut-item:hover .google-shortcut-circle {
        background: #3c4043;
        transform: translateY(-2px);
    }
    .google-shortcut-circle img {
        width: 48px;
        height: 48px;
        border-radius: 50%;
        object-fit: cover;
    }
    .google-shortcut-title {
        color: #e8eaed;
        font-size: 0.78rem;
        font-weight: 500;
        text-align: center;
        width: 80px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        line-height: 1.3;
    }

    /* 영상 상세 정보 바 반응형 */
    .video-info-banner {
        background: #181818;
        border: 1px solid #282828;
        border-radius: 8px;
        padding: 6px 14px;
        min-height: 36px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 10px;
        flex-wrap: wrap;
        margin-top: 4px;
    }
    .v-info-left {
        display: flex;
        align-items: center;
        gap: 8px;
        min-width: 0;
        flex: 1 1 auto;
    }
    .v-uploader-avatar {
        width: 22px;
        height: 22px;
        min-width: 22px;
        background: #333333;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        color: #fff;
        font-size: 0.72rem;
        font-weight: 700;
    }
    .v-info-title {
        font-weight: 700;
        font-size: 0.88rem;
        color: #ffffff;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        max-width: 600px;
    }
    .v-info-meta {
        display: flex;
        align-items: center;
        gap: 8px;
        flex-wrap: wrap;
    }
    .v-meta-item {
        color: #aaaaaa;
        font-size: 0.8rem;
        white-space: nowrap;
    }
    .v-meta-dot {
        color: #555555;
    }

    /* 반응형 모바일 및 태블릿 미디어 쿼리 */
    @media (max-width: 768px) {
        .block-container {
            padding-left: 0.5rem !important;
            padding-right: 0.5rem !important;
            padding-top: 0.4rem !important;
        }
        .yt-create-btn {
            display: none !important;
        }
        .yt-icon-round-btn {
            display: none !important;
        }
        .yt-mic-btn {
            display: none !important;
        }
        .yt-wordmark, .yt-country-code {
            display: none !important;
        }
        .yt-nav-header-left {
            gap: 8px !important;
        }
        .video-info-banner {
            flex-direction: column;
            align-items: flex-start;
            gap: 6px;
            padding: 8px 12px;
        }
        .v-info-title {
            white-space: normal;
            word-break: break-word;
            max-width: 100%;
        }
        .home-cache-grid {
            grid-template-columns: 1fr;
            gap: 12px;
        }
    }

    /* 대본 생성 중 로딩 화면 스타일 */
    .generating-screen-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        min-height: 55vh;
        width: 100%;
        text-align: center;
        padding: 60px 20px;
        box-sizing: border-box;
        animation: genFadeIn 0.35s ease-out forwards;
    }

    @keyframes genFadeIn {
        from {
            opacity: 0;
            transform: translateY(8px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    .generating-title {
        color: #ffffff !important;
        font-size: clamp(34px, 5.5vw, 56px) !important;
        font-weight: 800 !important;
        letter-spacing: -1.2px !important;
        margin: 0 0 34px 0 !important;
        line-height: 1.25 !important;
        text-align: center !important;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Noto Sans KR", sans-serif !important;
        text-shadow: 0 2px 14px rgba(255, 255, 255, 0.15), 0 4px 20px rgba(0, 0, 0, 0.7) !important;
    }

    .generating-spinner {
        width: 60px;
        height: 60px;
        border: 5px solid rgba(255, 255, 255, 0.14);
        border-top: 5px solid #ffffff;
        border-right: 5px solid rgba(255, 255, 255, 0.7);
        border-radius: 50%;
        animation: genSpinnerRotate 0.85s linear infinite;
        box-shadow: 0 0 24px rgba(255, 255, 255, 0.12);
        margin: 0 auto;
    }

    @keyframes genSpinnerRotate {
        0% {
            transform: rotate(0deg);
        }
        100% {
            transform: rotate(360deg);
        }
    }
</style>
""", unsafe_allow_html=True)


# --- [홈 복귀 및 캐시 로드/삭제 핸들러] ---
q_params = st.query_params

if q_params.get("home") == "true" or q_params.get("reset") == "true":
    for key in ["video_id", "video_info", "audio_path", "transcript_data", "chapters_data", "chat_messages", "current_url", "from_cache", "trigger_search", "is_analyzing", "target_analyze_url", "target_v_id"]:
        if key in st.session_state:
            del st.session_state[key]
    st.query_params.clear()
    st.rerun()

load_cache_id = q_params.get("load_cache")
if load_cache_id:
    c_data = load_from_cache(load_cache_id)
    if c_data:
        st.session_state.video_id = c_data["video_id"]
        st.session_state.video_info = c_data["video_info"]
        st.session_state.audio_path = c_data.get("audio_path", "")
        st.session_state.transcript_data = c_data["transcript_data"]
        st.session_state.chapters_data = c_data.get("chapters_data", [])
        st.session_state.current_url = c_data.get("url", f"https://www.youtube.com/watch?v={load_cache_id}")
        st.session_state.chat_messages = []
        st.session_state.from_cache = True
        st.query_params.clear()
        st.toast("분석 보관함에서 대본을 불러왔습니다.")
        st.rerun()

del_cache_id = q_params.get("delete_cache")
if del_cache_id:
    delete_from_cache(del_cache_id)
    st.query_params.clear()
    st.rerun()

if q_params.get("clear_all_cache") == "true":
    clear_all_cache()
    st.query_params.clear()
    st.rerun()


# --- 세션 상태 초기화 ---
if "video_id" not in st.session_state:
    st.session_state.video_id = None
if "video_info" not in st.session_state:
    st.session_state.video_info = None
if "audio_path" not in st.session_state:
    st.session_state.audio_path = None
if "transcript_data" not in st.session_state:
    st.session_state.transcript_data = None
if "chapters_data" not in st.session_state:
    st.session_state.chapters_data = []
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []
if "current_url" not in st.session_state:
    st.session_state.current_url = ""
if "is_analyzing" not in st.session_state:
    st.session_state.is_analyzing = False
if "target_analyze_url" not in st.session_state:
    st.session_state.target_analyze_url = ""
if "target_v_id" not in st.session_state:
    st.session_state.target_v_id = ""


# --- 사이드바 설정 ---
with st.sidebar:
    st.header("Gemini API 설정")
    env_api_key = os.environ.get("GEMINI_API_KEY", "")
    api_key_input = st.text_input(
        "Gemini API Key",
        value=env_api_key,
        type="password",
        help=".env 파일 또는 직접 입력 가능",
    )
    if not api_key_input:
        st.warning("Gemini API 키를 입력해주세요.")
    else:
        st.success("Gemini API 연결 완료")


# --- [핵심] 상단 네비바 (햄버거 메뉴 카테고리 및 로고 아이콘만 유지) ---
is_video_loaded = bool(st.session_state.video_id and st.session_state.video_info and st.session_state.transcript_data)

st.markdown("""
<div class="yt-nav-header-left" style="margin-bottom: 6px;">
    <button type="button" id="yt-hamburger-btn" class="yt-menu-icon" title="이전 목록 열기" style="background:none; border:none; padding:0; cursor:pointer; display:flex; align-items:center; justify-content:center;">
        <svg viewBox="0 0 24 24" width="22" height="22" fill="#ffffff">
            <path d="M3 18h18v-2H3v2zm0-5h18v-2H3v2zm0-7v2h18V6H3z"/>
        </svg>
    </button>
    <a href="?home=true" target="_self" class="yt-logo-link" title="홈으로 돌아가기">
        <svg width="28" height="20" viewBox="0 0 32 23" fill="none">
            <path d="M31.24 3.49C30.87 2.12 29.8 1.05 28.43 0.68C25.96 0 16 0 16 0C16 0 6.04 0 3.57 0.68C2.2 1.05 1.13 2.12 0.76 3.49C0 5.96 0 11.1 0 11.1C0 11.1 0 16.24 0.76 18.71C1.13 20.08 2.2 21.15 3.57 21.52C6.04 22.2 16 22.2 16 22.2C16 22.2 25.96 22.2 28.43 21.52C29.8 21.15 30.87 20.08 31.24 18.71C32 16.24 32 11.1 32 11.1C32 11.1 32 5.96 31.24 3.49Z" fill="#FF0000"/>
            <polygon points="12.8,15.8 21.2,11.1 12.8,6.4" fill="#FFFFFF"/>
        </svg>
        <span class="yt-wordmark">YouTube</span>
        <span class="yt-country-code">KR</span>
    </a>
</div>
""", unsafe_allow_html=True)

url_input = ""
search_submit = False

# --- [반응형 사이드 드로어 마크업 & 카테고리 목록 & 캐시 보관함] ---
cached_videos_list = get_all_cached_videos()
cached_cards_html = ""

if cached_videos_list:
    for cv in cached_videos_list:
        v_t_esc = cv['title'].replace('"', '&quot;').replace("'", "&#39;")
        v_u_esc = cv['uploader'].replace('"', '&quot;').replace("'", "&#39;")
        cached_cards_html += f"""<div class="d-video-card" data-title="{v_t_esc.lower()}" data-uploader="{v_u_esc.lower()}">
<a href="?load_cache={cv['video_id']}" target="_self" class="d-card-link" title="{v_t_esc}">
<div class="d-info-box">
<div class="d-title">{v_t_esc}</div>
<div class="d-uploader">{v_u_esc}</div>
<div class="d-footer-row">
<span class="d-dur-tag-inline">{cv['duration_str']}</span>
<span class="d-token-tag">저장됨</span>
<span class="d-date-tag">{cv.get('segment_count', 0)}개 구간</span>
</div>
</div>
</a>
<a href="?delete_cache={cv['video_id']}" target="_self" class="d-del-btn" title="보관함에서 삭제" onclick="return confirm('이 영상의 분석 캐시를 삭제하시겠습니까?');">
<svg viewBox="0 0 24 24" width="16" height="16" fill="#888">
<path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/>
</svg>
</a>
</div>"""
else:
    cached_cards_html = """<div class="d-empty-box">
<div style="font-weight: 700; color: #ffffff; margin-bottom: 4px; font-size: 0.95rem;">보관된 영상이 없습니다</div>
<div style="font-size: 0.8rem; color: #888888; line-height: 1.4;">상단에서 유튜브 링크를 분석하면<br>여기에 자동으로 영구 보관되어<br>언제든 대본을 다시 볼 수 있습니다.</div>
</div>"""

clear_btn_html = f'<div class="d-panel-footer"><a href="?clear_all_cache=true" target="_self" class="d-clear-all-btn" onclick="return confirm(\'정말 모든 분석 캐시를 삭제하시겠습니까?\');">전체 보관함 비우기</a></div>' if cached_videos_list else ''

raw_drawer_html = f"""
<div id="yt-drawer-backdrop" class="yt-drawer-backdrop" title="메뉴 닫기"></div>
<div id="yt-drawer-panel" class="yt-drawer-panel">
<div class="d-panel-header">
<button type="button" id="d-close-drawer-btn" class="d-close-drawer-btn yt-menu-icon" title="메뉴 닫기" style="background:none; border:none; padding:0; cursor:pointer; display:flex; align-items:center; justify-content:center;">
<svg viewBox="0 0 24 24" width="22" height="22" fill="#ffffff">
<path d="M3 18h18v-2H3v2zm0-5h18v-2H3v2zm0-7v2h18V6H3z"/>
</svg>
</button>
<span style="font-weight: 700; font-size: 1.05rem; color: #ffffff; margin-left: 12px; letter-spacing: -0.3px;">이전 목록</span>
</div>
<div class="d-panel-body">
<div class="d-section-header">
<div style="display: flex; align-items: center; gap: 6px;">
<span style="font-weight: 700; font-size: 0.95rem; color: #ffffff;">분석 완료 영상 목록</span>
</div>
<span class="d-count-pill">{len(cached_videos_list)}개 저장</span>
</div>
<div class="d-search-box">
<input type="text" id="d-drawer-search-input" placeholder="보관된 영상 검색..." oninput="if(window.parent.filterDrawerVideos)window.parent.filterDrawerVideos(this.value)" class="d-search-input" />
</div>
<div class="d-scroll-area" id="d-video-list-scroll">
{cached_cards_html}
<div id="d-filter-empty" style="display:none; text-align:center; padding:30px 10px; color:#777; font-size:0.8rem;">
검색된 영상이 없습니다.
</div>
</div>
{clear_btn_html}
</div>
</div>
"""
clean_drawer_html = "\n".join(l.strip() for l in raw_drawer_html.splitlines() if l.strip())
st.markdown(clean_drawer_html, unsafe_allow_html=True)

# 브라우저 DOM 이벤트 및 햄버거 메뉴 토글 / 바깥 영역 클릭 닫기 제어 스크립트 iframe 주입
components.html("""
<script>
(function() {
    try {
        const pDoc = window.parent.document;
        if (!pDoc) return;
        
        window.parent.openDrawer = function() {
            const bd = pDoc.getElementById('yt-drawer-backdrop');
            const pn = pDoc.getElementById('yt-drawer-panel');
            if (bd) bd.classList.add('open');
            if (pn) pn.classList.add('open');
        };
        window.parent.closeDrawer = function() {
            const bd = pDoc.getElementById('yt-drawer-backdrop');
            const pn = pDoc.getElementById('yt-drawer-panel');
            if (bd) bd.classList.remove('open');
            if (pn) pn.classList.remove('open');
        };
        window.parent.toggleDrawer = function() {
            const pn = pDoc.getElementById('yt-drawer-panel');
            if (pn && pn.classList.contains('open')) {
                window.parent.closeDrawer();
            } else {
                window.parent.openDrawer();
            }
        };

        window.parent.filterDrawerVideos = function(query) {
            const q = (query || '').toLowerCase().trim();
            const cards = pDoc.querySelectorAll('.d-video-card');
            let matchCount = 0;
            cards.forEach(function(card) {
                const title = (card.getAttribute('data-title') || '').toLowerCase();
                const uploader = (card.getAttribute('data-uploader') || '').toLowerCase();
                if (!q || title.includes(q) || uploader.includes(q)) {
                    card.style.display = 'flex';
                    matchCount++;
                } else {
                    card.style.display = 'none';
                }
            });
            const emptyNotice = pDoc.getElementById('d-filter-empty');
            if (emptyNotice) {
                emptyNotice.style.display = (matchCount === 0 && cards.length > 0) ? 'block' : 'none';
            }
        };

        window.parent.filterDrawerCategory = function(cat, btnElem) {
            if (btnElem) {
                const chips = pDoc.querySelectorAll('.d-cat-chip');
                chips.forEach(c => c.classList.remove('active'));
                btnElem.classList.add('active');
            }
            const input = pDoc.getElementById('d-drawer-search-input');
            if (cat === 'all') {
                if (input) input.value = '';
                window.parent.filterDrawerVideos('');
            } else {
                if (input) input.value = cat;
                window.parent.filterDrawerVideos(cat);
            }
        };

        // 기존 이벤트 리스너 중복 방지 정리
        if (pDoc.__yt_drawer_click_handler) {
            pDoc.removeEventListener('click', pDoc.__yt_drawer_click_handler, true);
        }
        if (pDoc.__yt_drawer_key_handler) {
            pDoc.removeEventListener('keydown', pDoc.__yt_drawer_key_handler);
        }

        pDoc.__yt_drawer_click_handler = function(e) {
            // 1. 햄버거 메뉴바 버튼 클릭 시: 토글 동작 (열려있으면 닫고, 닫혀있으면 엶)
            const hamBtn = e.target.closest('#yt-hamburger-btn');
            if (hamBtn) {
                e.preventDefault();
                e.stopPropagation();
                window.parent.toggleDrawer();
                return;
            }

            // 2. 드로어 상단 닫기 버튼 클릭 시: 닫기
            const closeBtn = e.target.closest('#d-close-drawer-btn, .d-close-drawer-btn');
            if (closeBtn) {
                e.preventDefault();
                e.stopPropagation();
                window.parent.closeDrawer();
                return;
            }

            // 3. 드로어 바깥 배경(Backdrop) 클릭 시: 닫기
            if (e.target.id === 'yt-drawer-backdrop' || e.target.classList.contains('yt-drawer-backdrop')) {
                e.preventDefault();
                e.stopPropagation();
                window.parent.closeDrawer();
                return;
            }

            // 4. 드로어가 열려있는 상태에서 카테고리/드로어 패널 영역 밖을 클릭한 경우: 닫기
            const pn = pDoc.getElementById('yt-drawer-panel');
            if (pn && pn.classList.contains('open')) {
                if (!pn.contains(e.target)) {
                    window.parent.closeDrawer();
                }
            }
        };

        pDoc.__yt_drawer_key_handler = function(e) {
            if (e.key === 'Escape') {
                window.parent.closeDrawer();
            }
        };

        // 캡처 단계에서 등록하여 어디서든 안정적으로 동작 보장
        pDoc.addEventListener('click', pDoc.__yt_drawer_click_handler, true);
        pDoc.addEventListener('keydown', pDoc.__yt_drawer_key_handler);

    } catch(err) {
        console.warn("[Drawer Script Warning]", err);
    }
})();
</script>
""", height=0)



# 다운로드 폴더
download_dir = os.path.join(os.path.dirname(__file__), "downloads")
os.makedirs(download_dir, exist_ok=True)


# --- 검색 및 분석 실행 ---
target_url = (
    st.session_state.get("home_url_input_box", "").strip()
    or (url_input or "").strip()
    or st.session_state.get("yt_url_input_box", "").strip()
    or st.session_state.get("current_url", "").strip()
)

if search_submit or st.session_state.get("trigger_search", False):
    st.session_state.trigger_search = False
    if not target_url:
        st.error("유튜브 영상 링크를 입력해주세요.")
    else:
        v_id = extract_video_id(target_url)
        if not v_id:
            st.error("올바른 유튜브 링크 형식이 아닙니다. (예: https://www.youtube.com/watch?v=...)")
        else:
            # [핵심 1] 이전에 분석한 영상인지 로컬 캐시 우선 확인 (Gemini API 0 토큰 소모)
            cached_data = load_from_cache(v_id)
            if cached_data:
                st.session_state.video_id = cached_data["video_id"]
                st.session_state.video_info = cached_data["video_info"]
                st.session_state.audio_path = cached_data.get("audio_path", "")
                st.session_state.transcript_data = cached_data["transcript_data"]
                st.session_state.chapters_data = cached_data.get("chapters_data", [])
                st.session_state.current_url = cached_data.get("url", target_url)
                st.session_state.chat_messages = []
                st.session_state.from_cache = True
                st.toast("이전에 분석된 영상입니다. 대본 페이지를 불러왔습니다.")
                st.rerun()
            elif not api_key_input.strip():
                st.error("신규 영상 분석을 위해 사이드바에서 Gemini API 키를 입력해주세요.")
            else:
                # [핵심 2] 신규 영상인 경우: 대본 생성 로딩 화면으로 전환 후 즉시 실행
                st.session_state.current_url = target_url
                st.session_state.is_analyzing = True
                st.session_state.target_analyze_url = target_url
                st.session_state.target_v_id = v_id
                st.rerun()


# --- 메인 화면 분기 (1: 대본 생성 중 로딩 화면 / 2: 분석 완료 대본 워크스페이스 / 3: 홈 검색 화면) ---
if st.session_state.get("is_analyzing", False):
    # 흰색 큰 텍스트 "대본 생성중" + 중앙 회전 로딩 스피너
    st.markdown("""
    <div class="generating-screen-container">
        <h1 class="generating-title">대본 생성중</h1>
        <div class="generating-spinner"></div>
    </div>
    """, unsafe_allow_html=True)

    t_url = st.session_state.get("target_analyze_url", "")
    t_vid = st.session_state.get("target_v_id", "")
    try:
        audio_path, video_info = download_audio(t_url, output_dir=download_dir)
        transcript_res = transcribe_with_timestamps(audio_path, api_key=api_key_input.strip())
        chapters = extract_video_chapters(
            segments=transcript_res.get("segments", []),
            full_text=transcript_res.get("full_text", ""),
            api_key=api_key_input.strip(),
        )
        st.session_state.video_id = t_vid
        st.session_state.video_info = video_info
        st.session_state.audio_path = audio_path
        st.session_state.transcript_data = transcript_res
        st.session_state.chapters_data = chapters
        st.session_state.chat_messages = []
        st.session_state.from_cache = False

        # 다음 재호출 시 0토큰으로 즉시 로드할 수 있도록 로컬 캐시에 자동 영구 저장
        save_to_cache(
            video_id=t_vid,
            video_info=video_info,
            audio_path=audio_path,
            transcript_data=transcript_res,
            chapters_data=chapters,
            url=t_url,
        )

        st.session_state.is_analyzing = False
        st.rerun()

    except Exception as e:
        st.session_state.is_analyzing = False
        st.error(f"대본 생성 중 오류가 발생했습니다: {e}")
        if st.button("홈 화면으로 돌아가기"):
            st.session_state.clear()
            st.rerun()

elif st.session_state.video_id and st.session_state.video_info and st.session_state.transcript_data:
    v_id = st.session_state.video_id
    v_info = st.session_state.video_info
    t_data = st.session_state.transcript_data
    chapters = st.session_state.chapters_data or []
    
    segments_list = t_data.get("segments", [])
    segments_json = json.dumps(segments_list, ensure_ascii=False)
    chapters_json = json.dumps(chapters, ensure_ascii=False)
    chat_json = json.dumps(st.session_state.chat_messages, ensure_ascii=False)
    v_title = v_info.get("title", "유튜브 영상")
    v_uploader = v_info.get("uploader", "채널명")
    v_duration_str = f"{v_info.get('duration', 0)//60}분 {v_info.get('duration', 0)%60}초"
    v_views = f"{v_info.get('view_count', 0):,}"
    api_key_clean = api_key_input.strip()

    safe_title = "".join(c for c in v_title if c.isalnum() or c in (" ", "_", "-")).rstrip()

    # 오디오 파일 크기 및 base64 인코딩 (다운로드 탭에서 0초 원클릭 다운로드용)
    audio_b64 = ""
    audio_size_str = "미추출"
    if st.session_state.audio_path and os.path.exists(st.session_state.audio_path):
        size_bytes = os.path.getsize(st.session_state.audio_path)
        if size_bytes < 1024 * 1024:
            audio_size_str = f"{size_bytes / 1024:.1f} KB"
        else:
            audio_size_str = f"{size_bytes / (1024 * 1024):.1f} MB"
        
        if size_bytes < 25 * 1024 * 1024:
            try:
                with open(st.session_state.audio_path, "rb") as f:
                    audio_b64 = base64.b64encode(f.read()).decode("utf-8")
            except Exception:
                audio_b64 = ""

    segments_count_val = len(segments_list)
    uploader_initial = v_uploader[0].upper() if v_uploader else "Y"
    is_from_cache = st.session_state.get("from_cache", False)
    cache_badge_html = ""

    # 전체 화면을 하나로 통합한 일체형 컴포넌트 HTML (좌측 플레이어/타임라인/상세정보 + 우측 4대 탭)
    integrated_html = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <style>
            @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
            @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap');
            
            * {{
                box-sizing: border-box;
                font-family: 'Pretendard', 'Roboto', sans-serif;
                margin: 0;
                padding: 0;
            }}
            body {{
                background: #0f0f0f;
                color: #f1f1f1;
                overflow: hidden;
            }}
            
            /* 2열 메인 컨테이너 (와이드 화면 및 축소 화면 모두 지원하는 반응형 컨테이너) */
            .app-container {{
                display: grid;
                grid-template-columns: 58fr 42fr;
                gap: 12px;
                width: 100%;
                height: 635px;
                max-height: 100vh;
                box-sizing: border-box;
                transition: all 0.25s ease;
            }}
            
            /*  유튜브 공식 영화관 모드 (Theater Mode) 전폭 레이아웃 */
            .app-container.theater-mode {{
                display: flex !important;
                flex-direction: column !important;
                gap: 14px !important;
                width: 100% !important;
                height: auto !important;
                max-height: none !important;
            }}
            .app-container.theater-mode .left-column {{
                width: 100% !important;
                height: auto !important;
                max-height: none !important;
                overflow: visible !important;
            }}
            .app-container.theater-mode .player-wrapper {{
                width: 100% !important;
                max-width: 100% !important;
                height: auto !important;
                max-height: min(72vh, 760px) !important;
                aspect-ratio: 16 / 9 !important;
                border-radius: 12px !important;
                background: #000 !important;
                box-shadow: 0 8px 32px rgba(0,0,0,0.9) !important;
            }}
            .app-container.theater-mode .yt-timeline-container {{
                margin-top: 3px !important;
            }}
            .app-container.theater-mode .yt-control-row {{
                margin-bottom: 3px !important;
            }}
            .app-container.theater-mode .yt-live-caption-box {{
                width: 100% !important;
            }}
            .app-container.theater-mode .right-column {{
                width: 100% !important;
                height: 580px !important;
                min-height: 520px !important;
                margin-top: 6px !important;
            }}
            
            /* ==================================================== */
            /*  좌측: 비디오 플레이어 + 타임라인 + 컨트롤 + 자막   */
            /* ==================================================== */
            .left-column {{
                display: flex;
                flex-direction: column;
                gap: 5px;
                height: 100%;
                min-height: 0;
                overflow: hidden;
                justify-content: flex-start;
            }}
            
            /* 대형/와이드 화면에서도 하단 컨트롤과 비디오 정보바가 잘리지 않도록 높이 자동 최적화 */
            .player-wrapper {{
                position: relative;
                width: 100%;
                max-width: 100%;
                max-height: calc(100% - 90px);
                aspect-ratio: 16 / 9;
                margin: 0 auto;
                background: #000;
                border-radius: 10px;
                overflow: hidden;
                box-shadow: 0 4px 20px rgba(0,0,0,0.8);
                flex: 0 1 auto;
                min-height: 0;
            }}
            .player-wrapper iframe {{
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                border: 0;
            }}
            
            /* 유튜브 정통 인터랙티브 타임라인 (시크바) */
            .yt-timeline-container {{
                position: relative;
                width: 100%;
                height: 16px;
                display: flex;
                align-items: center;
                cursor: pointer;
                user-select: none;
                flex-shrink: 0;
            }}
            .yt-timeline-track {{
                position: relative;
                width: 100%;
                height: 4px;
                background: rgba(255, 255, 255, 0.2);
                border-radius: 2px;
                transition: height 0.15s ease;
            }}
            .yt-timeline-container:hover .yt-timeline-track {{
                height: 7px;
            }}
            .yt-buffer-bar {{
                position: absolute;
                top: 0;
                left: 0;
                height: 100%;
                width: 0%;
                background: rgba(255, 255, 255, 0.35);
                border-radius: 2px;
                pointer-events: none;
            }}
            .yt-hover-bar {{
                position: absolute;
                top: 0;
                left: 0;
                height: 100%;
                width: 0%;
                background: rgba(255, 255, 255, 0.25);
                border-radius: 2px;
                pointer-events: none;
            }}
            .yt-play-bar {{
                position: absolute;
                top: 0;
                left: 0;
                height: 100%;
                width: 0%;
                background: #ff0000;
                border-radius: 2px;
                pointer-events: none;
            }}
            .yt-scrubber-handle {{
                position: absolute;
                top: 50%;
                transform: translate(-50%, -50%) scale(0);
                width: 13px;
                height: 13px;
                border-radius: 50%;
                background: #ff0000;
                transition: transform 0.15s ease;
                pointer-events: none;
                box-shadow: 0 0 4px rgba(255,0,0,0.8);
            }}
            .yt-timeline-container:hover .yt-scrubber-handle {{
                transform: translate(-50%, -50%) scale(1);
            }}
            
            /* 마우스 호버 시 뜨는 썸네일 + 분초 툴팁 */
            .yt-hover-tooltip {{
                position: absolute;
                bottom: 22px;
                transform: translateX(-50%);
                background: #181818;
                border: 1px solid #383838;
                border-radius: 8px;
                padding: 4px;
                box-shadow: 0 6px 16px rgba(0,0,0,0.9);
                display: none;
                pointer-events: none;
                z-index: 1000;
                text-align: center;
            }}
            .yt-tooltip-thumb {{
                width: 132px;
                height: 74px;
                border-radius: 5px;
                object-fit: cover;
                display: block;
                margin-bottom: 3px;
            }}
            .yt-tooltip-time {{
                color: #ffffff;
                font-size: 0.78rem;
                font-weight: 700;
                font-variant-numeric: tabular-nums;
                letter-spacing: 0.5px;
            }}
            
            /* 컨트롤 바: 볼륨 & 탐색 & 배속 & 시간 표시 */
            .yt-control-row {{
                display: flex;
                align-items: center;
                justify-content: space-between;
                background: #181818;
                border: 1px solid #272727;
                border-radius: 8px;
                padding: 4px 10px;
                gap: 8px;
                flex-shrink: 0;
                height: 34px;
            }}
            .yt-ctrl-left {{
                display: flex;
                align-items: center;
                gap: 8px;
                flex: 1;
            }}
            .ctrl-icon-btn {{
                background: transparent;
                border: none;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 2px;
                outline: none;
            }}
            .yt-vol-slider {{
                -webkit-appearance: none;
                width: 100%;
                max-width: 100px;
                height: 4px;
                border-radius: 2px;
                background: #333333;
                outline: none;
                cursor: pointer;
            }}
            .yt-vol-slider::-webkit-slider-thumb {{
                -webkit-appearance: none;
                width: 12px;
                height: 12px;
                border-radius: 50%;
                background: #ff0000;
                cursor: pointer;
            }}
            .yt-vol-badge {{
                font-size: 0.74rem;
                font-weight: 700;
                color: #ff4b4b;
                min-width: 32px;
            }}
            
            .yt-ctrl-center {{
                display: flex;
                align-items: center;
                gap: 5px;
            }}
            .skip-btn {{
                background: #242424;
                border: 1px solid #383838;
                color: #e0e0e0;
                border-radius: 6px;
                padding: 2px 7px;
                font-size: 0.72rem;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.15s;
            }}
            .skip-btn:hover {{
                background: #383838;
                color: #fff;
                border-color: #555;
            }}
            .speed-select {{
                background: #242424;
                border: 1px solid #383838;
                color: #3ea6ff;
                border-radius: 6px;
                padding: 2px 6px;
                font-size: 0.72rem;
                font-weight: 700;
                cursor: pointer;
                outline: none;
            }}
            
            .yt-ctrl-right {{
                display: flex;
                align-items: center;
                gap: 7px;
            }}
            .yt-time-badge {{
                font-size: 0.76rem;
                color: #aaaaaa;
                font-variant-numeric: tabular-nums;
                white-space: nowrap;
            }}
            .yt-theater-btn, .yt-fs-btn {{
                background: transparent;
                border: none;
                cursor: pointer;
                display: inline-flex;
                align-items: center;
                justify-content: center;
                padding: 3px 5px;
                border-radius: 4px;
                transition: all 0.15s ease;
                outline: none;
            }}
            .yt-theater-btn:hover, .yt-fs-btn:hover {{
                background: #2b2b32;
            }}
            .yt-theater-btn:hover svg, .yt-fs-btn:hover svg {{
                fill: #3ea6ff;
            }}
            .yt-theater-btn.active {{
                background: rgba(62, 166, 255, 0.18);
            }}
            .yt-theater-btn.active svg {{
                fill: #3ea6ff;
            }}
            
            /* 실시간 라이브 자막 바 */
            .yt-live-caption-box {{
                background: linear-gradient(180deg, #1f1f22 0%, #161618 100%);
                border: 1px solid #2d2d32;
                border-left: 5px solid #ff0000;
                border-radius: 9px;
                padding: 5px 12px;
                box-shadow: 0 4px 14px rgba(0, 0, 0, 0.5);
                display: flex;
                flex-direction: column;
                justify-content: center;
                min-height: 52px;
                max-height: 56px;
                flex-shrink: 0;
                width: 100%;
            }}
            .yt-live-head {{
                display: flex;
                align-items: center;
                justify-content: space-between;
                margin-bottom: 2px;
            }}
            .yt-live-tag {{
                display: inline-flex;
                align-items: center;
                gap: 5px;
                background: #ff0000;
                color: #ffffff;
                padding: 1px 7px;
                border-radius: 4px;
                font-size: 0.7rem;
                font-weight: 800;
                letter-spacing: 0.3px;
            }}
            .yt-live-dot {{
                width: 5px;
                height: 5px;
                background: #fff;
                border-radius: 50%;
                animation: pulse 1s infinite alternate;
            }}
            @keyframes pulse {{
                from {{ opacity: 0.2; }}
                to {{ opacity: 1; }}
            }}
            .copy-caption-btn {{
                background: #252528;
                border: 1px solid #3a3a40;
                color: #bbb;
                font-size: 0.68rem;
                font-weight: 600;
                padding: 1px 6px;
                border-radius: 4px;
                cursor: pointer;
                transition: all 0.15s;
            }}
            .copy-caption-btn:hover {{
                background: #333338;
                color: #fff;
                border-color: #3ea6ff;
            }}
            .yt-live-time {{
                color: #3ea6ff;
                font-size: 0.8rem;
                font-weight: 700;
                font-variant-numeric: tabular-nums;
            }}
            .yt-live-text {{
                color: #ffffff;
                font-size: 1.15rem;
                font-weight: 700;
                line-height: 1.35;
                letter-spacing: -0.2px;
                word-break: keep-all;
                overflow-wrap: break-word;
                display: -webkit-box;
                -webkit-line-clamp: 2;
                -webkit-box-orient: vertical;
                overflow: hidden;
                text-shadow: 0 1px 3px rgba(0,0,0,0.8);
            }}

            /*  영상 상세 정보 바 (100% 반응형 일체형 배너) */
            .video-info-banner {{
                background: #161616;
                border: 1px solid #282828;
                border-radius: 8px;
                padding: 6px 12px;
                min-height: 36px;
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 10px;
                flex-shrink: 0;
                width: 100%;
                box-sizing: border-box;
                transition: all 0.2s ease;
            }}
            .v-info-left {{
                display: flex;
                align-items: center;
                gap: 8px;
                min-width: 0;
                flex: 1 1 auto;
            }}
            .v-uploader-avatar {{
                width: 24px;
                height: 24px;
                min-width: 24px;
                background: #7c4dff;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                color: #fff;
                font-size: 0.72rem;
                font-weight: 700;
                flex-shrink: 0;
            }}
            .v-info-title {{
                font-weight: 700;
                font-size: 0.86rem;
                color: #ffffff;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
                line-height: 1.3;
            }}
            .v-info-meta {{
                display: flex;
                align-items: center;
                gap: 8px;
                flex-shrink: 0;
                flex-wrap: wrap;
                margin-left: auto;
            }}
            .v-meta-item {{
                color: #aaaaaa;
                font-size: 0.75rem;
                white-space: nowrap;
            }}
            .v-meta-dot {{
                color: #555555;
            }}
            
            @media (max-width: 680px) {{
                .video-info-banner {{
                    flex-direction: column !important;
                    align-items: flex-start !important;
                    gap: 6px !important;
                    padding: 8px 10px !important;
                }}
                .v-info-left {{
                    width: 100% !important;
                }}
                .v-info-title {{
                    white-space: normal !important;
                    word-break: break-word !important;
                }}
                .v-info-meta {{
                    width: 100% !important;
                    margin-left: 0 !important;
                    gap: 6px !important;
                }}
            }}
            
            /* ========================================= */
            /*  우측: 카테고리 4대 탭 통합 사이드 패널 */
            /* ========================================= */
            .right-column {{
                background: #181818;
                border: 1px solid #272727;
                border-radius: 12px;
                padding: 9px;
                display: flex;
                flex-direction: column;
                height: 100%;
                min-height: 0;
                overflow: hidden;
            }}
            
            /*  [유튜브 공식 알약 필터 탭 바 - 카테고리 4대 탭] */
            .tab-nav-bar {{
                display: flex;
                align-items: center;
                gap: 8px;
                margin-bottom: 8px;
                padding: 2px 0 6px 0;
                overflow-x: auto;
                scrollbar-width: none;
                -ms-overflow-style: none;
                flex-shrink: 0;
            }}
            .tab-nav-bar::-webkit-scrollbar {{
                display: none;
            }}
            .tab-chip {{
                background-color: #272727;
                color: #f1f1f1;
                border: none;
                border-radius: 8px;
                padding: 6px 14px;
                font-size: 0.82rem;
                font-weight: 500;
                cursor: pointer;
                transition: background-color 0.15s ease, color 0.15s ease;
                display: inline-flex;
                align-items: center;
                gap: 6px;
                white-space: nowrap;
                user-select: none;
                line-height: 1.3;
            }}
            .tab-chip:hover {{
                background-color: #3f3f3f;
                color: #ffffff;
            }}
            .tab-chip.active {{
                background-color: #ffffff !important;
                color: #0f0f0f !important;
                font-weight: 700 !important;
            }}
            
            .tab-panel {{
                display: none;
                flex: 1;
                min-height: 0;
                flex-direction: column;
                overflow: hidden;
            }}
            .tab-panel.active {{
                display: flex;
            }}

            .search-box-wrap {{
                display: flex;
                align-items: center;
                gap: 8px;
                background: #141416;
                border: 1px solid #282830;
                border-radius: 8px;
                padding: 4px 10px;
                margin-bottom: 6px;
                height: 32px;
                flex-shrink: 0;
            }}
            .search-box-wrap input {{
                background: transparent;
                border: none;
                color: #fff;
                font-size: 0.8rem;
                width: 100%;
                outline: none;
            }}
            
            /* 정확히 5칸 크기로 채워지는 텔레프롬프터 뷰포트 컨테이너 */
            .transcript-5slots-container {{
                flex: 1;
                height: calc(100% - 38px);
                min-height: 0;
                overflow-y: auto;
                overflow-x: hidden;
                display: flex;
                flex-direction: column;
                gap: 7px;
                padding-right: 4px;
                scroll-behavior: smooth;
                position: relative;
            }}
            .transcript-5slots-container::-webkit-scrollbar {{
                width: 5px;
            }}
            .transcript-5slots-container::-webkit-scrollbar-thumb {{
                background: #25252c;
                border-radius: 3px;
            }}
            .transcript-5slots-container::-webkit-scrollbar-thumb:hover {{
                background: #3ea6ff;
            }}
            
            /* [핵심] 높이 계산: (100% - 4개의 간격(28px)) / 5 -> 뷰포트에 오차 없이 5칸만 100% 들어참 */
            .t-slot-card {{
                flex: 0 0 calc((100% - 28px) / 5);
                height: calc((100% - 28px) / 5);
                min-height: calc((100% - 28px) / 5);
                max-height: calc((100% - 28px) / 5);
                box-sizing: border-box;
                border-radius: 9px;
                padding: 8px 12px;
                display: flex;
                flex-direction: column;
                justify-content: center;
                cursor: pointer;
                transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
                background: #151518;
                border: 1px solid #26262e;
                position: relative;
                overflow: hidden;
            }}
            .t-slot-card:hover {{
                background: #202026;
                border-color: #444455;
            }}
            
            /* [3번째 칸] 현재 영상 음성 대본 슬롯 (중앙 집중 하이라이트) */
            .t-slot-card.active {{
                background: linear-gradient(135deg, #0e2a47 0%, #17426b 100%) !important;
                border: 2px solid #3ea6ff !important;
                box-shadow: 0 0 16px rgba(62, 166, 255, 0.45), inset 0 0 6px rgba(62, 166, 255, 0.15) !important;
                transform: scale(1.01);
                z-index: 2;
            }}
            
            .t-slot-header {{
                display: flex;
                align-items: center;
                justify-content: space-between;
                margin-bottom: 4px;
                line-height: 1;
            }}
            .t-time-btn {{
                background: #222228;
                color: #8fa0b5;
                font-size: 0.76rem;
                font-weight: 700;
                padding: 2px 6px;
                border-radius: 4px;
                white-space: nowrap;
                font-variant-numeric: tabular-nums;
            }}
            .t-slot-card.active .t-time-btn {{
                background: #3ea6ff;
                color: #071322;
                font-weight: 800;
            }}
            
            .t-live-badge {{
                display: none;
                align-items: center;
                gap: 5px;
                font-size: 0.72rem;
                font-weight: 700;
                color: #3ea6ff;
                background: rgba(62, 166, 255, 0.2);
                border: 1px solid rgba(62, 166, 255, 0.4);
                padding: 1px 7px;
                border-radius: 10px;
            }}
            .t-slot-card.active .t-live-badge {{
                display: inline-flex;
            }}
            .t-pulse-dot {{
                width: 6px;
                height: 6px;
                background: #3ea6ff;
                border-radius: 50%;
                animation: t-pulse 1.2s infinite;
            }}
            @keyframes t-pulse {{
                0% {{ transform: scale(0.85); opacity: 0.6; }}
                50% {{ transform: scale(1.35); opacity: 1; box-shadow: 0 0 6px #3ea6ff; }}
                100% {{ transform: scale(0.85); opacity: 0.6; }}
            }}
            
            /* 대본 텍스트 - 5칸 박스에 딱 맞게 폰트 크기와 줄 간격 최적화 */
            .t-content {{
                font-size: 0.95rem;
                color: #b0b0bc;
                line-height: 1.4;
                word-break: keep-all;
                overflow: hidden;
                display: -webkit-box;
                -webkit-line-clamp: 2;
                -webkit-box-orient: vertical;
            }}
            .t-slot-card.active .t-content {{
                color: #ffffff !important;
                font-size: 1.04rem !important;
                font-weight: 700 !important;
                line-height: 1.42 !important;
            }}
            
            /* 첫 대본이 3번째 칸에서 시작되도록 하는 상/하단 2칸 순수 빈 공간 */
            .t-empty-spacer {{
                flex: 0 0 calc((100% - 28px) / 5);
                height: calc((100% - 28px) / 5);
                min-height: calc((100% - 28px) / 5);
                max-height: calc((100% - 28px) / 5);
                box-sizing: border-box;
                visibility: hidden;
                pointer-events: none;
                user-select: none;
            }}
            
            /* ------------------------------------- */
            /*  카테고리 2: Gemini AI 챗봇           */
            /* ------------------------------------- */
            .preset-chips-row {{
                display: flex;
                gap: 5px;
                margin-bottom: 7px;
                flex-wrap: wrap;
            }}
            .preset-chip {{
                background: #242424;
                color: #3ea6ff;
                border: 1px solid #333333;
                border-radius: 12px;
                padding: 3px 8px;
                font-size: 0.72rem;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.15s;
            }}
            .preset-chip:hover {{
                background: #333333;
                color: #ffffff;
                border-color: #3ea6ff;
            }}
            .chat-messages-container {{
                flex: 1;
                overflow-y: auto;
                display: flex;
                flex-direction: column;
                gap: 8px;
                padding-right: 4px;
                margin-bottom: 8px;
            }}
            .chat-messages-container::-webkit-scrollbar {{
                width: 5px;
            }}
            .chat-messages-container::-webkit-scrollbar-thumb {{
                background: #333;
                border-radius: 3px;
            }}
            .chat-bubble-u {{
                background: #252e3e;
                color: #fff;
                padding: 7px 10px;
                border-radius: 10px 10px 2px 10px;
                align-self: flex-end;
                font-size: 0.8rem;
                max-width: 90%;
                line-height: 1.35;
            }}
            .chat-bubble-a {{
                background: #1f1f1f;
                border: 1px solid #2e2e2e;
                border-left: 3px solid #ff0000;
                color: #ececec;
                padding: 8px 11px;
                border-radius: 10px 10px 10px 2px;
                align-self: flex-start;
                font-size: 0.8rem;
                max-width: 96%;
                line-height: 1.4;
            }}
            .chat-input-row {{
                display: flex;
                gap: 6px;
            }}
            .chat-input {{
                flex: 1;
                background: #121212;
                border: 1px solid #333;
                border-radius: 16px;
                padding: 6px 12px;
                color: #fff;
                font-size: 0.8rem;
                outline: none;
            }}
            .chat-send-btn {{
                background: #cc0000;
                border: none;
                border-radius: 16px;
                color: #fff;
                padding: 6px 14px;
                font-size: 0.8rem;
                font-weight: 700;
                cursor: pointer;
            }}
            .chat-send-btn:hover {{
                background: #ff0000;
            }}
            
            /* ------------------------------------- */
            /*  카테고리 3: 주제별 챕터 요약        */
            /* ------------------------------------- */
            .chapters-scroll-view {{
                flex: 1;
                overflow-y: auto;
                display: flex;
                flex-direction: column;
                gap: 7px;
                padding-right: 4px;
            }}
            .chapters-scroll-view::-webkit-scrollbar {{
                width: 5px;
            }}
            .chapters-scroll-view::-webkit-scrollbar-thumb {{
                background: #333;
                border-radius: 3px;
            }}
            .ch-card {{
                background: #1f1f1f;
                border: 1px solid #2c2c2c;
                border-radius: 8px;
                padding: 8px 10px;
                cursor: pointer;
                transition: all 0.15s ease;
            }}
            .ch-card:hover {{
                background: #272727;
                border-color: #ff0000;
            }}
            .ch-card.active {{
                background: #2a1818;
                border-color: #ff0000;
                box-shadow: 0 0 8px rgba(255, 0, 0, 0.4);
            }}
            .ch-header {{
                display: flex;
                align-items: center;
                gap: 6px;
                margin-bottom: 4px;
            }}
            .ch-time {{
                background: #ff0000;
                color: #fff;
                font-size: 0.72rem;
                font-weight: 700;
                padding: 1px 6px;
                border-radius: 4px;
                font-variant-numeric: tabular-nums;
            }}
            .ch-title {{
                color: #fff;
                font-size: 0.85rem;
                font-weight: 700;
            }}
            .ch-desc {{
                color: #aaa;
                font-size: 0.78rem;
                line-height: 1.35;
            }}
            
            /* ------------------------------------- */
            /*  카테고리 4: 대본 및 오디오 다운로드 허브 */
            /* ------------------------------------- */
            .dl-panel-container {{
                flex: 1;
                overflow-y: auto;
                display: flex;
                flex-direction: column;
                gap: 10px;
                padding: 2px 2px;
            }}
            .dl-panel-container::-webkit-scrollbar {{
                width: 5px;
            }}
            .dl-panel-container::-webkit-scrollbar-thumb {{
                background: #333;
                border-radius: 3px;
            }}
            .dl-card {{
                background: #1e1e22;
                border: 1px solid #2e2e36;
                border-radius: 10px;
                padding: 12px 14px;
                display: flex;
                flex-direction: column;
                gap: 7px;
                transition: all 0.2s;
            }}
            .dl-card:hover {{
                border-color: #3ea6ff;
                box-shadow: 0 4px 12px rgba(0,0,0,0.5);
            }}
            .dl-card-header {{
                display: flex;
                align-items: center;
                gap: 10px;
            }}
            .dl-card-icon {{
                font-size: 1.4rem;
                width: 34px;
                height: 34px;
                background: #27272c;
                border-radius: 8px;
                display: flex;
                align-items: center;
                justify-content: center;
            }}
            .dl-card-title {{
                font-size: 0.9rem;
                font-weight: 700;
                color: #ffffff;
            }}
            .dl-card-desc {{
                font-size: 0.75rem;
                color: #888888;
                margin-top: 1px;
            }}
            .dl-meta-chips {{
                display: flex;
                gap: 6px;
                margin-top: 2px;
            }}
            .dl-chip {{
                background: #26262c;
                border: 1px solid #363640;
                color: #3ea6ff;
                font-size: 0.7rem;
                padding: 1px 7px;
                border-radius: 4px;
                font-weight: 600;
            }}
            .dl-card-actions {{
                display: flex;
                gap: 6px;
                margin-top: 4px;
                flex-wrap: wrap;
            }}
            .dl-act-btn {{
                flex: 1;
                min-width: 110px;
                border: none;
                border-radius: 7px;
                padding: 6px 10px;
                font-size: 0.76rem;
                font-weight: 700;
                cursor: pointer;
                transition: all 0.15s;
                text-align: center;
            }}
            .dl-act-btn.primary {{
                background: #cc0000;
                color: #fff;
            }}
            .dl-act-btn.primary:hover {{
                background: #ff0000;
            }}
            .dl-act-btn.primary.audio {{
                background: #0f2b4c;
                border: 1px solid #3ea6ff;
                color: #3ea6ff;
            }}
            .dl-act-btn.primary.audio:hover {{
                background: #194373;
                color: #fff;
            }}
            .dl-act-btn.secondary {{
                background: #27272b;
                border: 1px solid #3a3a42;
                color: #ddd;
            }}
            .dl-act-btn.secondary:hover {{
                background: #36363d;
                color: #fff;
            }}
            .dl-act-btn.copy {{
                background: #222226;
                border: 1px solid #333338;
                color: #aaa;
            }}
            .dl-act-btn.copy:hover {{
                background: #303038;
                color: #fff;
            }}

            /* 화면 크기에 따른 반응형 미디어 쿼리 */
            @media (max-width: 900px) {{
                body {{
                    overflow: hidden !important;
                }}
                .app-container {{
                    display: flex !important;
                    flex-direction: column !important;
                    height: auto !important;
                    min-height: 100% !important;
                    gap: 12px !important;
                }}
                .left-column {{
                    width: 100% !important;
                    height: auto !important;
                    flex-shrink: 0 !important;
                }}
                .player-wrapper {{
                    width: 100% !important;
                    max-height: none !important;
                    aspect-ratio: 16 / 9 !important;
                }}
                .right-column {{
                    width: 100% !important;
                    height: 540px !important;
                    min-height: 480px !important;
                    flex-shrink: 0 !important;
                    margin-top: 6px !important;
                }}
            }}

            @media (max-width: 520px) {{
                .yt-control-row {{
                    padding: 3px 6px !important;
                    gap: 4px !important;
                }}
                .yt-vol-slider {{
                    max-width: 50px !important;
                }}
                .yt-vol-badge {{
                    display: none !important;
                }}
                .skip-btn {{
                    padding: 2px 4px !important;
                    font-size: 0.68rem !important;
                }}
                .speed-select {{
                    padding: 2px 3px !important;
                    font-size: 0.68rem !important;
                }}
                .yt-time-badge {{
                    font-size: 0.68rem !important;
                }}
                .yt-theater-btn, .yt-fs-btn {{
                    padding: 2px 3px !important;
                }}
                .right-column {{
                    height: 480px !important;
                    min-height: 440px !important;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="app-container">
            <!-- ============================================== -->
            <!--  [좌측]: 비디오 + 타임라인 + 컨트롤 + 라이브자막 -->
            <!-- ============================================== -->
            <div class="left-column">
                <!-- 좌우 공백 없이 100% 꽉 채운 16:9 비디오 플레이어 -->
                <div class="player-wrapper">
                    <div id="yt-player"></div>
                </div>

                <!-- 유튜브 정통 타임라인 바 (마우스 호버 시 썸네일 & 분초 툴팁) -->
                <div class="yt-timeline-container" id="timeline-container">
                    <div class="yt-hover-tooltip" id="hover-tooltip">
                        <img class="yt-tooltip-thumb" id="tooltip-thumb" src="https://img.youtube.com/vi/{v_id}/mqdefault.jpg" alt="thumbnail">
                        <div class="yt-tooltip-time" id="tooltip-time">00:00</div>
                    </div>
                    <div class="yt-timeline-track" id="timeline-track">
                        <div class="yt-buffer-bar" id="buffer-bar"></div>
                        <div class="yt-hover-bar" id="hover-bar"></div>
                        <div class="yt-play-bar" id="play-bar"></div>
                        <div class="yt-scrubber-handle" id="scrubber-handle"></div>
                    </div>
                </div>

                <!-- 볼륨 및 배속, 탐색 제어 바 -->
                <div class="yt-control-row">
                    <div class="yt-ctrl-left">
                        <button class="ctrl-icon-btn" onclick="toggleMute()" id="mute-btn" title="음소거 토글 (m)">
                            <svg id="speaker-icon" width="16" height="16" viewBox="0 0 24 24" fill="#ff0000">
                                <path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"/>
                            </svg>
                        </button>
                        <input type="range" class="yt-vol-slider" min="0" max="100" value="100" oninput="changeVol(this.value)">
                        <span class="yt-vol-badge" id="vol-badge">100%</span>
                    </div>
                    <div class="yt-ctrl-center">
                        <button class="skip-btn" onclick="skipRelative(-5)" title="5초 뒤로 (J)">-5s</button>
                        <button class="skip-btn" onclick="skipRelative(5)" title="5초 앞으로 (L)">+5s</button>
                        <select class="speed-select" onchange="changeSpeed(this.value)" id="speed-selector" title="재생 속도 조절">
                            <option value="0.75">0.75x</option>
                            <option value="1.0" selected>1.0x (보통)</option>
                            <option value="1.25">1.25x</option>
                            <option value="1.5">1.5x</option>
                            <option value="2.0">2.0x</option>
                        </select>
                    </div>
                    <div class="yt-ctrl-right">
                        <div class="yt-time-badge">
                            <span id="time-current">00:00</span> / <span id="time-total">00:00</span>
                        </div>
                        <!-- 유튜브 공식 영화관 모드 (Theater Mode) 버튼 -->
                        <button class="ctrl-icon-btn yt-theater-btn" id="theater-toggle-btn" onclick="toggleTheaterMode()" title="영화관 모드 (t)">
                            <svg id="theater-icon-enter" viewBox="0 0 24 24" width="18" height="18" fill="#f1f1f1">
                                <path d="M19 6H5c-1.1 0-2 .9-2 2v8c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2zm0 10H5V8h14v8z"/>
                            </svg>
                            <svg id="theater-icon-exit" viewBox="0 0 24 24" width="18" height="18" fill="#3ea6ff" style="display: none;">
                                <path d="M19 7H5c-1.1 0-2 .9-2 2v6c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V9c0-1.1-.9-2-2-2zm0 8H5V9h14v6z"/>
                            </svg>
                        </button>
                        <!-- 전체화면 버튼 -->
                        <button class="ctrl-icon-btn yt-fs-btn" id="fs-toggle-btn" onclick="toggleFullscreen()" title="전체화면 (f)">
                            <svg viewBox="0 0 24 24" width="17" height="17" fill="#f1f1f1">
                                <path d="M7 14H5v5h5v-2H7v-3zm-2-4h2V7h3V5H5v5zm12 7h-3v2h5v-5h-2v3zM14 5v2h3v3h2V5h-5z"/>
                            </svg>
                        </button>
                    </div>
                </div>

                <!-- 영상 상세 정보 배너 (일체형 반응형 배너) -->
                <div class="video-info-banner" title="{v_title}">
                    <div class="v-info-left">
                        <div class="v-uploader-avatar">{uploader_initial}</div>
                        <span class="v-info-title">{v_title}</span>
                    </div>
                    <div class="v-info-meta">
                        <span class="v-meta-item">{v_uploader}</span>
                        <span class="v-meta-dot">•</span>
                        <span class="v-meta-item">조회수 {v_views}회</span>
                        <span class="v-meta-dot">•</span>
                        <span class="v-meta-item">{v_duration_str}</span>
                    </div>
                </div>
            </div>

            <!-- ============================================== -->
            <!-- [우측]: 카테고리 4대 탭 통합 사이드 패널   -->
            <!-- ============================================== -->
            <div class="right-column">
                <div class="tab-nav-bar">
                    <button class="tab-chip active" id="tab-btn-transcript" onclick="switchTab('transcript')">대본</button>
                    <button class="tab-chip" id="tab-btn-chat" onclick="switchTab('chat')">Gemini 챗봇</button>
                    <button class="tab-chip" id="tab-btn-chapters" onclick="switchTab('chapters')">챕터</button>
                    <button class="tab-chip" id="tab-btn-download" onclick="switchTab('download')">다운로드</button>
                </div>

                <!-- 1. 시간대별 대본 탭 (5칸 맞춤 & 3번째 칸 실시간 음성 대본 싱크) -->
                <div class="tab-panel active" id="panel-transcript">
                    <div class="search-box-wrap">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="#888">
                            <path d="M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/>
                        </svg>
                        <input type="text" id="t-search-input" placeholder="대본 내용 실시간 검색..." oninput="onFilterTranscript(this.value)">
                        <span style="font-size: 0.76rem; color: #3ea6ff; font-weight: 600; white-space: nowrap;" id="t-count-badge"></span>
                    </div>

                    <div class="transcript-5slots-container" id="transcript-container"></div>
                </div>

                <!-- 2. Gemini AI 챗봇 탭 -->
                <div class="tab-panel" id="panel-chat">
                    <div class="preset-chips-row">
                        <span class="preset-chip" onclick="askPreset('이 영상의 가장 중요한 핵심 내용을 3줄로 요약해줘.')">3줄 핵심 요약</span>
                        <span class="preset-chip" onclick="askPreset('영상의 최종 결론과 화자의 핵심 메시지는 뭐야?')">최종 결론</span>
                        <span class="preset-chip" onclick="askPreset('영상에서 다루는 주요 이슈와 원인은 무엇인가요?')">주요 원인 분석</span>
                        <span class="preset-chip" onclick="askPreset('영상 속에 등장하는 핵심 개념과 키워드를 정리해줘.')">핵심 키워드 정리</span>
                        <span class="preset-chip" onclick="askPreset('영상 내용 중 시청자가 꼭 알아야 할 주요 사실(Fact)을 Q&A로 정리해줘.')">Q&A 팩트체크</span>
                    </div>

                    <div class="chat-messages-container" id="chat-box">
                        <div class="chat-bubble-a">
                            <b>Gemini AI 어시스턴트:</b><br>
                            영상 내용에 대해 궁금한 점을 질문해보세요. 상단 추천 질문 칩을 누르거나 직접 입력하시면 관련 영상 구간과 함께 즉시 답변해 드립니다.
                        </div>
                    </div>

                    <div class="chat-input-row">
                        <input type="text" class="chat-input" id="chat-input-field" placeholder="영상에 대해 질문하세요..." onkeydown="if(event.key==='Enter') sendChatQuestion()">
                        <button class="chat-send-btn" onclick="sendChatQuestion()">전송</button>
                    </div>
                </div>

                <!-- 3. 주제별 챕터 요약 탭 -->
                <div class="tab-panel" id="panel-chapters">
                    <div class="chapters-scroll-view" id="chapters-container"></div>
                </div>

                <!-- 4. 대본 및 오디오 다운로드 허브 탭 -->
                <div class="tab-panel" id="panel-download">
                    <div class="dl-panel-container">
                        <!-- 1. 전체 대본 카드 -->
                        <div class="dl-card">
                            <div class="dl-card-header">
                                <div class="dl-card-icon">TXT</div>
                                <div>
                                    <div class="dl-card-title">전체 텍스트 대본 (.txt)</div>
                                    <div class="dl-card-desc">Gemini AI가 전사한 텍스트 대본 파일</div>
                                </div>
                            </div>
                            <div class="dl-meta-chips">
                                <span class="dl-chip">총 {segments_count_val}개 발화</span>
                                <span class="dl-chip">UTF-8 포맷</span>
                            </div>
                            <div class="dl-card-actions">
                                <button class="dl-act-btn primary" onclick="downloadTranscriptTxt(false)">텍스트 다운로드</button>
                                <button class="dl-act-btn secondary" onclick="downloadTranscriptTxt(true)">타임스탬프 포함</button>
                                <button class="dl-act-btn copy" id="copy-all-btn" onclick="copyAllTranscript()">전체 복사</button>
                            </div>
                        </div>

                        <!-- 2. 고음질 오디오 카드 -->
                        <div class="dl-card">
                            <div class="dl-card-header">
                                <div class="dl-card-icon">MP3</div>
                                <div>
                                    <div class="dl-card-title">고음질 원본 오디오 (.m4a)</div>
                                    <div class="dl-card-desc">유튜브 원본 고음질 AAC/M4A 스트림 파일</div>
                                </div>
                            </div>
                            <div class="dl-meta-chips">
                                <span class="dl-chip">용량: {audio_size_str}</span>
                                <span class="dl-chip">길이: {v_duration_str}</span>
                            </div>
                            <div class="dl-card-actions">
                                <button class="dl-act-btn primary audio" onclick="downloadAudioFile()">고음질 오디오 다운로드</button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <script>
            var segments = {segments_json};
            var chapters = {chapters_json};
            var player;
            var currentActiveIdx = -1;
            var isUserScrolling = false;
            var scrollTimeout;
            var apiKey = "{api_key_clean}";
            var isExpandedView = false;
            var isTheaterMode = false;
            var isMuted = false;
            var lastVolume = 100;
            var videoTitleSafe = "{safe_title}";

            // YouTube IFrame API 로드
            var tag = document.createElement('script');
            tag.src = "https://www.youtube.com/iframe_api";
            var firstScriptTag = document.getElementsByTagName('script')[0];
            firstScriptTag.parentNode.insertBefore(tag, firstScriptTag);

            function onYouTubeIframeAPIReady() {{
                player = new YT.Player('yt-player', {{
                    videoId: '{v_id}',
                    playerVars: {{
                        'autoplay': 1,
                        'playsinline': 1,
                        'rel': 0,
                        'modestbranding': 1
                    }},
                    events: {{
                        'onReady': onPlayerReady
                    }}
                }});
            }}

            function fmtSec(sec) {{
                var total = Math.floor(Math.max(0, sec));
                var h = Math.floor(total / 3600);
                var m = Math.floor((total % 3600) / 60);
                var s = total % 60;
                if (h > 0) {{
                    return (h < 10 ? "0" + h : h) + ":" + (m < 10 ? "0" + m : m) + ":" + (s < 10 ? "0" + s : s);
                }}
                return (m < 10 ? "0" + m : m) + ":" + (s < 10 ? "0" + s : s);
            }}

            function onPlayerReady(event) {{
                event.target.setVolume(100);
                event.target.playVideo();
                renderTranscriptList(segments);
                renderChapters(chapters);

                var dur = event.target.getDuration();
                if (dur > 0) {{
                    document.getElementById('time-total').innerText = fmtSec(dur);
                }}

                // 150ms 고속 정밀 싱크 타이머
                setInterval(syncPlaybackAndTranscript, 150);
            }}

            function changeVol(v) {{
                if (player && player.setVolume) {{
                    player.setVolume(v);
                    lastVolume = v;
                    document.getElementById('vol-badge').innerText = v + "%";
                    if (v > 0 && isMuted) {{
                        isMuted = false;
                        player.unMute();
                    }}
                }}
            }}

            function toggleMute() {{
                if (!player) return;
                var slider = document.querySelector('.yt-vol-slider');
                var badge = document.getElementById('vol-badge');
                if (isMuted) {{
                    player.unMute();
                    player.setVolume(lastVolume);
                    slider.value = lastVolume;
                    badge.innerText = lastVolume + "%";
                    isMuted = false;
                }} else {{
                    lastVolume = player.getVolume() || 100;
                    player.mute();
                    slider.value = 0;
                    badge.innerText = "0%";
                    isMuted = true;
                }}
            }}

            function skipRelative(delta) {{
                if (player && player.getCurrentTime && player.seekTo) {{
                    var cur = player.getCurrentTime();
                    var dur = player.getDuration() || 0;
                    var next = Math.max(0, Math.min(dur, cur + delta));
                    player.seekTo(next, true);
                }}
            }}

            function changeSpeed(rate) {{
                if (player && player.setPlaybackRate) {{
                    player.setPlaybackRate(parseFloat(rate));
                }}
            }}

            function jumpTo(sec) {{
                if (player && player.seekTo) {{
                    player.seekTo(sec, true);
                    player.playVideo();
                }}
            }}

            function copyLiveCaption() {{
                var txt = document.getElementById('live-text-display').innerText;
                if (!txt) return;
                var btn = document.getElementById('copy-cap-btn');
                navigator.clipboard.writeText(txt).then(function() {{
                    btn.innerText = "복사됨";
                    setTimeout(function() {{ btn.innerText = "복사"; }}, 1500);
                }}).catch(function() {{
                    btn.innerText = "실패";
                    setTimeout(function() {{ btn.innerText = "복사"; }}, 1500);
                }});
            }}

            // ----------------------------------------------------
            // 파일 다운로드 기능 (다운로드 탭 연동)
            // ----------------------------------------------------
            function downloadTranscriptTxt(withTimestamp) {{
                if (!segments || segments.length === 0) {{
                    alert("다운로드할 대본 데이터가 없습니다.");
                    return;
                }}
                var textLines;
                if (withTimestamp) {{
                    textLines = segments.map(function(s) {{
                        return "[" + s.time_str + "] " + s.text;
                    }});
                }} else {{
                    textLines = segments.map(function(s) {{
                        return s.text;
                    }});
                }}
                var fullText = textLines.join("\\n");
                var blob = new Blob([fullText], {{ type: "text/plain;charset=utf-8" }});
                var url = URL.createObjectURL(blob);
                var a = document.createElement("a");
                a.href = url;
                a.download = videoTitleSafe + (withTimestamp ? "_timestamps.txt" : "_transcript.txt");
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
            }}

            function copyAllTranscript() {{
                if (!segments || segments.length === 0) return;
                var fullText = segments.map(function(s) {{
                    return "[" + s.time_str + "] " + s.text;
                }}).join("\\n");
                navigator.clipboard.writeText(fullText).then(function() {{
                    var btn = document.getElementById('copy-all-btn');
                    if (btn) {{
                        btn.innerText = "전체 복사 완료";
                        setTimeout(function() {{ btn.innerText = "전체 복사"; }}, 1500);
                    }}
                }});
            }}

            function downloadAudioFile() {{
                var b64Data = "{audio_b64}";
                if (!b64Data) {{
                    alert("오디오 데이터가 준비되지 않았습니다.");
                    return;
                }}
                try {{
                    var byteCharacters = atob(b64Data);
                    var byteNumbers = new Array(byteCharacters.length);
                    for (var i = 0; i < byteCharacters.length; i++) {{
                        byteNumbers[i] = byteCharacters.charCodeAt(i);
                    }}
                    var byteArray = new Uint8Array(byteNumbers);
                    var blob = new Blob([byteArray], {{ type: "audio/m4a" }});
                    var url = URL.createObjectURL(blob);
                    var a = document.createElement("a");
                    a.href = url;
                    a.download = videoTitleSafe + ".m4a";
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    URL.revokeObjectURL(url);
                }} catch(e) {{
                    alert("오디오 다운로드 중 오류: " + e.message);
                }}
            }}

            // ----------------------------------------------------
            // [핵심 1] 유튜브 마우스 호버 타임라인 & 썸네일/시간대 툴팁
            // ----------------------------------------------------
            var timelineContainer = document.getElementById('timeline-container');
            var hoverTooltip = document.getElementById('hover-tooltip');
            var tooltipTime = document.getElementById('tooltip-time');
            var hoverBar = document.getElementById('hover-bar');
            var playBar = document.getElementById('play-bar');
            var scrubberHandle = document.getElementById('scrubber-handle');

            timelineContainer.addEventListener('mousemove', function(e) {{
                if (!player || !player.getDuration) return;
                var dur = player.getDuration();
                if (!dur || dur <= 0) return;

                var rect = timelineContainer.getBoundingClientRect();
                var clickX = e.clientX - rect.left;
                var ratio = Math.max(0, Math.min(1, clickX / rect.width));
                var hoverSeconds = ratio * dur;

                hoverBar.style.width = (ratio * 100) + "%";
                hoverTooltip.style.display = 'block';
                var clampedX = Math.max(70, Math.min(rect.width - 70, clickX));
                hoverTooltip.style.left = clampedX + "px";
                tooltipTime.innerText = fmtSec(hoverSeconds);
            }});

            timelineContainer.addEventListener('mouseleave', function() {{
                hoverTooltip.style.display = 'none';
                hoverBar.style.width = "0%";
            }});

            timelineContainer.addEventListener('click', function(e) {{
                if (!player || !player.getDuration) return;
                var dur = player.getDuration();
                if (!dur || dur <= 0) return;

                var rect = timelineContainer.getBoundingClientRect();
                var ratio = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
                jumpTo(ratio * dur);
            }});

            // ----------------------------------------------------
            // [핵심 2] 정확히 5칸 크기 뷰포트 & 3번째 칸 실시간 음성 대본 고정 싱크
            // ----------------------------------------------------
            var tContainer = document.getElementById('transcript-container');
            var isUserScrolling = false;
            var scrollTimeout;

            tContainer.addEventListener('wheel', function() {{
                isUserScrolling = true;
                clearTimeout(scrollTimeout);
                scrollTimeout = setTimeout(function() {{
                    isUserScrolling = false;
                }}, 2500);
            }}, {{ passive: true }});

            tContainer.addEventListener('touchmove', function() {{
                isUserScrolling = true;
                clearTimeout(scrollTimeout);
                scrollTimeout = setTimeout(function() {{
                    isUserScrolling = false;
                }}, 2500);
            }}, {{ passive: true }});

            function syncPlaybackAndTranscript(forceSync) {{
                if (!player || !player.getCurrentTime) return;
                var cur = player.getCurrentTime();
                var dur = player.getDuration() || 1;

                // 1. 타임라인 진행률 바 업데이트
                var pct = Math.max(0, Math.min(100, (cur / dur) * 100));
                playBar.style.width = pct + "%";
                scrubberHandle.style.left = pct + "%";
                document.getElementById('time-current').innerText = fmtSec(cur);

                if (dur > 1) {{
                    document.getElementById('time-total').innerText = fmtSec(dur);
                }}

                // 2. 현재 발화 세그먼트 탐색
                var targetIdx = -1;
                for (var i = 0; i < segments.length; i++) {{
                    if (cur >= segments[i].start && cur <= (segments[i].end + 0.35)) {{
                        targetIdx = i;
                        break;
                    }}
                }}
                if (targetIdx === -1) {{
                    for (var j = segments.length - 1; j >= 0; j--) {{
                        if (cur >= segments[j].start) {{
                            targetIdx = j;
                            break;
                        }}
                    }}
                }}

                // 3. 3번째 칸 현재 음성 대본 동기화
                if (targetIdx !== -1) {{
                    var curSeg = segments[targetIdx];
                    var liveTimeEl = document.getElementById('live-time-display');
                    if (liveTimeEl) liveTimeEl.innerText = curSeg.time_str;
                    var liveTextEl = document.getElementById('live-text-display');
                    if (liveTextEl) liveTextEl.innerText = curSeg.text;

                    if (targetIdx !== currentActiveIdx || forceSync) {{
                        currentActiveIdx = targetIdx;

                        var prev = document.querySelector('.t-slot-card.active');
                        if (prev) prev.classList.remove('active');

                        var activeEl = document.getElementById('t-card-' + targetIdx);
                        if (activeEl) {{
                            activeEl.classList.add('active');

                            if (!isUserScrolling || forceSync) {{
                                var slotH = activeEl.offsetHeight;
                                var gap = 7;
                                var targetScrollTop = targetIdx * (slotH + gap);
                                tContainer.scrollTo({{
                                    top: targetScrollTop,
                                    behavior: 'smooth'
                                }});
                            }}
                        }}
                    }}
                }}

                // 4. 챕터 활성 하이라이트 동기화
                if (chapters && chapters.length > 0) {{
                    for (var k = 0; k < chapters.length; k++) {{
                        var ch = chapters[k];
                        var chEl = document.getElementById('ch-card-' + k);
                        if (chEl) {{
                            var nextStart = (k + 1 < chapters.length) ? chapters[k+1].start_seconds : (dur + 1);
                            if (cur >= ch.start_seconds && cur < nextStart) {{
                                chEl.classList.add('active');
                            }} else {{
                                chEl.classList.remove('active');
                            }}
                        }}
                    }}
                }}
            }}

            // 대본 목록 렌더링 (첫 번째 대본이 3번째 칸에서 시작되도록 상하단에 2칸 빈 공간 배치)
            function renderTranscriptList(list) {{
                tContainer.innerHTML = "";
                var countBadge = document.getElementById('t-count-badge');
                if (countBadge) {{
                    countBadge.innerText = (list ? list.length : 0) + "개 발화";
                }}

                if (!list || list.length === 0) {{
                    tContainer.innerHTML = "<div style='color: #888; font-size: 0.9rem; text-align: center; padding: 60px;'>검색 결과가 없습니다.</div>";
                    return;
                }}

                // 상단 2칸 빈 공간 (아무 텍스트도 없는 투명 빈 박스)
                var topEmpty1 = document.createElement('div');
                topEmpty1.className = 't-empty-spacer';
                tContainer.appendChild(topEmpty1);

                var topEmpty2 = document.createElement('div');
                topEmpty2.className = 't-empty-spacer';
                tContainer.appendChild(topEmpty2);

                // 발화 카드 목록 (5칸 크기에 맞춘 큼직한 카드)
                list.forEach(function(s, idx) {{
                    var card = document.createElement('div');
                    card.className = 't-slot-card';
                    var realIdx = (s.orig_index !== undefined ? s.orig_index : idx);
                    card.id = 't-card-' + realIdx;
                    card.dataset.index = realIdx;
                    card.onclick = function() {{
                        jumpTo(s.start);
                    }};

                    card.innerHTML = 
                        '<div class="t-slot-header">' +
                            '<span class="t-time-btn">' + s.time_str + '</span>' +
                            '<span class="t-live-badge"><span class="t-pulse-dot"></span>현재 음성 대본</span>' +
                        '</div>' +
                        '<div class="t-content">' + s.text + '</div>';

                    tContainer.appendChild(card);
                }});

                // 하단 2칸 빈 공간 (마지막 대본들도 3번째 칸까지 위로 올라갈 수 있도록 여유 공간 제공)
                var btmEmpty1 = document.createElement('div');
                btmEmpty1.className = 't-empty-spacer';
                tContainer.appendChild(btmEmpty1);

                var btmEmpty2 = document.createElement('div');
                btmEmpty2.className = 't-empty-spacer';
                tContainer.appendChild(btmEmpty2);
            }}

            // 대본 검색 필터
            var indexedSegments = segments.map(function(s, idx) {{
                return {{ orig_index: idx, start: s.start, end: s.end, time_str: s.time_str, text: s.text }};
            }});

            function onFilterTranscript(q) {{
                var val = (q || '').trim().toLowerCase();
                var filtered = indexedSegments;
                if (val) {{
                    filtered = indexedSegments.filter(function(s) {{
                        return s.text.toLowerCase().indexOf(val) !== -1;
                    }});
                }}
                renderTranscriptList(filtered);
                var countBadge = document.getElementById('t-count-badge');
                if (countBadge) {{
                    countBadge.innerText = val ? filtered.length + '개 구간' : '';
                }}
                if (currentActiveIdx !== -1 && !val) {{
                    syncPlaybackAndTranscript(true);
                }}
            }}

            // 탭 전환
            function switchTab(name) {{
                document.querySelectorAll('.tab-chip').forEach(function(el) {{ el.classList.remove('active'); }});
                document.querySelectorAll('.tab-panel').forEach(function(el) {{ el.classList.remove('active'); }});

                var btn = document.getElementById('tab-btn-' + name);
                var panel = document.getElementById('panel-' + name);
                if (btn) btn.classList.add('active');
                if (panel) panel.classList.add('active');
            }}

            // ----------------------------------------------------
            // 챗봇 비동기 질의응답 (무중단 실시간 답변)
            // ----------------------------------------------------
            function askPreset(q) {{
                document.getElementById('chat-input-field').value = q;
                sendChatQuestion();
            }}

            async function sendChatQuestion() {{
                var inputEl = document.getElementById('chat-input-field');
                var question = inputEl.value.trim();
                if (!question) return;

                var chatBox = document.getElementById('chat-box');

                var uMsg = document.createElement('div');
                uMsg.className = 'chat-bubble-u';
                uMsg.innerHTML = '<b>질문:</b> ' + question;
                chatBox.appendChild(uMsg);
                inputEl.value = "";

                var loadMsg = document.createElement('div');
                loadMsg.className = 'chat-bubble-a';
                loadMsg.id = 'chat-loading-item';
                loadMsg.innerHTML = '<b>Gemini AI:</b> 답변을 생성하고 있습니다...';
                chatBox.appendChild(loadMsg);
                chatBox.scrollTop = chatBox.scrollHeight;

                if (!apiKey) {{
                    loadMsg.innerHTML = '좌측 사이드바에서 Gemini API 키를 먼저 입력해주세요.';
                    return;
                }}

                try {{
                    var nl = String.fromCharCode(10);
                    var timelineScript = segments.slice(0, 120).map(function(s) {{
                        return "[" + s.time_str + "] " + s.text;
                    }}).join(nl);

                    var promptText = [
                        "당신은 유튜브 영상 분석 전문가 AI입니다.",
                        "제공된 시간대별 영상 트랜스크립트를 확인하고 질문에 명쾌하고 친절하게 답변하세요.",
                        "답변과 가장 밀접한 영상 속 구간(시작 시간 예: 01:23 및 초 단위)을 찾아 반드시 아래 JSON으로만 응답하세요.",
                        "",
                        "[대본]",
                        timelineScript,
                        "",
                        "[질문]",
                        question,
                        "",
                        "[응답 형식]",
                        "```json",
                        "{{",
                        '  "answer": "답변 내용...",',
                        '  "relevant_timestamp": "00:02",',
                        '  "relevant_seconds": 2.0',
                        "}}",
                        "```"
                    ].join(nl);

                    var modelsToTry = ["gemini-3.5-flash", "gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-3-flash-preview", "gemini-3.8-flash"];
                    var data = null;
                    var lastErrorMsg = "";

                    for (var m = 0; m < modelsToTry.length; m++) {{
                        var modelName = modelsToTry[m];
                        try {{
                            var resp = await fetch("https://generativelanguage.googleapis.com/v1beta/models/" + modelName + ":generateContent?key=" + apiKey, {{
                                method: "POST",
                                headers: {{ "Content-Type": "application/json" }},
                                body: JSON.stringify({{
                                    contents: [{{ parts: [{{ text: promptText }}] }}]
                                }})
                            }});

                            var resJson = await resp.json();
                            if (resp.ok && resJson && resJson.candidates && resJson.candidates.length > 0 && resJson.candidates[0].content) {{
                                data = resJson;
                                break;
                            }} else if (resJson && resJson.error) {{
                                lastErrorMsg = resJson.error.message || ("오류 코드 " + resJson.error.code);
                            }}
                        }} catch(netErr) {{
                            lastErrorMsg = netErr.message;
                        }}
                    }}

                    if (!data || !data.candidates || data.candidates.length === 0 || !data.candidates[0].content) {{
                        throw new Error(lastErrorMsg || "API 응답을 수신하지 못했습니다. 잠시 후 다시 시도해주세요.");
                    }}

                    var parts = data.candidates[0].content.parts || [];
                    var rawText = "";
                    for (var p = 0; p < parts.length; p++) {{
                        if (parts[p].text) {{
                            rawText += parts[p].text;
                        }}
                    }}

                    if (!rawText.trim()) {{
                        throw new Error("답변 텍스트를 추출할 수 없습니다.");
                    }}
                    
                    var answerText = rawText;
                    var relTs = "00:00";
                    var relSec = 0;

                    var firstBrace = rawText.indexOf("{{");
                    var lastBrace = rawText.lastIndexOf("}}");
                    if (firstBrace !== -1 && lastBrace !== -1 && lastBrace > firstBrace) {{
                        try {{
                            var jsonStr = rawText.substring(firstBrace, lastBrace + 1);
                            var parsed = JSON.parse(jsonStr);
                            answerText = parsed.answer || rawText;
                            relTs = parsed.relevant_timestamp || "00:00";
                            relSec = parseFloat(parsed.relevant_seconds) || 0;
                        }} catch(e) {{}}
                    }}

                    loadMsg.remove();
                    var aMsg = document.createElement('div');
                    aMsg.className = 'chat-bubble-a';

                    var tsButton = "";
                    if (relSec > 0 || relTs !== "00:00") {{
                        tsButton = '<div style="margin-top: 6px;">' +
                            '<button onclick="jumpTo(' + relSec + ')" style="background: #0f2b4c; border: 1px solid #3ea6ff; color: #3ea6ff; font-size: 0.72rem; font-weight: 700; padding: 2px 8px; border-radius: 4px; cursor: pointer;">' +
                            '구간 바로가기: [' + relTs + '] (' + Math.floor(relSec) + '초)</button></div>';
                    }}

                    aMsg.innerHTML = '<div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 4px;">' +
                        '<span><b>Gemini AI:</b></span>' +
                        '<button onclick="copyChatText(this)" style="background: transparent; border: none; color: #888; font-size: 0.7rem; cursor: pointer;">복사</button>' +
                        '</div>' +
                        '<div class="chat-text-content">' + answerText.split(nl).join('<br>') + '</div>' + tsButton;
                    chatBox.appendChild(aMsg);
                    chatBox.scrollTop = chatBox.scrollHeight;

                }} catch(err) {{
                    loadMsg.remove();
                    var errMsg = document.createElement('div');
                    errMsg.className = 'chat-bubble-a';
                    errMsg.style.borderColor = '#ff4b4b';
                    errMsg.innerHTML = '답변 생성 중 오류가 발생했습니다: ' + err.message;
                    chatBox.appendChild(errMsg);
                    chatBox.scrollTop = chatBox.scrollHeight;
                }}
            }}

            function copyChatText(btn) {{
                var parent = btn.closest('.chat-bubble-a');
                var contentEl = parent.querySelector('.chat-text-content');
                if (contentEl) {{
                    navigator.clipboard.writeText(contentEl.innerText).then(function() {{
                        btn.innerText = "완료";
                        setTimeout(function() {{ btn.innerText = "복사"; }}, 1500);
                    }});
                }}
            }}

            // ----------------------------------------------------
            // 챕터 렌더링
            // ----------------------------------------------------
            function renderChapters(list) {{
                var container = document.getElementById('chapters-container');
                container.innerHTML = "";
                if (!list || list.length === 0) {{
                    container.innerHTML = "<div style='color: #888; font-size: 0.8rem; text-align: center; padding: 30px;'>추출된 주제 챕터가 없습니다.</div>";
                    return;
                }}
                list.forEach(function(ch, idx) {{
                    var card = document.createElement('div');
                    card.className = 'ch-card';
                    card.id = 'ch-card-' + idx;
                    card.onclick = function() {{ jumpTo(ch.start_seconds); }};
                    card.innerHTML = 
                        '<div class="ch-header">' +
                            '<span class="ch-time">' + ch.time_str + '</span>' +
                            '<span class="ch-title">' + ch.title + '</span>' +
                        '</div>' +
                        '<div class="ch-desc">' + ch.summary + '</div>';
                    container.appendChild(card);
                }});
            }}

            //  유튜브 공식 영화관 모드 (Theater Mode) 토글 함수
            function toggleTheaterMode() {{
                isTheaterMode = !isTheaterMode;
                var container = document.querySelector('.app-container');
                var enterIcon = document.getElementById('theater-icon-enter');
                var exitIcon = document.getElementById('theater-icon-exit');
                var btn = document.getElementById('theater-toggle-btn');
                
                if (isTheaterMode) {{
                    if (container) container.classList.add('theater-mode');
                    document.body.classList.add('theater-active');
                    if (enterIcon) enterIcon.style.display = 'none';
                    if (exitIcon) exitIcon.style.display = 'block';
                    if (btn) {{
                        btn.title = "기본 보기 (t)";
                        btn.classList.add('active');
                    }}
                    try {{ localStorage.setItem('yt_ai_theater_mode', 'true'); }} catch(e) {{}}
                }} else {{
                    if (container) {{
                        container.classList.remove('theater-mode');
                    }}
                    document.body.classList.remove('theater-active');
                    if (enterIcon) enterIcon.style.display = 'block';
                    if (exitIcon) exitIcon.style.display = 'none';
                    if (btn) {{
                        btn.title = "영화관 모드 (t)";
                        btn.classList.remove('active');
                    }}
                    try {{ localStorage.setItem('yt_ai_theater_mode', 'false'); }} catch(e) {{}}
                }}
                
                syncParentFrameHeight();
                setTimeout(syncParentFrameHeight, 150);
                setTimeout(syncParentFrameHeight, 350);
            }}

            //  전체화면 토글 함수
            function toggleFullscreen() {{
                var elem = document.querySelector('.player-wrapper') || document.documentElement;
                if (!document.fullscreenElement) {{
                    if (elem.requestFullscreen) {{
                        elem.requestFullscreen();
                    }} else if (elem.webkitRequestFullscreen) {{
                        elem.webkitRequestFullscreen();
                    }} else if (elem.msRequestFullscreen) {{
                        elem.msRequestFullscreen();
                    }}
                }} else {{
                    if (document.exitFullscreen) {{
                        document.exitFullscreen();
                    }}
                }}
            }}

            //  키보드 단축키 (t: 영화관 모드, f: 전체화면, m: 음소거)
            document.addEventListener('keydown', function(e) {{
                var target = e.target;
                if (target && (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable)) {{
                    return;
                }}
                if (e.key === 't' || e.key === 'T') {{
                    e.preventDefault();
                    toggleTheaterMode();
                }} else if (e.key === 'f' || e.key === 'F') {{
                    e.preventDefault();
                    toggleFullscreen();
                }} else if (e.key === 'm' || e.key === 'M') {{
                    e.preventDefault();
                    toggleMute();
                }}
            }});

            //  뷰 모드 및 반응형 화면 너비에 따른 최적 iframe 높이 정밀 계산 (중간 빈 공간/늘어짐 현상 원천 차단)
            function calculateOptimalHeight() {{
                if (isTheaterMode) {{
                    var leftCol = document.querySelector('.left-column');
                    var rightCol = document.querySelector('.right-column');
                    var hLeft = leftCol ? leftCol.getBoundingClientRect().height : 0;
                    var hRight = rightCol ? rightCol.getBoundingClientRect().height : 580;
                    return Math.max(Math.round(hLeft + hRight + 32), 1160);
                }}
                
                if (window.innerWidth <= 900) {{
                    var leftCol = document.querySelector('.left-column');
                    var rightCol = document.querySelector('.right-column');
                    var hLeft = leftCol ? leftCol.getBoundingClientRect().height : 0;
                    var hRight = rightCol ? rightCol.getBoundingClientRect().height : 540;
                    return Math.max(Math.round(hLeft + hRight + 24), 980);
                }}
                
                // 데스크톱 기본 2열 모드: 645px 고정 (화면을 줄였다가 되돌아왔을 때 공백 없이 즉시 완벽 밀착)
                return 645;
            }}

            // 브라우저 리사이즈 및 영화관 모드 전환 시 Streamlit iframe 높이 자동 동기화
            function syncParentFrameHeight() {{
                try {{
                    var targetH = calculateOptimalHeight();
                    window.parent.postMessage({{ type: "streamlit:setFrameHeight", height: targetH }}, "*");
                    if (window.frameElement) {{
                        window.frameElement.style.height = targetH + "px";
                        if (window.frameElement.parentElement) {{
                            window.frameElement.parentElement.style.height = targetH + "px";
                        }}
                    }}
                    if (window.parent && window.parent.document) {{
                        var iframes = window.parent.document.querySelectorAll('iframe');
                        iframes.forEach(function(f) {{
                            try {{
                                if (f.contentWindow === window || f === window.frameElement) {{
                                    f.style.height = targetH + "px";
                                    if (f.parentElement) {{
                                        f.parentElement.style.height = targetH + "px";
                                    }}
                                }}
                            }} catch(err) {{}}
                        }});
                    }}
                }} catch (e) {{}}
            }}
            window.addEventListener('resize', function() {{
                syncParentFrameHeight();
            }});
            window.addEventListener('load', function() {{
                try {{
                    if (localStorage.getItem('yt_ai_theater_mode') === 'true') {{
                        toggleTheaterMode();
                    }}
                }} catch(e) {{}}
                setTimeout(syncParentFrameHeight, 200);
            }});
        </script>
    </body>
    </html>
    """

    # 컴포넌트 높이 645px로 지정 (영화관 모드 시 JS syncParentFrameHeight로 동적 확장 및 원상 복구)
    components.html(integrated_html, height=645)


else:
    # --- 실시간 대본 AI 홈 화면 ---
    def on_home_search_submit():
        st.session_state.trigger_search = True

    # "실시간 대본 AI" 로고 텍스트
    st.markdown("""<div class="google-home-container">
<div class="google-logo-text">실시간 대본 AI</div>
</div>""", unsafe_allow_html=True)

    # 화이트 필 검색창 (검색 인풋 + '출력' 버튼만 유지)
    with st.form("google_home_search_form", clear_on_submit=False, border=False):
        c_in, c_submit = st.columns([85, 15], gap="small")
        with c_in:
            st.text_input(
                "유튜브 링크를 입력하세요.",
                value="",
                placeholder="유튜브 링크를 입력하세요.",
                label_visibility="collapsed",
                key="home_url_input_box",
            )
        with c_submit:
            home_submitted = st.form_submit_button("출력", on_click=on_home_search_submit, use_container_width=True)

    if home_submitted and not st.session_state.get("trigger_search", False):
        st.session_state.trigger_search = True
        st.rerun()


