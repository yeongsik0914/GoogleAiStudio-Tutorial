import os
import json
from datetime import datetime
from typing import Dict, Any, List, Optional

CACHE_DIR = os.path.join(os.path.dirname(__file__), "video_cache")
os.makedirs(CACHE_DIR, exist_ok=True)


def _get_cache_path(video_id: str) -> str:
    return os.path.join(CACHE_DIR, f"{video_id}.json")


def save_to_cache(
    video_id: str,
    video_info: Dict[str, Any],
    audio_path: str,
    transcript_data: Dict[str, Any],
    chapters_data: List[Dict[str, Any]],
    url: str,
) -> bool:
    """분석 완료된 영상 메타데이터, 오디오 경로, 대본 및 챕터 데이터를 로컬 JSON 캐시에 영구 보관합니다."""
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        # 상대 경로로 안전하게 보관하여 환경 이동 시에도 유지
        rel_audio_path = os.path.relpath(audio_path, os.path.dirname(__file__)) if os.path.isabs(audio_path) else audio_path
        
        data = {
            "video_id": video_id,
            "url": url,
            "video_info": video_info,
            "audio_path": rel_audio_path,
            "transcript_data": transcript_data,
            "chapters_data": chapters_data,
            "cached_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
        with open(_get_cache_path(video_id), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"[Cache Error] Failed to save cache for {video_id}: {e}")
        return False


def load_from_cache(video_id: str) -> Optional[Dict[str, Any]]:
    """
    캐시된 영상 데이터를 로드합니다.
    오디오 파일이 임시 삭제되었더라도 JSON 캐시에 저장된 대본과 챕터 데이터를
    온전히 복원하여 추가 토큰 소모(Gemini API 재호출)를 100% 방지합니다.
    """
    cache_path = _get_cache_path(video_id)
    if not os.path.exists(cache_path):
        return None
    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 필수 대본 데이터 검증
        if not data.get("transcript_data"):
            return None
        
        # 오디오 파일 절대 경로 복원 및 존재 여부 확인
        stored_audio = data.get("audio_path", "")
        abs_audio = ""
        if stored_audio:
            if not os.path.isabs(stored_audio):
                candidate = os.path.join(os.path.dirname(__file__), stored_audio)
            else:
                candidate = stored_audio

            if os.path.exists(candidate):
                abs_audio = candidate
            else:
                # downloads 폴더에서 동일 video_id 파일 탐색
                downloads_dir = os.path.join(os.path.dirname(__file__), "downloads")
                if os.path.exists(downloads_dir):
                    for f in os.listdir(downloads_dir):
                        if f.startswith(video_id):
                            matched = os.path.join(downloads_dir, f)
                            if os.path.exists(matched):
                                abs_audio = matched
                                break
                                
        data["audio_path"] = abs_audio
        return data
    except Exception as e:
        print(f"[Cache Error] Failed to load cache for {video_id}: {e}")
        return None



def has_cache(video_id: str) -> bool:
    """해당 영상이 캐시에 유효하게 보관되어 있는지 확인합니다."""
    return load_from_cache(video_id) is not None


def get_all_cached_videos() -> List[Dict[str, Any]]:
    """보관함에 저장된 모든 영상 목록을 최신순으로 정렬하여 반환합니다."""
    results = []
    if not os.path.exists(CACHE_DIR):
        return results

    for fname in os.listdir(CACHE_DIR):
        if not fname.endswith(".json"):
            continue
        v_id = fname[:-5]
        cache_data = load_from_cache(v_id)
        if not cache_data:
            continue

        info = cache_data.get("video_info", {})
        dur = info.get("duration", 0)
        dur_str = f"{dur // 60}:{dur % 60:02d}"

        results.append({
            "video_id": v_id,
            "title": info.get("title", "제목 없음"),
            "uploader": info.get("uploader", "채널명 없음"),
            "thumbnail": info.get("thumbnail") or f"https://img.youtube.com/vi/{v_id}/hqdefault.jpg",
            "duration_str": dur_str,
            "url": cache_data.get("url", f"https://www.youtube.com/watch?v={v_id}"),
            "cached_at": cache_data.get("cached_at", ""),
            "segment_count": len(cache_data.get("transcript_data", {}).get("segments", [])),
        })

    # 최신 등록순 정렬
    results.sort(key=lambda x: x.get("cached_at", ""), reverse=True)
    return results


def delete_from_cache(video_id: str) -> bool:
    """개별 영상 캐시를 삭제합니다."""
    cache_path = _get_cache_path(video_id)
    if os.path.exists(cache_path):
        try:
            os.remove(cache_path)
            return True
        except Exception:
            return False
    return False


def clear_all_cache() -> int:
    """모든 영상 캐시를 일괄 삭제합니다."""
    count = 0
    if os.path.exists(CACHE_DIR):
        for fname in os.listdir(CACHE_DIR):
            if fname.endswith(".json"):
                try:
                    os.remove(os.path.join(CACHE_DIR, fname))
                    count += 1
                except Exception:
                    pass
    return count
