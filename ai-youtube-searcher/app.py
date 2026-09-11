import os
import sys

# 실행 위치(CWD)에 구애받지 않고 로컬 모듈(ui_loader, downloader 등)을 항상 정상 탐색하도록 sys.path 등록
APP_DIR = os.path.dirname(os.path.abspath(__file__))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

import json
import base64
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

# 로컬 엔진 및 UI 모듈 임포트
from ui_loader import (
    load_css,
    load_js,
    render_drawer_html,
    render_player_component,
    render_index_html,
    render_navbar_html,
)
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

# 흰고양이 앱 아이콘 로드 및 Base64 인코딩
CAT_ICON_PATH = os.path.join(os.path.dirname(__file__), "assets", "white_cat_icon_opt.png")
CAT_ICON_B64 = ""
if os.path.exists(CAT_ICON_PATH):
    with open(CAT_ICON_PATH, "rb") as _f:
        CAT_ICON_B64 = base64.b64encode(_f.read()).decode("utf-8")

# --- 페이지 설정 (와이드 모드, 사이드바 기본 축소) ---
st.set_page_config(
    page_title="AIYS - AI 유튜브 검색기",
    page_icon=CAT_ICON_PATH if os.path.exists(CAT_ICON_PATH) else None,
    layout="wide",
    initial_sidebar_state="collapsed",
)

# --- 구글 유튜브 공식 다크 테마 UI CSS (static/css/global_theme.css 분리 로드) ---
st.markdown(f"<style>{load_css('global_theme.css')}</style>", unsafe_allow_html=True)


# --- [홈 복귀 및 캐시 로드/삭제/URL 파라미터 핸들러] ---
q_params = st.query_params

query_url = q_params.get("url")
if query_url:
    st.session_state.current_url = query_url.strip()
    st.session_state.trigger_search = True
    st.query_params.clear()
    st.rerun()

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


# --- [핵심] 상단 네비바 (templates/navbar.html 템플릿 렌더링) ---
is_video_loaded = bool(st.session_state.video_id and st.session_state.video_info and st.session_state.transcript_data)

st.markdown(render_navbar_html(CAT_ICON_B64), unsafe_allow_html=True)

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


clean_drawer_html = render_drawer_html(
    saved_count=len(cached_videos_list),
    cached_cards_html=cached_cards_html,
    clear_btn_html=clear_btn_html,
)
st.markdown(clean_drawer_html, unsafe_allow_html=True)

# 브라우저 DOM 이벤트 및 햄버거 메뉴 토글 / 바깥 영역 클릭 닫기 제어 스크립트 iframe 주입 (static/js/drawer.js)
components.html(f"<script>{load_js('drawer.js')}</script>", height=0)



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


    # 전체 화면을 하나로 통합한 일체형 컴포넌트 HTML (static/ 내 css, html, js 분리 렌더링)
    integrated_html = render_player_component(
        v_id=v_id,
        v_title=v_title,
        uploader_initial=uploader_initial,
        v_uploader=v_uploader,
        v_views=v_views,
        v_duration_str=v_duration_str,
        segments_count_val=segments_count_val,
        audio_size_str=audio_size_str,
        segments=segments_list,
        chapters=chapters,
        api_key=api_key_clean,
        safe_title=safe_title,
        audio_b64=audio_b64,
    )

    # 컴포넌트 높이 645px로 지정 (영화관 모드 시 JS syncParentFrameHeight로 동적 확장 및 원상 복구)
    components.html(integrated_html, height=645)


else:
    # --- 실시간 대본 AI 메인 홈 화면 (templates/index.html 템플릿 렌더링) ---
    st.markdown(render_index_html(), unsafe_allow_html=True)


