import os
import sys
import streamlit as st
from dotenv import load_dotenv

# 로컬 모듈 임포트
from downloader import get_video_info, download_audio
from transcriber import transcribe_audio_stream, get_client

# Windows 콘솔 인코딩 대응
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# .env 로드
load_dotenv()

# --- 페이지 기본 설정 (와이드 레이아웃) ---
st.set_page_config(
    page_title="YouTube AI Transcriber Studio",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed",  # 유튜브처럼 메인 콘텐츠에 집중하도록 사이드바 기본 축소
)

# --- 모던 유튜브 스타일 CSS 디자인 ---
st.markdown("""
<style>
    /* 전체 배경 및 폰트 */
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    * {
        font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* 상단 헤더 바 */
    .yt-navbar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.8rem 1.2rem;
        background: #0f0f0f;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        border: 1px solid #272727;
    }
    .yt-logo {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 1.25rem;
        font-weight: 700;
        color: #ffffff;
    }
    .yt-badge {
        background: #ff0000;
        color: white;
        padding: 2px 8px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    
    /* 비디오 정보 카드 */
    .video-card {
        background: #181818;
        border-radius: 14px;
        padding: 1.2rem;
        margin-top: 1rem;
        border: 1px solid #2a2a2a;
    }
    .video-title {
        font-size: 1.3rem;
        font-weight: 700;
        color: #f1f1f1;
        margin-bottom: 0.5rem;
        line-height: 1.4;
    }
    .video-meta {
        display: flex;
        align-items: center;
        gap: 12px;
        color: #aaaaaa;
        font-size: 0.9rem;
    }
    .channel-badge {
        background: #272727;
        padding: 4px 10px;
        border-radius: 20px;
        color: #e0e0e0;
        font-weight: 600;
        display: inline-flex;
        align-items: center;
        gap: 6px;
    }
    
    /* 우측 패널 카드 */
    .panel-card {
        background: #181818;
        border-radius: 14px;
        padding: 1.2rem;
        border: 1px solid #2a2a2a;
        height: 100%;
    }
    .panel-header {
        font-size: 1.15rem;
        font-weight: 700;
        color: #ffffff;
        margin-bottom: 1rem;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    
    /* 태그 칩 */
    .keyword-chip {
        display: inline-block;
        background: #272727;
        color: #3ea6ff;
        padding: 5px 12px;
        border-radius: 16px;
        font-size: 0.85rem;
        font-weight: 500;
        margin-right: 6px;
        margin-bottom: 6px;
    }
    
    /* 대화 말풍선 */
    .chat-bubble-user {
        background: #2b3945;
        color: #ffffff;
        padding: 10px 14px;
        border-radius: 12px 12px 0 12px;
        margin-bottom: 8px;
        font-size: 0.92rem;
        align-self: flex-end;
    }
    .chat-bubble-ai {
        background: #222222;
        color: #e0e0e0;
        padding: 10px 14px;
        border-radius: 12px 12px 12px 0;
        margin-bottom: 12px;
        font-size: 0.92rem;
        border-left: 3px solid #ff4b4b;
    }
    
    /* 유튜브 공식 알약 검색창 스타일 */
    div[data-testid="stForm"] {
        border: none !important;
        padding: 0 !important;
        margin: 0 !important;
        background: transparent !important;
    }
    .stTextInput input {
        background-color: #121212 !important;
        color: #f1f1f1 !important;
        border: 1px solid #333333 !important;
        border-radius: 20px 0 0 20px !important;
        height: 38px !important;
        padding-left: 16px !important;
        font-size: 0.86rem !important;
    }
    .stTextInput input:focus {
        border-color: #3ea6ff !important;
        box-shadow: 0 0 0 1px #3ea6ff !important;
    }
    div[data-testid="stForm"] .stButton button {
        background-color: #222222 !important;
        border: 1px solid #333333 !important;
        border-left: none !important;
        border-radius: 0 20px 20px 0 !important;
        color: #f1f1f1 !important;
        font-weight: 700 !important;
        font-size: 0.86rem !important;
        height: 38px !important;
        transition: all 0.2s ease !important;
    }
    div[data-testid="stForm"] .stButton button:hover {
        background-color: #ff0000 !important;
        border-color: #ff0000 !important;
        color: #ffffff !important;
    }
</style>
""", unsafe_allow_html=True)


# --- 세션 상태 관리 ---
if "result_text" not in st.session_state:
    st.session_state.result_text = None
if "audio_path" not in st.session_state:
    st.session_state.audio_path = None
if "video_info" not in st.session_state:
    st.session_state.video_info = None
if "summary_text" not in st.session_state:
    st.session_state.summary_text = None
