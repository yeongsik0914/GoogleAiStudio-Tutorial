import os
import sys
import streamlit as st
from dotenv import load_dotenv

# 로컬 모듈 임포트
from downloader import get_video_info, download_audio
from transcriber import transcribe_audio_stream, transcribe_audio_full, get_client

# Windows 환경 콘솔 인코딩 대응
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# .env 로드
load_dotenv()

# --- 페이지 기본 설정 ---
st.set_page_config(
    page_title="YouTube Audio & Gemini STT",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- 커스텀 스타일 ---
st.markdown("""
<style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        color: #666;
        font-size: 1.05rem;
        margin-bottom: 1.5rem;
    }
    .stDownloadButton button {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)


# --- 사이드바 설정 ---
with st.sidebar:
    st.header("⚙️ 서비스 설정")
    
    # API 키 관리
    env_api_key = os.environ.get("GEMINI_API_KEY", "")
    api_key_input = st.text_input(
        "Gemini API Key",
        value=env_api_key,
        type="password",
        help=".env 파일에 GEMINI_API_KEY가 있으면 자동으로 불러옵니다.",
    )
    
    if not api_key_input:
        st.warning("⚠️ Gemini API 키를 입력하거나 .env 파일에 등록해주세요.")
    else:
        st.success("✅ API 키가 준비되었습니다.")

    st.markdown("---")
    
    # 모델 선택
    st.subheader("🤖 AI 모델 선택")
    model_choice = st.selectbox(
        "STT 전사 모델",
        options=["gemini-3.5-transcribe", "gemini-3.6-flash"],
        index=0,
        help="gemini-3.5-transcribe는 단어별 타임스탬프 및 화자 분리를 지원하는 최신 전사 전용 모델입니다.",
    )

    # 전사 프롬프트
    prompt_instruction = st.text_area(
        "전사 지시 프롬프트",
        value="이 오디오의 내용을 한국어로 정확하게 받아쓰기(전사)해줘. 문맥에 맞게 줄바꿈과 구두점을 자연스럽게 정리해줘.",
        height=100,
    )

    # 다운로드 디렉터리
    download_dir = os.path.join(os.path.dirname(__file__), "downloads")
    os.makedirs(download_dir, exist_ok=True)


# --- 메인 화면 ---
st.markdown('<div class="main-title">🎙️ 유튜브 오디오 다운로드 & Gemini STT 트랜스크립트</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">유튜브 영상 URL을 입력하면 원본 오디오를 추출하고 Google Gemini로 정확한 텍스트를 전사합니다.</div>', unsafe_allow_html=True)

# URL 입력 섹션
url_col, btn_col = st.columns([5, 1])
with url_col:
    youtube_url = st.text_input(
        "유튜브 영상 URL 입력",
        placeholder="https://www.youtube.com/watch?v=... 또는 https://youtu.be/...",
        label_visibility="collapsed",
    )
with btn_col:
    start_btn = st.button("🚀 변환 시작", type="primary", use_container_width=True)

# 세션 상태 초기화
if "result_text" not in st.session_state:
    st.session_state.result_text = None
if "audio_path" not in st.session_state:
    st.session_state.audio_path = None
if "video_info" not in st.session_state:
    st.session_state.video_info = None

# 변환 로직 실행
if start_btn:
    if not youtube_url.strip():
        st.error("유튜브 영상 URL을 입력해주세요.")
    elif not api_key_input.strip():
        st.error("Gemini API Key가 필요합니다. 사이드바에서 키를 입력해주세요.")
    else:
        # 상태 진행 표시
        with st.status("🎬 작업을 처리하고 있습니다...", expanded=True) as status:
            try:
                # 1단계: 영상 정보 및 오디오 다운로드
                status.write("📥 1/3: 유튜브 영상 분석 및 오디오 다운로드 중...")
                audio_path, video_info = download_audio(youtube_url.strip(), output_dir=download_dir)
                st.session_state.audio_path = audio_path
                st.session_state.video_info = video_info
                status.write(f"✅ 오디오 다운로드 완료: **{video_info['title']}**")

                # 2단계: Gemini STT 호출
                status.write(f"🧠 2/3: Gemini AI (`{model_choice}`)로 음성 전사 중...")
                
                # 스트리밍 텍스트 수신
                transcript_collector = []
                for chunk in transcribe_audio_stream(
                    audio_path=audio_path,
                    api_key=api_key_input.strip(),
                    model_name=model_choice,
                    prompt=prompt_instruction,
                ):
                    transcript_collector.append(chunk)

                final_text = "".join(transcript_collector)
                st.session_state.result_text = final_text

                # 3단계: 완료
                status.write("✨ 3/3: 트랜스크립트 변환 완료!")
                status.update(label="🎉 모든 작업이 성공적으로 완료되었습니다!", state="complete", expanded=False)

            except Exception as e:
                status.update(label="❌ 오류가 발생했습니다.", state="error", expanded=True)
                st.error(f"오류 상세: {str(e)}")


# 결과 표시 섹션
if st.session_state.video_info and st.session_state.audio_path:
    info = st.session_state.video_info
    
    st.markdown("---")
    media_col, content_col = st.columns([1, 1])

    with media_col:
        st.subheader("📺 원본 영상 및 추출된 오디오")
        st.video(info["url"])
        st.write(f"**제목:** {info['title']}")
        st.write(f"**채널:** {info['uploader']}")
        
        # 다운로드된 오디오 플레이어
        st.markdown("**🎧 추출된 오디오 재생:**")
        if os.path.exists(st.session_state.audio_path):
            with open(st.session_state.audio_path, "rb") as f:
                st.audio(f.read())

    with content_col:
        st.subheader("📝 변환된 트랜스크립트 (스크립트)")

        if st.session_state.result_text:
            # 텍스트 영역
            st.text_area(
                "전체 텍스트",
                value=st.session_state.result_text,
                height=380,
                label_visibility="collapsed",
            )

            # 다운로드 버튼
            file_title = "".join(c for c in info["title"] if c.isalnum() or c in (" ", "_", "-")).rstrip()
            txt_filename = f"{file_title}_transcript.txt"
            
            dl_col1, dl_col2 = st.columns(2)
            with dl_col1:
                st.download_button(
                    label="💾 텍스트 파일(.txt) 다운로드",
                    data=st.session_state.result_text.encode("utf-8"),
                    file_name=txt_filename,
                    mime="text/plain",
                    use_container_width=True,
                )
            
            with dl_col2:
                # 빠른 3줄 요약 요청 기능
                if st.button("⚡ AI 3줄 핵심 요약", use_container_width=True):
                    with st.spinner("요약 생성 중..."):
                        try:
                            client = get_client(api_key_input.strip())
                            summary_res = client.models.generate_content(
                                model="gemini-3.6-flash",
                                contents=f"다음 유튜브 영상 트랜스크립트 내용을 핵심만 3줄로 불렛포인트(-) 요약해줘:\n\n{st.session_state.result_text}",
                            )
                            st.info(f"**📌 핵심 3줄 요약:**\n\n{summary_res.text}")
                        except Exception as e:
                            st.error(f"요약 실패: {e}")
        else:
            st.info("변환된 텍스트가 여기에 표시됩니다.")
