import os
import re
from typing import Dict, Any, Tuple, Optional
import yt_dlp


def extract_video_id(url: str) -> Optional[str]:
    """유튜브 URL에서 11자리 비디오 ID를 추출합니다."""
    patterns = [
        r"(?:v=|\/)([0-9A-Za-z_-]{11}).*",
        r"(?:embed\/|shorts\/|youtu.be\/)([0-9A-Za-z_-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def get_video_info(url: str) -> Dict[str, Any]:
    """유튜브 영상 메타데이터를 조회합니다."""
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        video_id = info.get("id") or extract_video_id(url)
        return {
            "id": video_id,
            "title": info.get("title", "제목 없음"),
            "thumbnail": info.get("thumbnail"),
            "duration": int(info.get("duration", 0)),
            "uploader": info.get("uploader", "알 수 없는 채널"),
            "view_count": info.get("view_count", 0),
            "url": f"https://www.youtube.com/watch?v={video_id}",
        }


def download_audio(url: str, output_dir: str = "downloads") -> Tuple[str, Dict[str, Any]]:
    """
    유튜브 URL에서 원본 고음질 오디오 스트림(m4a/aac)을 다운로드합니다.
    FFmpeg 없이도 고속 다운로드됩니다.
    """
    os.makedirs(output_dir, exist_ok=True)
    info = get_video_info(url)
    video_id = info["id"]
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

    downloaded = [
        os.path.join(output_dir, f)
        for f in os.listdir(output_dir)
        if f.startswith(video_id)
    ]
    if not downloaded:
        raise FileNotFoundError("오디오 다운로드에 실패했습니다.")

    audio_path = max(downloaded, key=os.path.getmtime)
    return audio_path, info