if "keywords" not in st.session_state:
    st.session_state.keywords = []
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "translated_text" not in st.session_state:
    st.session_state.translated_text = None


# --- 상단 유튜브 스타일 헤더 바 ---
st.markdown("""
<div class="yt-navbar">
    <div class="yt-logo">
        <span style="color: #ff0000; font-size: 1.6rem;">▶</span>
        <span>Studio Transcriber</span>
        <span class="yt-badge">AI Powered</span>
    </div>
    <div style="color: #888; font-size: 0.85rem;">Google Gemini 3.5 & yt-dlp Engine</div>
</div>
""", unsafe_allow_html=True)


# --- 사이드바: 고급 환경 설정 ---
with st.sidebar:
    st.header("⚙️ 엔진 및 API 설정")
    env_api_key = os.environ.get("GEMINI_API_KEY", "")
    api_key_input = st.text_input(
        "Gemini API Key",
        value=env_api_key,
        type="password",
        help=".env 파일 또는 직접 입력할 수 있습니다.",
    )
    if not api_key_input:
        st.warning("⚠️ API 키가 필요합니다.")
    else:
        st.success("✅ API 키 인증됨")

    st.markdown("---")
    model_choice = st.selectbox(
        "STT 음성 인식 모델",
        options=["gemini-3.5-transcribe", "gemini-3.6-flash"],
        index=0,
        help="gemini-3.5-transcribe는 단어별 전사와 화자 구분에 최적화된 최신 모델입니다.",
    )

    download_dir = os.path.join(os.path.dirname(__file__), "downloads")
    os.makedirs(download_dir, exist_ok=True)


# --- 상단 중앙 검색 입력창 (유튜브 공식 알약형 중앙 정렬) ---
col_pad_l, col_center, col_pad_r = st.columns([1.5, 7, 1.5], gap="small")
with col_center:
    with st.form("stt_search_form", clear_on_submit=False, border=False):
        c_input, c_btn = st.columns([80, 20], gap="small")
        with c_input:
            youtube_url = st.text_input(
                "유튜브 URL 입력창",
                placeholder="분석하고 싶은 유튜브 영상 URL을 입력하세요 (예: https://www.youtube.com/watch?v=...)",
                label_visibility="collapsed",
            )
        with c_btn:
            start_btn = st.form_submit_button("🚀 자막 추출", type="primary", use_container_width=True)


# --- 변환 실행 로직 ---
if start_btn:
    if not youtube_url.strip():
        st.error("유튜브 영상 URL을 입력해주세요.")
    elif not api_key_input.strip():
        st.error("Gemini API 키가 필요합니다. 사이드바에서 키를 확인해주세요.")
    else:
        with st.status("🎬 유튜브 오디오 추출 및 AI 분석을 진행합니다...", expanded=True) as status:
            try:
                # 1. 다운로드
                status.write("📥 1/3: 유튜브 영상 메타데이터 분석 및 고음질 오디오 스트림 다운로드 중...")
                audio_path, video_info = download_audio(youtube_url.strip(), output_dir=download_dir)
                st.session_state.audio_path = audio_path
                st.session_state.video_info = video_info
                # 이전 분석 결과 리셋
                st.session_state.summary_text = None
                st.session_state.keywords = []
                st.session_state.chat_history = []
                st.session_state.translated_text = None
                status.write(f"✅ 오디오 추출 완료: **{video_info['title']}**")

                # 2. STT 전사
                status.write(f"🧠 2/3: Google Gemini (`{model_choice}`) 음성 전사 실행 중...")
                transcript_collector = []
                for chunk in transcribe_audio_stream(
                    audio_path=audio_path,
                    api_key=api_key_input.strip(),
                    model_name=model_choice,
                    prompt="이 오디오의 내용을 한국어로 정확하게 받아쓰기(전사)해줘. 문맥에 맞게 줄바꿈과 문장 부호를 자연스럽게 정리해줘.",
                ):
                    transcript_collector.append(chunk)

                final_text = "".join(transcript_collector)
                st.session_state.result_text = final_text

                # 3. 완료
                status.write("✨ 3/3: 트랜스크립트 변환 완료!")
                status.update(label="🎉 영상 분석 및 스크립트 추출이 성공적으로 완료되었습니다!", state="complete", expanded=False)

            except Exception as e:
                status.update(label="❌ 오류가 발생했습니다.", state="error", expanded=True)
                st.error(f"오류 상세: {str(e)}")


