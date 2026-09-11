import os
import json
import re
from typing import List, Dict, Any, Tuple
from dotenv import load_dotenv
from google import genai

load_dotenv()


def search_content_timestamps(
    query: str,
    segments: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    사용자가 입력한 검색어(특정 내용)가 포함된 타임스탬프 세그먼트를 찾습니다.
    대소문자 무시 및 형태소 유사 매칭을 수행합니다.
    """
    if not query.strip() or not segments:
        return []

    q = query.strip().lower()
    keywords = [w for w in re.split(r"\s+", q) if len(w) > 0]
    matched_results = []

    for seg in segments:
        text_lower = seg["text"].lower()
        score = 0

        # 정확한 일치
        if q in text_lower:
            score += 10

        # 개별 키워드 매칭
        for kw in keywords:
            if kw in text_lower:
                score += 2

        if score > 0:
            matched_results.append({
                "start": seg["start"],
                "end": seg["end"],
                "time_str": seg["time_str"],
                "text": seg["text"],
                "speaker": seg.get("speaker", "화자"),
                "score": score,
            })

    # 연관성 점수 높은 순 정렬
    matched_results.sort(key=lambda x: x["score"], reverse=True)
    return matched_results


def answer_question_with_timestamps(
    question: str,
    segments: List[Dict[str, Any]],
    full_text: str,
    api_key: str = None,
) -> Dict[str, Any]:
    """
    Gemini 3.8 Flash 모델(gemini-3.8-flash)을 사용하여 영상 대본 기반 질의응답을 수행하고,
    답변과 관련된 영상 속 타임스탬프(초)를 함께 반환합니다.
    """
    key = api_key or os.environ.get("GEMINI_API_KEY")
    if not key:
        raise ValueError("GEMINI_API_KEY가 설정되지 않았습니다.")

    client = genai.Client(api_key=key)

    # 시간대가 태깅된 대본 텍스트 제작
    timeline_script = "\n".join([
        f"[{seg['time_str']}] {seg['text']}"
        for seg in segments[:100]  # 최대 100개 세그먼트
    ])

    system_prompt = f"""당신은 유튜브 영상 분석 전문가 AI입니다.
제공된 시간대별 영상 트랜스크립트를 꼼꼼히 확인하고 사용자의 질문에 정확하고 명쾌하게 답변해주세요.

[규칙]
1. 답변은 읽기 쉽고 친절한 어조로 작성하세요.
2. 답변과 가장 밀접하게 관련된 영상의 시작 시간(예: "01:23" 또는 초 단위)을 찾아 JSON 형식으로 함께 제공해주세요.

[시간대별 트랜스크립트]
{timeline_script}

[사용자 질문]
{question}

[응답 포맷 (반드시 아래 JSON 형식으로만 응답할 것)]:
```json
{{
  "answer": "질문에 대한 상세한 설명과 답변...",
  "relevant_timestamp": "00:02",
  "relevant_seconds": 2.0
}}
```"""

    response = client.models.generate_content(
        model="gemini-3.5-flash",
        contents=system_prompt,
    )

    raw_text = response.text or ""
    
    # JSON 파싱
    try:
        json_match = re.search(r"```json\s*(\{.*?\})\s*```", raw_text, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group(1))
            return {
                "answer": data.get("answer", raw_text),
                "relevant_timestamp": data.get("relevant_timestamp", "00:00"),
                "relevant_seconds": float(data.get("relevant_seconds", 0.0)),
            }
        else:
            # 중괄호 직접 파싱 시도
            brace_match = re.search(r"(\{.*\})", raw_text, re.DOTALL)
            if brace_match:
                data = json.loads(brace_match.group(1))
                return {
                    "answer": data.get("answer", raw_text),
                    "relevant_timestamp": data.get("relevant_timestamp", "00:00"),
                    "relevant_seconds": float(data.get("relevant_seconds", 0.0)),
                }
    except Exception:
        pass

    # JSON 파싱 실패 시 일반 텍스트로 처리
    return {
        "answer": raw_text,
        "relevant_timestamp": "00:00",
        "relevant_seconds": 0.0,
    }


def extract_video_chapters(
    segments: List[Dict[str, Any]],
    full_text: str,
    api_key: str = None,
) -> List[Dict[str, Any]]:
    """
    Gemini 3.8 Flash를 활용하여 전체 대본을 주제별 주요 카테고리/챕터(시작시간, 제목, 핵심요약)로 자동 분할합니다.
    """
    key = api_key or os.environ.get("GEMINI_API_KEY")
    if not key:
        return []

    client = genai.Client(api_key=key)

    timeline_script = "\n".join([
        f"[{seg['time_str']}] {seg['text']}"
        for seg in segments[:120]
    ])

    prompt = f"""당신은 영상 콘텐츠 분석가입니다.
아래 제공된 시간대별 영상 대본을 읽고, 영상의 흐름을 3~6개의 주요 주제(카테고리/챕터)로 나누어 정리해주세요.

[대본]
{timeline_script}

[응답 규칙]
- 반드시 아래 JSON 배열 형식으로만 응답하세요. 다른 설명은 붙이지 마세요.
- start_seconds: 해당 챕터의 시작 시간 (초 단위 숫자)
- time_str: "MM:SS" 형식
- title: 해당 챕터의 핵심 주제명 (15자 이내)
- summary: 해당 챕터의 1~2줄 핵심 내용 요약

```json
[
  {{
    "start_seconds": 0.0,
    "time_str": "00:00",
    "title": "오프닝 및 주제 소개",
    "summary": "영상의 주제와 오늘 다룰 주요 내용을 소개합니다."
  }}
]
```"""

    try:
        response = client.models.generate_content(
            model="gemini-3.5-flash",
            contents=prompt,
        )
        raw = response.text or ""
        json_match = re.search(r"```json\s*(\[.*?\])\s*```", raw, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(1))
        bracket_match = re.search(r"(\[.*\])", raw, re.DOTALL)
        if bracket_match:
            return json.loads(bracket_match.group(1))
    except Exception as e:
        print(f"챕터 생성 실패: {e}")

    # 실패 시 기본 세그먼트 기반 fallback
    if segments:
        return [
            {
                "start_seconds": segments[0]["start"],
                "time_str": segments[0]["time_str"],
                "title": "전체 영상",
                "summary": segments[0]["text"][:60] + "...",
            }
        ]
    return []

