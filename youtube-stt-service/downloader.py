import os
import re
from typing import Dict, Any, Tuple
import yt_dlp


def sanitize_filename(filename: str) -> str:
    """파일명에서 윈도우/리눅스 특수문자를 제거합니다."""
    return re.sub(r'[\\/*?:"<>|]', "", filename)


def get_video_info(url: str) -> Dict[str, Any]:
    """
    유튜브 URL에서 영상 메타데이터(제목, 썸네일, 재생시간, 채널명)를 추출합니다.
    다운로드는 수행하지 않습니다.
    """
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return {
            "id": info.get("id"),
            "title": info.get("title", "제목 없음"),
            "thumbnail": info.get("thumbnail"),
            "duration": info.get("duration", 0),
            "uploader": info.get("uploader", "알 수 없음"),
            "url": url,
        }


def download_audio(url: str, output_dir: str = "downloads") -> Tuple[str, Dict[str, Any]]:
    """
    유튜브 URL에서 고음질 오디오 스트림(m4a/webm/mp3)을 다운로드합니다.
    ffmpeg 없이도 유튜브 원본 고음질 m4a 오디오 스트림을 직접 저장합니다.

    Returns:
        (saved_audio_filepath, video_info_dict)
    """
    os.makedirs(output_dir, exist_ok=True)

    # 1. 정보 추출
    info = get_video_info(url)
    video_id = info["id"]
    
    # 2. 다운로드 옵션 설정 (ffmpeg 없이 m4a/bestaudio 직접 저장)
    outtmpl = os.path.join(output_dir, f"{video_id}.%(ext)s")
    
    ydl_opts = {
        "format": "m4a/bestaudio/best",
        "outtmpl": outtmpl,
        "quiet": True,
        "no_warnings": True,
        "overwrites": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    # 3. 실제 저장된 파일 경로 찾기
    downloaded_files = [
        os.path.join(output_dir, f)
        for f in os.listdir(output_dir)
        if f.startswith(video_id)
    ]

    if not downloaded_files:
        raise FileNotFoundError("오디오 다운로드에 실패했거나 파일을 찾을 수 없습니다.")

    # 가장 최근에 수정된 파일 선택
    audio_path = max(downloaded_files, key=os.path.getmtime)
    return audio_path, info