# --- 유튜브 스타일 2열 레이아웃 (좌측: 비디오 룸 / 우측: AI 패널) ---
if st.session_state.video_info and st.session_state.audio_path:
    info = st.session_state.video_info
    duration_min = info["duration"] // 60
    duration_sec = info["duration"] % 60
    
    st.markdown("---")
    left_col, right_col = st.columns([6, 5], gap="large")

    # ================= [좌측 열: 미디어 룸] =================
    with left_col:
        # 1. 비디오 플레이어
        st.video(info["url"])

        # 2. 비디오 메타데이터 카드
        st.markdown(f"""
        <div class="video-card">
            <div class="video-title">{info['title']}</div>
            <div class="video-meta">
                <span class="channel-badge">📺 {info['uploader']}</span>
                <span>⏱️ {duration_min}분 {duration_sec}초</span>
                <span>🔊 고음질 AAC/M4A 추출됨</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # 3. 오디오 전용 플레이어
        st.write(" ")
        st.markdown("**🎧 추출된 음성 원본 플레이어:**")
        if os.path.exists(st.session_state.audio_path):
            with open(st.session_state.audio_path, "rb") as f:
                st.audio(f.read())

        # 4. 액션 버튼 툴바
        st.write(" ")
        action_col1, action_col2 = st.columns(2)
        safe_title = "".join(c for c in info["title"] if c.isalnum() or c in (" ", "_", "-")).rstrip()
        
        with action_col1:
            st.download_button(
                label="📥 텍스트 대본 다운로드 (.txt)",
                data=(st.session_state.result_text or "").encode("utf-8"),
                file_name=f"{safe_title}_transcript.txt",
                mime="text/plain",
                use_container_width=True,
            )
        with action_col2:
            # 오디오 파일 다운로드 제공
            with open(st.session_state.audio_path, "rb") as f:
                audio_bytes = f.read()
            st.download_button(
                label="🎵 오디오 파일 다운로드 (.m4a)",
                data=audio_bytes,
                file_name=os.path.basename(st.session_state.audio_path),
                mime="audio/m4a",
                use_container_width=True,
            )

    # ================= [우측 열: AI 인터랙티브 사이드 패널] =================
    with right_col:
        # 유튜브 우측 추천목록 위치에 배치되는 AI 탭 네비게이션
        tab_script, tab_summary, tab_chat, tab_translate = st.tabs([
            "📑 전체 스크립트",
            "💡 AI 스마트 요약",
            "💬 영상에 질문하기",
            "🌐 다국어 번역",
        ])

        # --- TAB 1: 전체 스크립트 & 키워드 검색 ---
        with tab_script:
            st.markdown('<div class="panel-header">📑 전체 음성 트랜스크립트</div>', unsafe_allow_html=True)
            
            # 본문 내 실시간 검색창
            search_query = st.text_input("🔎 대본 내 단어 검색", placeholder="찾고 싶은 키워드를 입력하세요...")
            
            script_content = st.session_state.result_text or "추출된 스크립트가 없습니다."
            
            if search_query.strip():
                count = script_content.count(search_query.strip())
                st.caption(f"'{search_query}' 검색 결과: 총 {count}회 언급되었습니다.")
            
            # 스크립트 텍스트 영역
            st.text_area(
                "대본 내용",
                value=script_content,
                height=420,
                label_visibility="collapsed",
            )

        # --- TAB 2: AI 스마트 요약 & 토픽 키워드 ---
        with tab_summary:
            st.markdown('<div class="panel-header">💡 AI 핵심 요약 및 토픽</div>', unsafe_allow_html=True)

            if st.session_state.summary_text is None:
                if st.button("⚡ AI 3줄 요약 & 핵심 키워드 생성하기", type="primary", use_container_width=True):
                    with st.spinner("Gemini AI가 내용을 분석하고 있습니다..."):
                        try:
                            client = get_client(api_key_input.strip())
                            prompt = f"""다음 유튜브 영상의 트랜스크립트를 분석해줘:
1. 가장 중요한 핵심 내용을 3개의 불렛포인트(-)로 명확하게 요약해줘.
2. 영상의 핵심 주제 키워드 5개를 쉼표(,)로 구분해서 작성해줘.

형식:
[요약]
- 요약 1
- 요약 2
- 요약 3

[키워드]
키워드1, 키워드2, 키워드3, 키워드4, 키워드5

트랜스크립트:
{st.session_state.result_text}"""
                            res = client.models.generate_content(
                                model="gemini-3.6-flash",
                                contents=prompt,
                            )
                            raw_res = res.text
                            st.session_state.summary_text = raw_res
                            st.rerun()
                        except Exception as e:
                            st.error(f"요약 실패: {e}")
            else:
                st.markdown(st.session_state.summary_text)
                if st.button("🔄 요약 다시 생성하기", use_container_width=True):
                    st.session_state.summary_text = None
                    st.rerun()

        # --- TAB 3: 영상 내용 Q&A (영상에 질문하기) ---
        with tab_chat:
            st.markdown('<div class="panel-header">💬 영상 내용에 대해 질문해보세요</div>', unsafe_allow_html=True)
            st.caption("영상 전체를 다 보지 않아도 궁금한 점을 Gemini에게 바로 물어볼 수 있습니다.")

            # 대화 기록 표시
            chat_container = st.container(height=300)
            with chat_container:
                if not st.session_state.chat_history:
                    st.info("예: '이 영상에서 언급된 핵심 수치가 뭐야?', '결론이 어떻게 끝났어?'")
                for q, a in st.session_state.chat_history:
                    st.markdown(f'<div class="chat-bubble-user">🙋 <b>질문:</b> {q}</div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="chat-bubble-ai">🤖 <b>답변:</b> {a}</div>', unsafe_allow_html=True)

            user_question = st.text_input("질문 입력", placeholder="영상 내용과 관련된 질문을 입력하세요...", label_visibility="collapsed")
            if st.button("질문 전송", use_container_width=True):
                if user_question.strip():
                    with st.spinner("답변 생성 중..."):
                        try:
                            client = get_client(api_key_input.strip())
                            qa_prompt = f"""당신은 영상 분석 AI 전문가입니다. 아래 제공된 영상 트랜스크립트 내용을 바탕으로 사용자의 질문에 친절하고 정확하게 답변해주세요.

[영상 제목]: {info['title']}
[트랜스크립트]:
{st.session_state.result_text}

[사용자 질문]:
{user_question}"""
                            ans_res = client.models.generate_content(
                                model="gemini-3.6-flash",
                                contents=qa_prompt,
                            )
                            st.session_state.chat_history.append((user_question, ans_res.text))
                            st.rerun()
                        except Exception as e:
                            st.error(f"답변 실패: {e}")

        # --- TAB 4: 다국어 번역 ---
        with tab_translate:
            st.markdown('<div class="panel-header">🌐 대본 다국어 번역</div>', unsafe_allow_html=True)
            
            target_lang = st.selectbox("번역할 목표 언어 선택", ["영어 (English)", "일본어 (日本語)", "중국어 (中文)", "스페인어 (Español)"])
            
            if st.button(f"🚀 {target_lang}로 번역하기", use_container_width=True):
                with st.spinner(f"{target_lang}로 번역 중..."):
                    try:
                        client = get_client(api_key_input.strip())
                        trans_prompt = f"""다음 한국어 트랜스크립트를 자연스러운 {target_lang}로 전문 번역해줘:\n\n{st.session_state.result_text}"""
                        trans_res = client.models.generate_content(
                            model="gemini-3.6-flash",
                            contents=trans_prompt,
                        )
                        st.session_state.translated_text = trans_res.text
                    except Exception as e:
                        st.error(f"번역 실패: {e}")

            if st.session_state.translated_text:
                st.text_area("번역 결과", value=st.session_state.translated_text, height=300, label_visibility="collapsed")
                st.download_button(
                    label="💾 번역된 대본 다운로드 (.txt)",
                    data=st.session_state.translated_text.encode("utf-8"),
                    file_name=f"{safe_title}_{target_lang[:2]}_translation.txt",
                    mime="text/plain",
                    use_container_width=True,
                )
else:
    # URL 입력 전 대기 화면 (모던 안내 카드)
    st.markdown("""
    <div style="background: #161616; border-radius: 16px; padding: 3rem 2rem; text-align: center; border: 1px dashed #333; margin-top: 2rem;">
        <div style="font-size: 3rem; margin-bottom: 1rem;">🎬</div>
        <h3 style="color: #ffffff; margin-bottom: 0.5rem;">유튜브 영상 주소를 입력하여 AI 전사를 시작하세요</h3>
        <p style="color: #888; max-width: 600px; margin: 0 auto 1.5rem auto;">
            유튜브의 고음질 오디오 스트림을 추출하여 Google Gemini 최신 모델로 완벽한 텍스트 대본과 AI 요약, 번역 및 Q&A를 제공합니다.
        </p>
        <div style="display: flex; justify-content: center; gap: 12px; flex-wrap: wrap;">
            <span class="keyword-chip">⚡ 초고속 m4a 추출</span>
            <span class="keyword-chip">🎙️ Gemini 3.5 Transcribe</span>
            <span class="keyword-chip">💡 3줄 요약 & 토픽</span>
            <span class="keyword-chip">💬 영상 Q&A AI</span>
            <span class="keyword-chip">🌐 다국어 번역</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
