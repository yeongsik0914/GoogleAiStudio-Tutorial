import os
import sys
import json
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

# 로컬 엔진 모듈 임포트
from downloader import extract_video_id, get_video_info, download_audio
from transcribe_engine import transcribe_with_timestamps, format_seconds
from qa_engine import answer_question_with_timestamps

# Windows 환경 한글 출력 인코딩 대응
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

load_dotenv()

# --- 페이지 설정 (와이드 모드, 사이드바 닫힘) ---
st.set_page_config(
    page_title="AI 유튜브 검색기",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# --- 한 화면에 딱 맞추는 모던 다크 UI CSS ---
st.markdown("""
<style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    * {
        font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* Streamlit 기본 헤더 투명화 및 안전 여백 확보 */
    header[data-testid="stHeader"] {
        background: transparent !important;
        height: 2.5rem !important;
    }
    
    /* 기본 여백 설정 (상단 헤더와 겹치지 않도록 padding-top 3.5rem 지정) */
    .block-container {
        padding-top: 3.5rem !important;
        padding-bottom: 0.8rem !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
        max-width: 100% !important;
    }
    
    /* 상단 슬림 네비바 */
    .nav-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        background: #111111;
        border: 1px solid #282828;
        border-radius: 12px;
        padding: 10px 18px;
        margin-bottom: 14px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.5);
    }
    .brand-title {
        display: flex;
        align-items: center;
        gap: 10px;
        font-size: 1.25rem;
        font-weight: 800;
        color: #ffffff;
    }
    .badge-gemini {
        background: linear-gradient(135deg, #ff4b4b, #ff7675);
        color: white;
        padding: 3px 10px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 0.3px;
    }

    /* 챗봇 컨테이너 스타일 */
    .chat-card {
        background: #141414;
        border: 1px solid #242424;
        border-radius: 12px;
        padding: 12px;
        height: 100%;
    }
    .chat-bubble-user {
        background: #253342;
        color: #ffffff;
        padding: 8px 12px;
        border-radius: 10px 10px 2px 10px;
        margin-bottom: 8px;
        font-size: 0.88rem;
        line-height: 1.35;
    }
    .chat-bubble-ai {
        background: #1c1c1c;
        color: #ececec;
        padding: 10px 14px;
        border-radius: 10px 10px 10px 2px;
        margin-bottom: 10px;
        font-size: 0.88rem;
        border-left: 3px solid #ff4b4b;
        line-height: 1.45;
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
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []


# --- 상단 슬림 네비바 ---
st.markdown("""
<div class="nav-header">
    <div class="brand-title">
        <svg width="26" height="18" viewBox="0 0 28 20" fill="none">
            <rect width="28" height="20" rx="5" fill="#FF0000"/>
            <polygon points="11,6 19,10 11,14" fill="#FFFFFF"/>
        </svg>
        <span>AI 유튜브 검색기</span>
        <span class="badge-gemini">Gemini 3.5 & 3.8</span>
    </div>
    <div style="color: #888; font-size: 0.84rem;">실시간 대본 싱크 • 무중단 음향 제어 • 영상 질의응답</div>
</div>
""", unsafe_allow_html=True)


# --- 사이드바 설정 ---
with st.sidebar:
    st.header("⚙️ 환경 설정")
    env_api_key = os.environ.get("GEMINI_API_KEY", "")
    api_key_input = st.text_input(
        "Gemini API Key",
        value=env_api_key,
        type="password",
        help=".env 파일 또는 직접 입력 가능",
    )
    if not api_key_input:
        st.warning("⚠️ API 키를 입력해주세요.")
    else:
        st.success("✅ API 키 인증 완료")


# --- 상단 검색창 (유튜브 검색창 스타일, 한 줄 배치) ---
col_search, col_btn = st.columns([84, 16], gap="small")
with col_search:
    url_input = st.text_input(
        "유튜브 링크 주소",
        placeholder="유튜브 영상 주소를 입력하세요 (예: https://www.youtube.com/watch?v=...)",
        label_visibility="collapsed",
    )
with col_btn:
    search_submit = st.button("🔍 검색 및 분석", type="primary", use_container_width=True)


# 다운로드 폴더
download_dir = os.path.join(os.path.dirname(__file__), "downloads")
os.makedirs(download_dir, exist_ok=True)


# --- 검색 및 분석 실행 ---
if search_submit:
    if not url_input.strip():
        st.error("유튜브 영상 링크를 입력해주세요.")
    elif not api_key_input.strip():
        st.error("사이드바에서 Gemini API 키를 입력해주세요.")
    else:
        v_id = extract_video_id(url_input.strip())
        if not v_id:
            st.error("올바른 유튜브 링크 형식이 아닙니다.")
        else:
            with st.status("🎬 영상 로드 및 타임스탬프 분석 중...", expanded=True) as status:
                try:
                    status.write("📥 1/3: 영상 정보 조회 및 오디오 추출...")
                    audio_path, video_info = download_audio(url_input.strip(), output_dir=download_dir)
                    st.session_state.video_id = v_id
                    st.session_state.video_info = video_info
                    st.session_state.audio_path = audio_path

                    status.write("🎙️ 2/3: `gemini-3.5-transcribe` 모델로 실시간 타임스탬프 추출 중...")
                    transcript_res = transcribe_with_timestamps(audio_path, api_key=api_key_input.strip())
                    st.session_state.transcript_data = transcript_res

                    st.session_state.chat_messages = []
                    status.write("✨ 3/3: 분석 완료!")
                    status.update(label="🎉 영상 분석 완료!", state="complete", expanded=False)

                except Exception as e:
                    status.update(label="❌ 오류 발생", state="error", expanded=True)
                    st.error(f"오류 상세: {e}")


# --- 메인 2열 레이아웃: 한 화면에 맞춘 컴팩트 뷰 ---
if st.session_state.video_id and st.session_state.video_info and st.session_state.transcript_data:
    v_id = st.session_state.video_id
    v_info = st.session_state.video_info
    t_data = st.session_state.transcript_data
    segments_json = json.dumps(t_data.get("segments", []), ensure_ascii=False)

    col_media, col_chat = st.columns([62, 38], gap="medium")

    # ==============================================================
    # 📺 [좌측]: 영상 전체 표시 + 컨트롤 + 라이브 대사 + 3개 대본
    # ==============================================================
    with col_media:
        # 플레이어 + 무중단 볼륨 + 라이브 대사 + 딱 3개씩 보이는 대본 리스트 통합 컴포넌트
        player_html = f"""
        <!DOCTYPE html>
        <html lang="ko">
        <head>
            <meta charset="UTF-8">
            <style>
                @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
                * {{
                    box-sizing: border-box;
                    font-family: 'Pretendard', sans-serif;
                    margin: 0;
                    padding: 0;
                }}
                body {{
                    background: transparent;
                    color: #fff;
                    overflow: hidden;
                }}
                
                /* [해결] 영상이 잘리지 않도록 16:9 비율 고정 및 반응형 뷰포트 맞춤 */
                .player-box {{
                    position: relative;
                    width: 100%;
                    aspect-ratio: 16 / 9;
                    max-height: 330px;
                    background: #000;
                    border-radius: 10px;
                    overflow: hidden;
                    box-shadow: 0 4px 16px rgba(0,0,0,0.6);
                    margin: 0 auto;
                }}
                .player-box iframe {{
                    position: absolute;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    border: 0;
                }}
                
                /* 슬림 무중단 컨트롤 바 */
                .ctrl-bar {{
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    background: #161616;
                    border: 1px solid #262626;
                    border-radius: 8px;
                    padding: 6px 12px;
                    margin-top: 8px;
                    gap: 12px;
                }}
                .vol-group {{
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    flex: 1;
                }}
                .vol-slider {{
                    -webkit-appearance: none;
                    width: 100%;
                    height: 5px;
                    border-radius: 3px;
                    background: #333;
                    outline: none;
                    cursor: pointer;
                }}
                .vol-slider::-webkit-slider-thumb {{
                    -webkit-appearance: none;
                    width: 14px;
                    height: 14px;
                    border-radius: 50%;
                    background: #ff4b4b;
                    cursor: pointer;
                    box-shadow: 0 0 4px rgba(255, 75, 75, 0.7);
                }}
                .vol-badge {{
                    font-size: 0.78rem;
                    font-weight: 700;
                    color: #ff4b4b;
                    min-width: 36px;
                }}
                .time-badge {{
                    font-size: 0.78rem;
                    color: #888;
                    font-variant-numeric: tabular-nums;
                    white-space: nowrap;
                }}
                
                /* 실시간 라이브 대사 박스 */
                .live-box {{
                    background: linear-gradient(90deg, #132338 0%, #0d1624 100%);
                    border: 1px solid #0284c7;
                    border-radius: 8px;
                    padding: 8px 12px;
                    margin-top: 8px;
                    box-shadow: 0 2px 8px rgba(2, 132, 199, 0.2);
                }}
                .live-head {{
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    margin-bottom: 3px;
                }}
                .live-tag {{
                    display: inline-flex;
                    align-items: center;
                    gap: 5px;
                    background: #ef4444;
                    color: #fff;
                    padding: 1px 6px;
                    border-radius: 4px;
                    font-size: 0.68rem;
                    font-weight: 800;
                }}
                .live-dot {{
                    width: 5px;
                    height: 5px;
                    background: #fff;
                    border-radius: 50%;
                    animation: pulse 1s infinite alternate;
                }}
                @keyframes pulse {{
                    from {{ opacity: 0.3; }}
                    to {{ opacity: 1; }}
                }}
                .live-time {{
                    color: #38bdf8;
                    font-size: 0.75rem;
                    font-weight: 700;
                }}
                .live-text {{
                    color: #ffffff;
                    font-size: 0.95rem;
                    font-weight: 700;
                    line-height: 1.35;
                    white-space: nowrap;
                    overflow: hidden;
                    text-overflow: ellipsis;
                }}

                /* [핵심] 대본에 표시되는 텍스트 수를 3개씩만 나오도록 높이 고정 (약 130px) */
                .transcript-section {{
                    margin-top: 8px;
                    background: #131313;
                    border: 1px solid #222;
                    border-radius: 8px;
                    padding: 6px 10px;
                }}
                .transcript-head-row {{
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    margin-bottom: 6px;
                }}
                .transcript-title {{
                    font-size: 0.82rem;
                    font-weight: 700;
                    color: #aaa;
                    display: flex;
                    align-items: center;
                    gap: 5px;
                }}
                .search-input {{
                    background: #1f1f1f;
                    border: 1px solid #333;
                    border-radius: 5px;
                    padding: 3px 8px;
                    color: #fff;
                    font-size: 0.75rem;
                    width: 140px;
                    outline: none;
                }}
                .search-input:focus {{
                    border-color: #38bdf8;
                }}
                
                /* 딱 3개 카드가 화면에 피트되는 높이 (128px) */
                .transcript-scroll-view {{
                    height: 128px;
                    overflow-y: auto;
                    display: flex;
                    flex-direction: column;
                    gap: 5px;
                    padding-right: 4px;
                }}
                .transcript-scroll-view::-webkit-scrollbar {{
                    width: 4px;
                }}
                .transcript-scroll-view::-webkit-scrollbar-thumb {{
                    background: #333;
                    border-radius: 2px;
                }}
                
                .card-item {{
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    padding: 6px 10px;
                    background: #1a1a1a;
                    border: 1px solid transparent;
                    border-radius: 6px;
                    cursor: pointer;
                    transition: all 0.15s ease;
                    min-height: 36px;
                    max-height: 38px;
                }}
                .card-item:hover {{
                    background: #242424;
                    border-color: #38bdf8;
                }}
                .card-item.active {{
                    background: #15324b !important;
                    border-color: #38bdf8 !important;
                    box-shadow: 0 0 8px rgba(56, 189, 248, 0.4);
                }}
                .time-chip {{
                    background: #262626;
                    color: #38bdf8;
                    font-size: 0.75rem;
                    font-weight: 700;
                    padding: 2px 6px;
                    border-radius: 4px;
                    white-space: nowrap;
                    font-variant-numeric: tabular-nums;
                }}
                .card-item.active .time-chip {{
                    background: #38bdf8;
                    color: #0b1120;
                }}
                .text-content {{
                    color: #bbb;
                    font-size: 0.82rem;
                    line-height: 1.25;
                    white-space: nowrap;
                    overflow: hidden;
                    text-overflow: ellipsis;
                    flex: 1;
                }}
                .card-item.active .text-content {{
                    color: #fff;
                    font-weight: 600;
                }}
            </style>
        </head>
        <body>
            <!-- 1. 비디오 뷰포트 (16:9 완전 표시, 잘림 없음) -->
            <div class="player-box">
                <div id="yt-player"></div>
            </div>

            <!-- 2. 무중단 실시간 음향 조절 바 -->
            <div class="ctrl-bar">
                <div class="vol-group">
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="#ff4b4b">
                        <path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"/>
                    </svg>
                    <input type="range" class="vol-slider" id="vol-slider" min="0" max="100" value="100" oninput="changeVol(this.value)">
                    <span class="vol-badge" id="vol-badge">100%</span>
                </div>
                <div class="time-badge">
                    ⏱️ <span id="time-current">00:00</span> / <span id="time-total">00:00</span>
                </div>
            </div>

            <!-- 3. 실시간 라이브 대사 (한 줄 컴팩트) -->
            <div class="live-box">
                <div class="live-head">
                    <div class="live-tag">
                        <span class="live-dot"></span>
                        <span>실시간 대사</span>
                    </div>
                    <div class="live-time" id="live-time-display">00:00</div>
                </div>
                <div class="live-text" id="live-text-display">영상을 재생하면 실시간 대사가 여기에 나타납니다.</div>
            </div>

            <!-- 4. 전체 대본 (딱 3개씩 보이는 컴팩트 스크롤 뷰) -->
            <div class="transcript-section">
                <div class="transcript-head-row">
                    <div class="transcript-title">
                        <span>📑 시간대별 대본</span>
                        <span style="font-size: 0.7rem; color: #666;">(클릭 시 즉시 이동)</span>
                    </div>
                    <input type="text" class="search-input" placeholder="🔍 대본 검색..." oninput="onSearchFilter(this.value)">
                </div>
                <div class="transcript-scroll-view" id="transcript-list">
                    <!-- JS 카드가 들어갑니다 -->
                </div>
            </div>

            <script>
                var segments = {segments_json};
                var player;
                var currentActiveIdx = -1;

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
                            'onReady': onPlayerReady,
                            'onStateChange': onPlayerStateChange
                        }}
                    }});
                }}

                function fmtSec(sec) {{
                    var total = Math.floor(sec);
                    var m = Math.floor(total / 60);
                    var s = total % 60;
                    return (m < 10 ? "0" + m : m) + ":" + (s < 10 ? "0" + s : s);
                }}

                function onPlayerReady(event) {{
                    event.target.setVolume(100);
                    event.target.playVideo();
                    renderList(segments);

                    var dur = event.target.getDuration();
                    if (dur > 0) {{
                        document.getElementById('time-total').innerText = fmtSec(dur);
                    }}

                    // 200ms 주기로 실시간 싱크 체크
                    setInterval(syncTranscript, 200);
                }}

                function onPlayerStateChange(event) {{
                    var dur = player.getDuration();
                    if (dur > 0) {{
                        document.getElementById('time-total').innerText = fmtSec(dur);
                    }}
                }}

                // 무중단 볼륨 조절 (페이지 새로고침 없음)
                function changeVol(v) {{
                    if (player && player.setVolume) {{
                        player.setVolume(v);
                        document.getElementById('vol-badge').innerText = v + "%";
                    }}
                }}

                // 특정 시간대로 점프
                function jumpTo(sec) {{
                    if (player && player.seekTo) {{
                        player.seekTo(sec, true);
                        player.playVideo();
                    }}
                }}

                function renderList(list) {{
                    var box = document.getElementById('transcript-list');
                    box.innerHTML = "";
                    if (!list || list.length === 0) {{
                        box.innerHTML = "<div style='color: #666; font-size: 0.8rem; text-align: center; padding: 10px;'>검색 결과가 없습니다.</div>";
                        return;
                    }}
                    list.forEach(function(s, idx) {{
                        var item = document.createElement('div');
                        item.className = 'card-item';
                        item.id = 'card-' + idx;
                        item.onclick = function() {{ jumpTo(s.start); }};
                        item.innerHTML = '<span class="time-chip">' + s.time_str + '</span><span class="text-content">' + s.text + '</span>';
                        box.appendChild(item);
                    }});
                }}

                function onSearchFilter(val) {{
                    var q = val.trim().toLowerCase();
                    if (!q) {{
                        renderList(segments);
                        return;
                    }}
                    var filtered = segments.filter(function(s) {{
                        return s.text.toLowerCase().indexOf(q) !== -1;
                    }});
                    renderList(filtered);
                }}

                // 실시간 대사 싱크 및 카드 활성화/자동 스크롤
                function syncTranscript() {{
                    if (!player || !player.getCurrentTime) return;
                    var cur = player.getCurrentTime();
                    document.getElementById('time-current').innerText = fmtSec(cur);

                    var targetIdx = -1;
                    for (var i = 0; i < segments.length; i++) {{
                        if (cur >= segments[i].start && cur <= (segments[i].end + 0.3)) {{
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

                    if (targetIdx !== -1 && targetIdx !== currentActiveIdx) {{
                        currentActiveIdx = targetIdx;
                        var curSeg = segments[targetIdx];

                        // 라이브 배너 대사 업데이트
                        document.getElementById('live-time-display').innerText = curSeg.time_str;
                        document.getElementById('live-text-display').innerText = curSeg.text;

                        // 이전 활성 카드 해제
                        var prev = document.querySelector('.card-item.active');
                        if (prev) prev.classList.remove('active');

                        // 현재 카드 활성화 및 자동 스크롤
                        var activeEl = document.getElementById('card-' + targetIdx);
                        if (activeEl) {{
                            activeEl.classList.add('active');
                            activeEl.scrollIntoView({{ behavior: 'smooth', block: 'nearest' }});
                        }}
                    }}
                }}
            </script>
        </body>
        </html>
        """
        # 한 화면에 꼭 맞는 높이로 최적화
        components.html(player_html, height=545)

        # 미니멀 정보 & 다운로드 바 (한 줄 배치)
        sub_c1, sub_c2, sub_c3 = st.columns([3, 1.2, 1.2], gap="small")
        with sub_c1:
            st.caption(f"📺 **{v_info['uploader']}** | ⏱️ {v_info['duration']//60}분 {v_info['duration']%60}초 | 👀 {v_info['view_count']:,}회")
        with sub_c2:
            safe_title = "".join(c for c in v_info["title"] if c.isalnum() or c in (" ", "_", "-")).rstrip()
            st.download_button(
                "📥 대본.txt",
                data=t_data.get("full_text", "").encode("utf-8"),
                file_name=f"{safe_title}_transcript.txt",
                mime="text/plain",
                use_container_width=True,
            )
        with sub_c3:
            if st.session_state.audio_path and os.path.exists(st.session_state.audio_path):
                with open(st.session_state.audio_path, "rb") as f:
                    st.download_button(
                        "🎵 오디오.m4a",
                        data=f.read(),
                        file_name=os.path.basename(st.session_state.audio_path),
                        mime="audio/m4a",
                        use_container_width=True,
                    )

    # ==============================================================
    # 💬 [우측]: 영상 우측에 딱 붙어 한 화면에 피트되는 챗봇
    # ==============================================================
    with col_chat:
        st.markdown("""
        <div style="background: #141414; padding: 8px 12px; border-radius: 8px; border: 1px solid #242424; margin-bottom: 8px; display: flex; align-items: center; justify-content: space-between;">
            <div style="font-weight: 700; font-size: 0.95rem; color: #fff; display: flex; align-items: center; gap: 6px;">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="#38bdf8">
                    <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H6l-2 2V4h16v12z"/>
                </svg>
                <span>Gemini 3.8 Flash 영상 챗봇</span>
            </div>
            <span style="font-size: 0.72rem; color: #38bdf8; background: #0c2d48; padding: 2px 6px; border-radius: 4px;">대본 실시간 연동</span>
        </div>
        """, unsafe_allow_html=True)

        # 챗봇 대화 스크롤 영역 (좌측 컴포넌트와 높이 정확히 일치)
        chat_box = st.container(height=450)
        with chat_box:
            if not st.session_state.chat_messages:
                st.info("💡 **영상에 대해 질문해보세요:**\n- 이 영상에서 가장 중요한 핵심 내용이 뭐야?\n- 특정 인물이나 사건이 어떻게 언급됐어?\n- 결론이 어떻게 끝났어?")
            
            for msg in st.session_state.chat_messages:
                st.markdown(f'<div class="chat-bubble-user">🙋 <b>질문:</b> {msg["q"]}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="chat-bubble-ai">🤖 <b>Gemini 3.8 Flash:</b><br>{msg["a"]}</div>', unsafe_allow_html=True)
                if msg.get("sec", 0) > 0:
                    st.caption(f"📍 관련 구간: **[{msg.get('ts', '00:00')}]** ({int(msg['sec'])}초)")

        # 컴팩트 질문 입력창
        q_col, send_col = st.columns([82, 18], gap="small")
        with q_col:
            user_q = st.text_input(
                "질문",
                placeholder="영상에 대해 궁금한 점을 입력하세요...",
                key="chat_in",
                label_visibility="collapsed",
            )
        with send_col:
            send_btn = st.button("전송", type="primary", use_container_width=True)

        if send_btn and user_q.strip():
            with st.spinner("Gemini 3.8 Flash 답변 생성 중..."):
                try:
                    segments = t_data.get("segments", [])
                    full_text = t_data.get("full_text", "")
                    qa_res = answer_question_with_timestamps(
                        question=user_q.strip(),
                        segments=segments,
                        full_text=full_text,
                        api_key=api_key_input.strip(),
                    )
                    st.session_state.chat_messages.append({
                        "q": user_q.strip(),
                        "a": qa_res["answer"],
                        "ts": qa_res.get("relevant_timestamp", "00:00"),
                        "sec": qa_res.get("relevant_seconds", 0.0),
                    })
                    st.rerun()
                except Exception as e:
                    st.error(f"답변 생성 실패: {e}")

else:
    # 초기 대기 화면
    st.markdown("""
    <div style="background: #131313; border-radius: 12px; padding: 2.5rem 1.5rem; text-align: center; border: 1px dashed #2a2a2a; margin-top: 1rem;">
        <div style="font-size: 2.8rem; margin-bottom: 0.6rem;">🎬</div>
        <h3 style="color: #ffffff; margin-bottom: 0.4rem;">AI 유튜브 검색기</h3>
        <p style="color: #888; max-width: 580px; margin: 0 auto 1.2rem auto; font-size: 0.9rem; line-height: 1.5;">
            상단 검색창에 유튜브 영상 링크를 입력하세요.<br>
            <b>Gemini 3.5 Transcribe</b> 실시간 대본 싱크와 <b>Gemini 3.8 Flash</b> 영상 질의응답이 한 화면에서 동작합니다.
        </p>
        <div style="display: flex; justify-content: center; gap: 8px; flex-wrap: wrap;">
            <span style="background: #202020; color: #38bdf8; padding: 4px 10px; border-radius: 16px; font-size: 0.8rem;">✨ 16:9 완전 영상 뷰</span>
            <span style="background: #202020; color: #ff4b4b; padding: 4px 10px; border-radius: 16px; font-size: 0.8rem;">🔊 끊김없는 볼륨 조절</span>
            <span style="background: #202020; color: #10b981; padding: 4px 10px; border-radius: 16px; font-size: 0.8rem;">📑 대본 3개 컴팩트 뷰</span>
            <span style="background: #202020; color: #f59e0b; padding: 4px 10px; border-radius: 16px; font-size: 0.8rem;">💬 우측 Gemini 3.8 챗봇</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
