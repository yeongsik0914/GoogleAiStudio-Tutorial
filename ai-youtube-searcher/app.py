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
    .yt-logo-group {
        display: flex;
        align-items: center;
        gap: 8px;
        cursor: pointer;
        user-select: none;
    }
    .yt-logo-text {
        font-size: 1.18rem;
        font-weight: 800;
        letter-spacing: -0.5px;
        color: #ffffff;
        display: flex;
        align-items: center;
    }
    .badge-gemini {
        background: linear-gradient(135deg, #ff0000 0%, #ff4b4b 100%);
        color: white;
        padding: 2px 7px;
        border-radius: 10px;
        font-size: 0.68rem;
        font-weight: 700;
        letter-spacing: 0.3px;
        margin-left: 6px;
    }
    .yt-nav-header-right {
        display: flex;
        align-items: center;
        justify-content: flex-end;
        height: 38px;
        gap: 6px;
        position: relative !important;
        z-index: 100 !important;
    }
    .header-chip-status {
        background: #1c1c1f;
        border: 1px solid #2e2e34;
        color: #3ea6ff;
        padding: 4px 10px;
        border-radius: 14px;
        font-size: 0.72rem;
        font-weight: 600;
    }
    
    /* 유튜브 공식 알약 검색창 & 버튼 스타일 (호버 위치값 및 클릭 완벽 보장) */
    div[data-testid="stForm"] {
        border: none !important;
        padding: 0 !important;
        margin: 0 !important;
        background: transparent !important;
        position: relative !important;
        z-index: 100 !important;
        pointer-events: auto !important;
    }
    
    /* 인풋창 스타일 - 둥근 알약형 (20px) 전체 래퍼 및 내부 인풋 완벽 매핑 */
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
        background-color: #121214 !important;
        border: 1px solid #38383e !important;
        border-radius: 20px !important;
        height: 38px !important;
        min-height: 38px !important;
        padding: 0 !important;
        transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
        cursor: text !important;
    }
    .stTextInput > div > div:hover {
        border-color: #555562 !important;
    }
    .stTextInput > div > div:focus-within {
        border-color: #3ea6ff !important;
        box-shadow: 0 0 0 1px #3ea6ff !important;
    }
    .stTextInput input {
        background-color: transparent !important;
        color: #f1f1f1 !important;
        border: none !important;
        border-radius: 20px !important;
        height: 36px !important;
        padding: 0 16px !important;
        font-size: 0.86rem !important;
        box-shadow: none !important;
        transform: none !important;
        outline: none !important;
        cursor: text !important;
        pointer-events: auto !important;
    }
    
    /* 검색 버튼 - 둥근 알약형 레드 버튼 (정확한 submit button 셀렉터 및 클릭 보장) */
    div[data-testid="stFormSubmitButton"] {
        margin: 0 !important;
        padding: 0 !important;
        height: 38px !important;
        display: flex !important;
        align-items: center !important;
        width: 100% !important;
        position: relative !important;
        z-index: 101 !important;
    }
    div[data-testid="stFormSubmitButton"] button,
    div[data-testid="stForm"] button,
    .stButton button[kind="primary"] {
        width: 100% !important;
        height: 38px !important;
        min-height: 38px !important;
        background-color: #cc0000 !important;
        border: 1px solid #cc0000 !important;
        border-radius: 20px !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        font-size: 0.86rem !important;
        padding: 0 16px !important;
        box-shadow: none !important;
        transform: none !important;
        transition: background-color 0.15s ease, border-color 0.15s ease, box-shadow 0.15s ease !important;
        cursor: pointer !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        pointer-events: auto !important;
    }
    div[data-testid="stFormSubmitButton"] button:hover,
    div[data-testid="stForm"] button:hover,
    .stButton button[kind="primary"]:hover {
        background-color: #ff0000 !important;
        border-color: #ff0000 !important;
        color: #ffffff !important;
        box-shadow: 0 2px 10px rgba(255, 0, 0, 0.4) !important;
        transform: none !important;
    }
    div[data-testid="stFormSubmitButton"] button:active,
    div[data-testid="stForm"] button:active,
    .stButton button[kind="primary"]:active {
        background-color: #b30000 !important;
        border-color: #b30000 !important;
        transform: none !important;
    }
    div[data-testid="stFormSubmitButton"] button:focus,
    div[data-testid="stForm"] button:focus {
        box-shadow: 0 0 0 2px rgba(255, 0, 0, 0.5) !important;
        outline: none !important;
    }
    div[data-testid="stFormSubmitButton"] button p,
    div[data-testid="stForm"] button p {
        margin: 0 !important;
        padding: 0 !important;
        font-size: 0.86rem !important;
        font-weight: 700 !important;
        color: #ffffff !important;
        line-height: 1 !important;
    }
