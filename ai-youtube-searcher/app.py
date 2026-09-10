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
    page_icon="▶️",
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
    
    /* 전체 배경을 유튜브 공식 다크 테마(#0f0f0f)로 지정 및 안전한 뷰포트 스크롤 */
    html, body, [data-testid="stAppViewContainer"], .stApp {
        background-color: #0f0f0f !important;
        color: #f1f1f1 !important;
        overflow-x: hidden !important;
        overflow-y: auto !important;
    }
    
    /* 앱 전체 부드럽고 얇은 스크롤바 */
    [data-testid="stAppViewContainer"]::-webkit-scrollbar {
        width: 6px;
    }
    [data-testid="stAppViewContainer"]::-webkit-scrollbar-thumb {
        background: #24242c;
        border-radius: 3px;
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
    
    /* 유튜브 공식 일체형 검색창 & 마이크 버튼 (Image 2 완벽 구현) */
    div[data-testid="stForm"] {
        border: none !important;
        padding: 0 !important;
        margin: 0 !important;
        background: transparent !important;
        position: relative !important;
        z-index: 100 !important;
    }
    div[data-testid="stForm"] [data-testid="stHorizontalBlock"] {
        gap: 0px !important;
        align-items: center !important;
    }
    
    /* 검색 인풋창 (좌측 둥근 알약 + 우측 직각 연결) */
    .stTextInput {
        margin: 0 !important;
        padding: 0 !important;
        position: relative !important;
        z-index: 101 !important;
    }
    .stTextInput > div {
        margin: 0 !important;
        padding: 0 !important;
    }
    .stTextInput > div > div {
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
    .stTextInput > div > div:hover {
        border-color: #444444 !important;
    }
    .stTextInput > div > div:focus-within {
        border-color: #1c62b9 !important;
        box-shadow: inset 0 1px 2px rgba(0, 0, 0, 0.5) !important;
    }
    .stTextInput input {
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
    
    /* 검색 제출 버튼 (좌측 직각 + 우측 둥근 알약 다크 그레이) */
    div[data-testid="stFormSubmitButton"] {
        margin: 0 !important;
        padding: 0 !important;
        height: 40px !important;
        display: flex !important;
        align-items: center !important;
        width: 100% !important;
        position: relative !important;
        z-index: 101 !important;
    }
    div[data-testid="stFormSubmitButton"] button,
    div[data-testid="stForm"] button {
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
    div[data-testid="stFormSubmitButton"] button:hover,
    div[data-testid="stForm"] button:hover {
        background-color: #272727 !important;
        border-color: #383838 !important;
        color: #ffffff !important;
    }
    div[data-testid="stFormSubmitButton"] button:active,
    div[data-testid="stForm"] button:active {
        background-color: #333333 !important;
    }
    div[data-testid="stFormSubmitButton"] button p,
    div[data-testid="stForm"] button p {
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
    
    /* 반응형 사이드 드로어 (분석 보관함) */
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
    }
    .yt-drawer-backdrop.open {
        opacity: 1;
        pointer-events: auto;
    }
    .yt-drawer-panel {
        position: fixed;
        top: 0;
        left: 0;
        width: 370px;
        max-width: 88vw;
        height: 100vh;
        background: #0f0f0f;
        border-right: 1px solid #282828;
        box-shadow: 6px 0 28px rgba(0, 0, 0, 0.85);
        z-index: 99999 !important;
        transform: translateX(-100%);
        transition: transform 0.28s cubic-bezier(0.1, 0.9, 0.2, 1);
        display: flex;
        flex-direction: column;
        box-sizing: border-box;
    }
    .yt-drawer-panel.open {
        transform: translateX(0);
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
        padding: 8px 10px;
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
    .d-thumb-box {
        position: relative;
        width: 86px;
        height: 52px;
        min-width: 86px;
        border-radius: 6px;
        overflow: hidden;
        background: #000;
    }
    .d-thumb-img {
        width: 100%;
        height: 100%;
        object-fit: cover;
    }
    .d-dur-tag {
        position: absolute;
        bottom: 3px;
        right: 4px;
        background: rgba(0, 0, 0, 0.85);
        color: #fff;
        font-size: 0.68rem;
        font-weight: 700;
        padding: 1px 4px;
        border-radius: 4px;
    }
    .d-info-box {
        flex: 1;
        min-width: 0;
        display: flex;
        flex-direction: column;
        gap: 3px;
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
</style>
""", unsafe_allow_html=True)


# --- [홈 복귀 및 캐시 로드/삭제 핸들러] ---
q_params = st.query_params

if q_params.get("home") == "true" or q_params.get("reset") == "true":
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.query_params.clear()
    st.rerun()

load_cache_id = q_params.get("load_cache")
if load_cache_id:
    c_data = load_from_cache(load_cache_id)
    if c_data:
        st.session_state.video_id = c_data["video_id"]
        st.session_state.video_info = c_data["video_info"]
        st.session_state.audio_path = c_data["audio_path"]
        st.session_state.transcript_data = c_data["transcript_data"]
        st.session_state.chapters_data = c_data.get("chapters_data", [])
        st.session_state.current_url = c_data.get("url", f"https://www.youtube.com/watch?v={load_cache_id}")
        st.session_state.chat_messages = []
        st.session_state.from_cache = True
        st.query_params.clear()
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


# --- 사이드바 설정 ---
with st.sidebar:
    st.header("⚙️ Gemini API 설정")
    env_api_key = os.environ.get("GEMINI_API_KEY", "")
    api_key_input = st.text_input(
        "Gemini API Key",
        value=env_api_key,
        type="password",
        help=".env 파일 또는 직접 입력 가능",
    )
    if not api_key_input:
        st.warning("⚠️ Gemini API 키를 입력해주세요.")
    else:
        st.success("✅ Gemini API 연결 완료")


# --- [핵심] 유튜브 공식 상단 네비바 (Image 2 완벽 구현) ---
col_head_left, col_head_center, col_head_right = st.columns([2.0, 5.8, 2.2], gap="small")

with col_head_left:
    st.markdown("""
    <div class="yt-nav-header-left">
        <button class="yt-menu-icon" onclick="openDrawer()" title="카테고리 메뉴 열기 (분석 보관함)" style="background:none; border:none; padding:0; cursor:pointer;">
            <svg viewBox="0 0 24 24" width="20" height="20" fill="#ffffff">
                <path d="M3 18h18v-2H3v2zm0-5h18v-2H3v2zm0-7v2h18V6H3z"/>
            </svg>
        </button>
        <a href="?home=true" target="_self" class="yt-logo-link" title="YouTube 홈으로 돌아가기">
            <svg width="28" height="20" viewBox="0 0 32 23" fill="none">
                <path d="M31.24 3.49C30.87 2.12 29.8 1.05 28.43 0.68C25.96 0 16 0 16 0C16 0 6.04 0 3.57 0.68C2.2 1.05 1.13 2.12 0.76 3.49C0 5.96 0 11.1 0 11.1C0 11.1 0 16.24 0.76 18.71C1.13 20.08 2.2 21.15 3.57 21.52C6.04 22.2 16 22.2 16 22.2C16 22.2 25.96 22.2 28.43 21.52C29.8 21.15 30.87 20.08 31.24 18.71C32 16.24 32 11.1 32 11.1C32 11.1 32 5.96 31.24 3.49Z" fill="#FF0000"/>
                <polygon points="12.8,15.8 21.2,11.1 12.8,6.4" fill="#FFFFFF"/>
            </svg>
            <span class="yt-wordmark">YouTube</span>
            <span class="yt-country-code">KR</span>
        </a>
    </div>
    """, unsafe_allow_html=True)

with col_head_center:
    c_s_form, c_s_mic = st.columns([91, 9], gap="small")
    with c_s_form:
        with st.form("yt_search_form", clear_on_submit=False, border=False):
            c_search_in, c_search_btn = st.columns([88, 12], gap="small")
            with c_search_in:
                url_input = st.text_input(
                    "유튜브 링크 주소",
                    value=st.session_state.current_url,
                    placeholder="검색할 유튜브 영상 링크 입력 (예: https://www.youtube.com/watch?v=...)",
                    label_visibility="collapsed",
                    key="yt_url_input_box",
                )
            with c_search_btn:
                search_submit = st.form_submit_button("🔍", type="primary", use_container_width=True)
    with c_s_mic:
        st.markdown("""
        <div class="yt-mic-btn" title="음성으로 검색">
            <svg viewBox="0 0 24 24" width="19" height="19" fill="#f1f1f1">
                <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3zm-1-9c0-.55.45-1 1-1s1 .45 1 1v6c0 .55-.45 1-1 1s-1-.45-1-1V5zm6 6c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"/>
            </svg>
        </div>
        """, unsafe_allow_html=True)

with col_head_right:
    st.markdown("""
    <div class="yt-nav-header-right">
        <div class="yt-create-btn" title="만들기">
            <svg viewBox="0 0 24 24" width="18" height="18" fill="#ffffff">
                <path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/>
            </svg>
            <span>만들기</span>
        </div>
        <div class="yt-icon-round-btn" title="알림">
            <svg viewBox="0 0 24 24" width="20" height="20" fill="#ffffff">
                <path d="M10 20h4c0 1.1-.9 2-2 2s-2-.9-2-2zm10-2v-1l-2-2v-6c0-3.07-1.63-5.64-4.5-6.32V2c0-.83-.67-1.5-1.5-1.5s-1.5.67-1.5 1.5v.68C7.64 3.36 6 5.92 6 9v6l-2 2v1h16zm-3-2H7v-7c0-2.48 1.51-4.5 4-4.5s4 2.02 4 4.5v7z"/>
            </svg>
        </div>
        <div class="yt-avatar-circle" title="계정">10</div>
    </div>
    """, unsafe_allow_html=True)

# --- [반응형 사이드 드로어 마크업 & JS 주입] ---
cached_videos_list = get_all_cached_videos()
cached_cards_html = ""

if cached_videos_list:
    for cv in cached_videos_list:
        v_t_esc = cv['title'].replace('"', '&quot;').replace("'", "&#39;")
        cached_cards_html += f"""
        <div class="d-video-card">
            <a href="?load_cache={cv['video_id']}" target="_self" class="d-card-link" title="{v_t_esc}">
                <div class="d-thumb-box">
                    <img src="{cv['thumbnail']}" alt="thumb" class="d-thumb-img" onerror="this.src='https://img.youtube.com/vi/{cv['video_id']}/hqdefault.jpg'"/>
                    <span class="d-dur-tag">{cv['duration_str']}</span>
                </div>
                <div class="d-info-box">
                    <div class="d-title">{v_t_esc}</div>
                    <div class="d-uploader">📺 {cv['uploader']}</div>
                    <div class="d-footer-row">
                        <span class="d-token-tag">⚡ 0토큰 로드</span>
                        <span class="d-date-tag">{cv['cached_at']}</span>
                    </div>
                </div>
            </a>
            <a href="?delete_cache={cv['video_id']}" target="_self" class="d-del-btn" title="보관함에서 삭제" onclick="return confirm('이 영상의 분석 캐시를 삭제하시겠습니까?');">
                <svg viewBox="0 0 24 24" width="16" height="16" fill="#888">
                    <path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/>
                </svg>
            </a>
        </div>
        """
else:
    cached_cards_html = """
    <div class="d-empty-box">
        <div style="font-size: 2.2rem; margin-bottom: 8px;">📂</div>
        <div style="font-weight: 700; color: #ffffff; margin-bottom: 4px; font-size: 0.95rem;">아직 보관된 영상이 없습니다</div>
        <div style="font-size: 0.8rem; color: #888888; line-height: 1.4;">상단에서 유튜브 링크를 분석하면<br>여기에 자동으로 보관되어 언제든 0토큰으로 다시 볼 수 있습니다.</div>
    </div>
    """

clear_btn_html = f'<div class="d-panel-footer"><a href="?clear_all_cache=true" target="_self" class="d-clear-all-btn" onclick="return confirm(\'정말 모든 분석 캐시를 삭제하시겠습니까?\');">🗑️ 전체 캐시 비우기</a></div>' if cached_videos_list else ''

drawer_markup = f"""
<div id="yt-drawer-backdrop" class="yt-drawer-backdrop" onclick="closeDrawer()"></div>
<div id="yt-drawer-panel" class="yt-drawer-panel">
    <div class="d-panel-header">
        <button class="yt-menu-icon" onclick="closeDrawer()" title="메뉴 닫기" style="background:none; border:none; padding:0; cursor:pointer;">
            <svg viewBox="0 0 24 24" width="20" height="20" fill="#ffffff">
                <path d="M3 18h18v-2H3v2zm0-5h18v-2H3v2zm0-7v2h18V6H3z"/>
            </svg>
        </button>
        <a href="?home=true" target="_self" class="yt-logo-link" style="margin-left: 12px;">
            <svg width="28" height="20" viewBox="0 0 32 23" fill="none">
                <path d="M31.24 3.49C30.87 2.12 29.8 1.05 28.43 0.68C25.96 0 16 0 16 0C16 0 6.04 0 3.57 0.68C2.2 1.05 1.13 2.12 0.76 3.49C0 5.96 0 11.1 0 11.1C0 11.1 0 16.24 0.76 18.71C1.13 20.08 2.2 21.15 3.57 21.52C6.04 22.2 16 22.2 16 22.2C16 22.2 25.96 22.2 28.43 21.52C29.8 21.15 30.87 20.08 31.24 18.71C32 16.24 32 11.1 32 11.1C32 11.1 32 5.96 31.24 3.49Z" fill="#FF0000"/>
                <polygon points="12.8,15.8 21.2,11.1 12.8,6.4" fill="#FFFFFF"/>
            </svg>
            <span class="yt-wordmark">YouTube</span>
            <span class="yt-country-code">KR</span>
        </a>
    </div>
    
    <div class="d-panel-body">
        <a href="?home=true" target="_self" class="d-menu-btn" title="새로운 영상 분석 홈 화면">
            <span style="font-size: 1.15rem;">🏠</span>
            <span>홈 (새 영상 검색)</span>
        </a>
        
        <div class="d-section-divider"></div>
        
        <div class="d-section-header">
            <div style="display: flex; align-items: center; gap: 6px;">
                <span style="font-size: 1.05rem;">📁</span>
                <span style="font-weight: 700; font-size: 0.95rem; color: #ffffff;">분석 보관함</span>
            </div>
            <span class="d-count-pill">{len(cached_videos_list)}개 보관</span>
        </div>
        
        <div class="d-scroll-area">
            {cached_cards_html}
        </div>
        
        {clear_btn_html}
    </div>
</div>

<script>
function openDrawer() {{
    var bd = document.getElementById('yt-drawer-backdrop');
    var pn = document.getElementById('yt-drawer-panel');
    if (bd && pn) {{
        bd.classList.add('open');
        pn.classList.add('open');
    }}
}}
function closeDrawer() {{
    var bd = document.getElementById('yt-drawer-backdrop');
    var pn = document.getElementById('yt-drawer-panel');
    if (bd && pn) {{
        bd.classList.remove('open');
        pn.classList.remove('open');
    }}
}}
document.addEventListener('keydown', function(e) {{
    if (e.key === 'Escape') closeDrawer();
}});
</script>
"""
st.markdown(drawer_markup, unsafe_allow_html=True)



# 다운로드 폴더
download_dir = os.path.join(os.path.dirname(__file__), "downloads")
os.makedirs(download_dir, exist_ok=True)


# --- 검색 및 분석 실행 ---
target_url = (url_input or "").strip() or st.session_state.get("yt_url_input_box", "").strip() or st.session_state.get("current_url", "").strip()

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
                st.session_state.audio_path = cached_data["audio_path"]
                st.session_state.transcript_data = cached_data["transcript_data"]
                st.session_state.chapters_data = cached_data.get("chapters_data", [])
                st.session_state.current_url = cached_data.get("url", target_url)
                st.session_state.chat_messages = []
                st.session_state.from_cache = True
                st.toast("⚡ 이전에 분석된 영상입니다. Gemini 토큰 소모 없이 즉시 불러왔습니다!", icon="🚀")
                st.rerun()
            elif not api_key_input.strip():
                st.error("신규 영상 분석을 위해 사이드바에서 Gemini API 키를 입력해주세요.")
            else:
                # [핵심 2] 신규 영상인 경우: 오디오 다운로드 및 Gemini 3.5 STT & 3.8 챕터 생성
                st.session_state.current_url = target_url
                status_holder = st.empty()
                with status_holder.status("🎬 유튜브 영상 분석 및 AI 데이터 생성 중...", expanded=True) as status:
                    try:
                        status.write("📥 1/3: 영상 메타데이터 조회 및 오디오 추출...")
                        audio_path, video_info = download_audio(target_url, output_dir=download_dir)
                        st.session_state.video_id = v_id
                        st.session_state.video_info = video_info
                        st.session_state.audio_path = audio_path

                        status.write("🎙️ 2/3: `gemini-3.5-transcribe` 모델로 실시간 타임스탬프 전사 추출...")
                        transcript_res = transcribe_with_timestamps(audio_path, api_key=api_key_input.strip())
                        st.session_state.transcript_data = transcript_res

                        status.write("🏷️ 3/3: `gemini-3.8-flash` 모델로 주제별 챕터 및 핵심 요약 추출...")
                        chapters = extract_video_chapters(
                            segments=transcript_res.get("segments", []),
                            full_text=transcript_res.get("full_text", ""),
                            api_key=api_key_input.strip(),
                        )
                        st.session_state.chapters_data = chapters
                        st.session_state.chat_messages = []
                        st.session_state.from_cache = False

                        # [핵심 3] 다음 재호출 시 0토큰으로 즉시 로드할 수 있도록 로컬 캐시에 자동 영구 저장
                        save_to_cache(
                            video_id=v_id,
                            video_info=video_info,
                            audio_path=audio_path,
                            transcript_data=transcript_res,
                            chapters_data=chapters,
                            url=target_url,
                        )

                        status.update(label="🎉 영상 분석 및 카테고리 보관 완료!", state="complete", expanded=False)
                        status_holder.empty()
                        st.rerun()

                    except Exception as e:
                        status.update(label="❌ 오류 발생", state="error", expanded=True)
                        st.error(f"오류 상세: {e}")


# --- 메인 구글 유튜브 스타일 일체형 통합 웹 앱 ---
if st.session_state.video_id and st.session_state.video_info and st.session_state.transcript_data:
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

    # 전체 화면을 하나로 통합한 일체형 컴포넌트 HTML (좌측 플레이어/타임라인 + 우측 4대 탭)
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
            
            /* 2열 메인 컨테이너 (615px 높이로 100vh 일체화 및 상단 잘림 방지) */
            .app-container {{
                display: grid;
                grid-template-columns: 58fr 42fr;
                gap: 12px;
                width: 100%;
                height: 615px;
                box-sizing: border-box;
            }}
            
            /* ==================================================== */
            /* 📺 좌측: 비디오 플레이어(좌우 공백 없이 100% 꽉 채움) + 타임라인 + 자막 */
            /* ==================================================== */
            .left-column {{
                display: flex;
                flex-direction: column;
                gap: 6px;
                height: 100%;
                min-height: 0;
            }}
            
            /* [핵심] 좌우 공백 없이 칼럼 전체 너비를 100% 꽉 채우는 16:9 플레이어 */
            .player-wrapper {{
                position: relative;
                width: 100%;
                aspect-ratio: 16 / 9;
                background: #000;
                border-radius: 10px;
                overflow: hidden;
                box-shadow: 0 4px 20px rgba(0,0,0,0.8);
                flex-shrink: 0;
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
            }}
            .yt-time-badge {{
                font-size: 0.76rem;
                color: #aaaaaa;
                font-variant-numeric: tabular-nums;
                white-space: nowrap;
            }}
            
            /* 실시간 라이브 자막 바 */
            .yt-live-caption-box {{
                background: linear-gradient(180deg, #1f1f22 0%, #161618 100%);
                border: 1px solid #2d2d32;
                border-left: 5px solid #ff0000;
                border-radius: 9px;
                padding: 7px 12px;
                box-shadow: 0 4px 14px rgba(0, 0, 0, 0.5);
                display: flex;
                flex-direction: column;
                justify-content: center;
                min-height: 64px;
                max-height: 64px;
                flex-shrink: 0;
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
            
            /* ========================================= */
            /* 📑💬 우측: 카테고리 4대 탭 통합 사이드 패널 */
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
            
            /* 유튜브 알약 필터 탭 바 (4개 탭 수용) */
            .tab-nav-bar {{
                display: flex;
                gap: 5px;
                margin-bottom: 7px;
                border-bottom: 1px solid #282828;
                padding-bottom: 7px;
            }}
            .tab-chip {{
                background: #272727;
                color: #f1f1f1;
                border: 1px solid #383838;
                border-radius: 16px;
                padding: 4px 9px;
                font-size: 0.74rem;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.15s ease;
                display: flex;
                align-items: center;
                gap: 4px;
                white-space: nowrap;
            }}
            .tab-chip:hover {{
                background: #383838;
            }}
            .tab-chip.active {{
                background: #f1f1f1 !important;
                color: #0f0f0f !important;
                border-color: #ffffff !important;
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
            
            /* ---------------------------------------------------- */
            /* 📑 카테고리 1: 정확히 5칸 크기 맞춤 & 3번째 칸 실시간 음성 싱크 */
            /* ---------------------------------------------------- */
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
            /* 💬 카테고리 2: Gemini AI 챗봇           */
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
            /* 🏷️ 카테고리 3: 주제별 챕터 요약        */
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
            /* 📥 카테고리 4: 대본 및 오디오 다운로드 허브 */
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
        </style>
    </head>
    <body>
        <div class="app-container">
            <!-- ============================================== -->
            <!-- 📺 [좌측]: 비디오 + 타임라인 + 컨트롤 + 라이브자막 -->
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
                        <button class="ctrl-icon-btn" onclick="toggleMute()" id="mute-btn" title="음소거 토글">
                            <svg id="speaker-icon" width="16" height="16" viewBox="0 0 24 24" fill="#ff0000">
                                <path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"/>
                            </svg>
                        </button>
                        <input type="range" class="yt-vol-slider" min="0" max="100" value="100" oninput="changeVol(this.value)">
                        <span class="yt-vol-badge" id="vol-badge">100%</span>
                    </div>
                    <div class="yt-ctrl-center">
                        <button class="skip-btn" onclick="skipRelative(-5)" title="5초 뒤로">⏪ -5s</button>
                        <button class="skip-btn" onclick="skipRelative(5)" title="5초 앞으로">+5s ⏩</button>
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
                            ⏱️ <span id="time-current">00:00</span> / <span id="time-total">00:00</span>
                        </div>
                    </div>
                </div>

                <!-- 실시간 라이브 자막 -->
                <div class="yt-live-caption-box">
                    <div class="yt-live-head">
                        <div class="yt-live-tag">
                            <span class="yt-live-dot"></span>
                            <span>실시간 대사</span>
                        </div>
                        <div style="display: flex; align-items: center; gap: 8px;">
                            <button class="copy-caption-btn" onclick="copyLiveCaption()" id="copy-cap-btn" title="현재 대사 복사">📋 복사</button>
                            <div class="yt-live-time" id="live-time-display">00:00</div>
                        </div>
                    </div>
                    <div class="yt-live-text" id="live-text-display">영상을 재생하면 실시간 음성에 맞추어 대사가 출력됩니다.</div>
                </div>
            </div>

            <!-- ============================================== -->
            <!-- 📑💬 [우측]: 카테고리 4대 탭 통합 사이드 패널   -->
            <!-- ============================================== -->
            <div class="right-column">
                <div class="tab-nav-bar">
                    <button class="tab-chip active" id="tab-btn-transcript" onclick="switchTab('transcript')">📑 대본</button>
                    <button class="tab-chip" id="tab-btn-chat" onclick="switchTab('chat')">💬 Gemini 챗봇</button>
                    <button class="tab-chip" id="tab-btn-chapters" onclick="switchTab('chapters')">🏷️ 챕터</button>
                    <button class="tab-chip" id="tab-btn-download" onclick="switchTab('download')">📥 다운로드</button>
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
                        <span class="preset-chip" onclick="askPreset('이 영상의 가장 중요한 핵심 내용을 3줄로 요약해줘.')">📌 3줄 핵심 요약</span>
                        <span class="preset-chip" onclick="askPreset('영상의 최종 결론과 화자의 핵심 메시지는 뭐야?')">🎯 최종 결론</span>
                        <span class="preset-chip" onclick="askPreset('영상에서 다루는 주요 이슈와 원인은 무엇인가요?')">🔍 주요 원인 분석</span>
                        <span class="preset-chip" onclick="askPreset('영상 속에 등장하는 핵심 개념과 키워드를 정리해줘.')">💡 핵심 키워드 정리</span>
                        <span class="preset-chip" onclick="askPreset('영상 내용 중 시청자가 꼭 알아야 할 주요 사실(Fact)을 Q&A로 정리해줘.')">❓ Q&A 팩트체크</span>
                    </div>

                    <div class="chat-messages-container" id="chat-box">
                        <div class="chat-bubble-a">
                            🤖 <b>Gemini 3.8 Flash 어시스턴트:</b><br>
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
                                <div class="dl-card-icon">📄</div>
                                <div>
                                    <div class="dl-card-title">전체 텍스트 대본 (.txt)</div>
                                    <div class="dl-card-desc">Gemini AI가 고정밀 전사한 텍스트 대본 파일</div>
                                </div>
                            </div>
                            <div class="dl-meta-chips">
                                <span class="dl-chip">총 {segments_count_val}개 발화</span>
                                <span class="dl-chip">UTF-8 포맷</span>
                            </div>
                            <div class="dl-card-actions">
                                <button class="dl-act-btn primary" onclick="downloadTranscriptTxt(false)">📥 텍스트 다운로드</button>
                                <button class="dl-act-btn secondary" onclick="downloadTranscriptTxt(true)">⏱️ 타임스탬프 포함</button>
                                <button class="dl-act-btn copy" id="copy-all-btn" onclick="copyAllTranscript()">📋 전체 복사</button>
                            </div>
                        </div>

                        <!-- 2. 고음질 오디오 카드 -->
                        <div class="dl-card">
                            <div class="dl-card-header">
                                <div class="dl-card-icon">🎵</div>
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
                                <button class="dl-act-btn primary audio" onclick="downloadAudioFile()">🎵 고음질 오디오 다운로드</button>
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
                    btn.innerText = "✅ 복사됨";
                    setTimeout(function() {{ btn.innerText = "📋 복사"; }}, 1500);
                }}).catch(function() {{
                    btn.innerText = "❌ 실패";
                    setTimeout(function() {{ btn.innerText = "📋 복사"; }}, 1500);
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
                        btn.innerText = "✅ 전체 복사 완료";
                        setTimeout(function() {{ btn.innerText = "📋 전체 복사"; }}, 1500);
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

                // 3. 자막 및 3번째 칸 현재 음성 대본 동기화
                if (targetIdx !== -1) {{
                    var curSeg = segments[targetIdx];
                    document.getElementById('live-time-display').innerText = curSeg.time_str;
                    document.getElementById('live-text-display').innerText = curSeg.text;

                    if (targetIdx !== currentActiveIdx || forceSync) {{
                        currentActiveIdx = targetIdx;

                        var prev = document.querySelector('.t-slot-card.active');
                        if (prev) prev.classList.remove('active');

                        var activeEl = document.getElementById('t-card-' + targetIdx);
                        if (activeEl) {{
                            activeEl.classList.add('active');

                            if (!isUserScrolling || forceSync) {{
                                // [핵심] 첫 대본이 3번째 칸에서 시작하여 시간 경과에 따라 위로 올라가도록 스크롤 동기화
                                // 상단에 2칸의 빈 공간이 있으므로, targetIdx번째 발화 카드가 정확히 3번째 칸에 오기 위한 스크롤 위치:
                                // targetScrollTop = targetIdx * (slotH + gap)
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
                            '<span class="t-time-btn">⏱️ ' + s.time_str + '</span>' +
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
                var val = q.trim().toLowerCase();
                if (!val) {{
                    renderTranscriptList(indexedSegments);
                    if (currentActiveIdx !== -1) {{
                        syncPlaybackAndTranscript(true);
                    }}
                    return;
                }}
                var filtered = indexedSegments.filter(function(s) {{
                    return s.text.toLowerCase().indexOf(val) !== -1;
                }});
                renderTranscriptList(filtered);
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
                uMsg.innerHTML = '🙋 <b>질문:</b> ' + question;
                chatBox.appendChild(uMsg);
                inputEl.value = "";

                var loadMsg = document.createElement('div');
                loadMsg.className = 'chat-bubble-a';
                loadMsg.id = 'chat-loading-item';
                loadMsg.innerHTML = '🤖 <b>Gemini 3.8 Flash:</b> 답변을 생성하고 있습니다... ⏳';
                chatBox.appendChild(loadMsg);
                chatBox.scrollTop = chatBox.scrollHeight;

                if (!apiKey) {{
                    loadMsg.innerHTML = '⚠️ 좌측 사이드바에서 Gemini API 키를 먼저 입력해주세요.';
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

                    var resp = await fetch("https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent?key=" + apiKey, {{
                        method: "POST",
                        headers: {{ "Content-Type": "application/json" }},
                        body: JSON.stringify({{
                            contents: [{{ parts: [{{ text: promptText }}] }}]
                        }})
                    }});

                    var data = await resp.json();
                    var rawText = data.candidates[0].content.parts[0].text;
                    
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
                            '⏱️ 구간 바로가기: [' + relTs + '] (' + Math.floor(relSec) + '초)</button></div>';
                    }}

                    aMsg.innerHTML = '<div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 4px;">' +
                        '<span>🤖 <b>Gemini 3.8 Flash:</b></span>' +
                        '<button onclick="copyChatText(this)" style="background: transparent; border: none; color: #888; font-size: 0.7rem; cursor: pointer;">📋 복사</button>' +
                        '</div>' +
                        '<div class="chat-text-content">' + answerText.split(nl).join('<br>') + '</div>' + tsButton;
                    chatBox.appendChild(aMsg);
                    chatBox.scrollTop = chatBox.scrollHeight;

                }} catch(err) {{
                    loadMsg.remove();
                    var errMsg = document.createElement('div');
                    errMsg.className = 'chat-bubble-a';
                    errMsg.style.borderColor = '#ff4b4b';
                    errMsg.innerHTML = '⚠️ 답변 생성 중 오류가 발생했습니다: ' + err.message;
                    chatBox.appendChild(errMsg);
                    chatBox.scrollTop = chatBox.scrollHeight;
                }}
            }}

            function copyChatText(btn) {{
                var parent = btn.closest('.chat-bubble-a');
                var contentEl = parent.querySelector('.chat-text-content');
                if (contentEl) {{
                    navigator.clipboard.writeText(contentEl.innerText).then(function() {{
                        btn.innerText = "✅ 완료";
                        setTimeout(function() {{ btn.innerText = "📋 복사"; }}, 1500);
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
        </script>
    </body>
    </html>
    """

    # 컴포넌트 높이 620px로 지정하여 상단 UI 잘림 없이 한 화면에 완전 렌더링
    components.html(integrated_html, height=620)

    # 하단 비디오 상세 정보 바 (토큰 0 캐시 로드 여부 표시)
    uploader_initial = v_uploader[0].upper() if v_uploader else "Y"
    is_from_cache = st.session_state.get("from_cache", False)
    cache_badge_html = """
    <span style="margin-left: auto; color: #10b981; font-size: 0.76rem; font-weight: 700; background: #0c291e; border: 1px solid #165b40; padding: 2px 10px; border-radius: 12px; white-space: nowrap;">
        ⚡ 로컬 캐시 (토큰 0 소모)
    </span>
    """ if is_from_cache else """
    <span style="margin-left: auto; color: #3ea6ff; font-size: 0.76rem; font-weight: 700; background: #0f2338; border: 1px solid #1d466e; padding: 2px 10px; border-radius: 12px; white-space: nowrap;">
        ✨ Gemini 3.5 신규 분석
    </span>
    """

    st.markdown(f"""
    <div style="background: #181818; border: 1px solid #282828; border-radius: 8px; padding: 4px 14px; height: 34px; display: flex; align-items: center; gap: 10px; overflow: hidden;" title="{v_title}">
        <div style="width: 22px; height: 22px; min-width: 22px; background: #333333; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: #fff; font-size: 0.72rem; font-weight: 700;">
            {uploader_initial}
        </div>
        <span style="font-weight: 700; font-size: 0.88rem; color: #ffffff; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 58%;">
            {v_title}
        </span>
        <span style="color: #555;">•</span>
        <span style="color: #aaaaaa; font-size: 0.8rem; white-space: nowrap;">📺 {v_uploader}</span>
        <span style="color: #555;">•</span>
        <span style="color: #aaaaaa; font-size: 0.8rem; white-space: nowrap;">조회수 {v_views}회</span>
        <span style="color: #555;">•</span>
        <span style="color: #aaaaaa; font-size: 0.8rem; white-space: nowrap;">⏱️ {v_duration_str}</span>
        {cache_badge_html}
    </div>
    """, unsafe_allow_html=True)


else:
    # 초기 대기 화면 (중앙 정렬 배너 & 원클릭 샘플 추천 칩)
    st.markdown("""
    <div style="background: #181818; border-radius: 16px; padding: 2.8rem 2rem; text-align: center; border: 1px dashed #333333; margin-top: 1.2rem;">
        <div style="margin-bottom: 0.8rem;">
            <svg width="60" height="42" viewBox="0 0 32 23" fill="none">
                <path d="M31.24 3.49C30.87 2.12 29.8 1.05 28.43 0.68C25.96 0 16 0 16 0C16 0 6.04 0 3.57 0.68C2.2 1.05 1.13 2.12 0.76 3.49C0 5.96 0 11.1 0 11.1C0 11.1 0 16.24 0.76 18.71C1.13 20.08 2.2 21.15 3.57 21.52C6.04 22.2 16 22.2 16 22.2C16 22.2 25.96 22.2 28.43 21.52C29.8 21.15 30.87 20.08 31.24 18.71C32 16.24 32 11.1 32 11.1C32 11.1 32 5.96 31.24 3.49Z" fill="#FF0000"/>
                <polygon points="12.8,15.8 21.2,11.1 12.8,6.4" fill="#FFFFFF"/>
            </svg>
        </div>
        <h2 style="color: #ffffff; margin-bottom: 0.5rem; font-weight: 800; font-size: 1.5rem;">Google YouTube AI Searcher</h2>
        <p style="color: #aaaaaa; max-width: 640px; margin: 0 auto 1.5rem auto; font-size: 0.92rem; line-height: 1.6;">
            상단 중앙 검색창에 분석할 유튜브 영상 주소를 입력하고 <b>[🔍 검색]</b>을 누르세요.<br>
            <b>실시간 음성-대본 0ms 싱크 전체 대본 뷰</b>, <b>유튜브 공식 호버 타임라인 & 썸네일 미리보기</b>, <b>Gemini 3.8 AI 질의응답</b>, <b>원클릭 파일 다운로드 허브</b>를 지원합니다.
        </p>
        <div style="display: flex; justify-content: center; gap: 10px; flex-wrap: wrap;">
            <span style="background: #272727; color: #ff4b4b; padding: 6px 14px; border-radius: 18px; font-size: 0.82rem; font-weight: 600;">🎞️ 유튜브 호버 타임라인 & 썸네일</span>
            <span style="background: #272727; color: #3ea6ff; padding: 6px 14px; border-radius: 18px; font-size: 0.82rem; font-weight: 600;">⚡ 실시간 음성-대본 0ms 싱크</span>
            <span style="background: #272727; color: #10b981; padding: 6px 14px; border-radius: 18px; font-size: 0.82rem; font-weight: 600;">📑 실시간 음성 싱크 전체 대본</span>
            <span style="background: #272727; color: #f59e0b; padding: 6px 14px; border-radius: 18px; font-size: 0.82rem; font-weight: 600;">📥 대본 & 오디오 다운로드 허브</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 원클릭 샘플 추천 테스트 버튼
    c_s1, c_s2, c_s3 = st.columns([1.8, 2.4, 1.8])
    with c_s2:
        if st.button("🚀 샘플 영상 원클릭 즉시 분석 (횟집 수족관 영상)", use_container_width=True):
            st.session_state.current_url = "https://www.youtube.com/watch?v=IbhBAZNAHvk"
            st.session_state.trigger_search = True
            st.rerun()

