"""
UI 및 정적 자산(CSS) 로더 모듈
AGENTS.md 표준 규격에 따라 프론트엔드 스타일시트를 안전하게 로드합니다.
"""

from functools import lru_cache
from pathlib import Path

# static 디렉터리 경로 설정
STATIC_DIR = Path(__file__).resolve().parent / "static"


@lru_cache(maxsize=16)
def load_css(filename: str = "style.css") -> str:
    """
    static/css/ 경로에서 CSS 파일을 UTF-8로 읽어옵니다.
    lru_cache를 적용하여 디스크 I/O를 최소화합니다.
    """
    file_path = STATIC_DIR / "css" / filename
    if not file_path.exists():
        raise FileNotFoundError(f"CSS 파일을 찾을 수 없습니다: {file_path}")
    return file_path.read_text(encoding="utf-8")