</style>
""", unsafe_allow_html=True)


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


# --- [핵심] 최상단 네비바 & 중앙 정렬 알약형 링크 검색창 ---
col_head_left, col_head_center, col_head_right = st.columns([2.2, 5.6, 2.2], gap="medium")

with col_head_left:
    st.markdown("""
    <div class="yt-nav-header-left">
        <div class="yt-logo-group">
            <svg width="28" height="20" viewBox="0 0 32 23" fill="none">
                <path d="M31.24 3.49C30.87 2.12 29.8 1.05 28.43 0.68C25.96 0 16 0 16 0C16 0 6.04 0 3.57 0.68C2.2 1.05 1.13 2.12 0.76 3.49C0 5.96 0 11.1 0 11.1C0 11.1 0 16.24 0.76 18.71C1.13 20.08 2.2 21.15 3.57 21.52C6.04 22.2 16 22.2 16 22.2C16 22.2 25.96 22.2 28.43 21.52C29.8 21.15 30.87 20.08 31.24 18.71C32 16.24 32 11.1 32 11.1C32 11.1 32 5.96 31.24 3.49Z" fill="#FF0000"/>
                <polygon points="12.8,15.8 21.2,11.1 12.8,6.4" fill="#FFFFFF"/>
            </svg>
            <span class="yt-logo-text">AI Studio</span>
            <span class="badge-gemini">3.5 & 3.8</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

with col_head_center:
    with st.form("yt_search_form", clear_on_submit=False, border=False):
        c_search_in, c_search_btn = st.columns([82, 18], gap="small")
        with c_search_in:
            url_input = st.text_input(
                "유튜브 링크 주소",
                value=st.session_state.current_url,
                placeholder="유튜브 영상 링크 입력 (예: https://www.youtube.com/watch?v=...)",
                label_visibility="collapsed",
                key="yt_url_input_box",
            )
        with c_search_btn:
            search_submit = st.form_submit_button("🔍 검색", type="primary", use_container_width=True)

with col_head_right:
    st.write("")


# 다운로드 폴더
download_dir = os.path.join(os.path.dirname(__file__), "downloads")
os.makedirs(download_dir, exist_ok=True)


# --- 검색 및 분석 실행 ---
target_url = (url_input or "").strip() or st.session_state.get("yt_url_input_box", "").strip() or st.session_state.get("current_url", "").strip()

if search_submit or st.session_state.get("trigger_search", False):
    st.session_state.trigger_search = False
    if not target_url:
        st.error("유튜브 영상 링크를 입력해주세요.")
    elif not api_key_input.strip():
        st.error("사이드바에서 Gemini API 키를 입력해주세요.")
    else:
        v_id = extract_video_id(target_url)
        if not v_id:
            st.error("올바른 유튜브 링크 형식이 아닙니다. (예: https://www.youtube.com/watch?v=...)")
        else:
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

                    status.update(label="🎉 영상 분석 및 카테고리 생성 완료!", state="complete", expanded=False)
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

    # 하단 비디오 상세 정보 바 (다운로드 버튼 완전 삭제 및 전체 폭 정렬)
    uploader_initial = v_uploader[0].upper() if v_uploader else "Y"

    st.markdown(f"""
    <div style="background: #181818; border: 1px solid #282828; border-radius: 8px; padding: 4px 14px; height: 34px; display: flex; align-items: center; gap: 10px; overflow: hidden;" title="{v_title}">
        <div style="width: 22px; height: 22px; min-width: 22px; background: #333333; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: #fff; font-size: 0.72rem; font-weight: 700;">
            {uploader_initial}
        </div>
        <span style="font-weight: 700; font-size: 0.88rem; color: #ffffff; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 70%;">
            {v_title}
        </span>
        <span style="color: #555;">•</span>
        <span style="color: #aaaaaa; font-size: 0.8rem; white-space: nowrap;">📺 {v_uploader}</span>
        <span style="color: #555;">•</span>
        <span style="color: #aaaaaa; font-size: 0.8rem; white-space: nowrap;">조회수 {v_views}회</span>
        <span style="color: #555;">•</span>
        <span style="color: #aaaaaa; font-size: 0.8rem; white-space: nowrap;">⏱️ {v_duration_str}</span>
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

