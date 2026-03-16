from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any

from app.integrations.openai.recommendation import recommendation_chat_completion

# recommendation_type 별칭을 내부 표준 타입으로 맞추기 위한 매핑
# - general/lifestyle 계열 -> general_care
# - warning/caution/medication 계열 -> medication_caution
# - followup/visit 계열 -> follow_up
TYPE_ALIASES = {
    "general": "general_care",
    "general_care": "general_care",
    "lifestyle": "general_care",
    "daily_care": "general_care",
    "medication": "medication_caution",
    "medication_caution": "medication_caution",
    "drug_caution": "medication_caution",
    "drug": "medication_caution",
    "warning": "medication_caution",
    "caution": "medication_caution",
    "followup": "follow_up",
    "follow_up": "follow_up",
    "follow-up": "follow_up",
    "visit": "follow_up",
    "hospital_visit": "follow_up",
    "monitoring": "follow_up",
}

# source 우선순위
# 숫자가 클수록 "같은 의미면 더 우선적으로 남길 후보"
SOURCE_PRIORITY = {
    "direct_guideline": 4,  # DiseaseGuideline 직접 매칭
    "medication_rule": 3,  # 약물명 기반 룰 생성
    "vector_fallback": 2,  # vector search fallback
    "scan.medical_record.clinical_note": 2,
    "scan.medical_record.diagnosis": 2,
    "scan.diagnosis": 1,
    "scan.medical_record": 1,
    "scan": 1,
    "llm_refined": 1,  # LLM 후처리 결과
}

# 타입별 최대 노출 개수
TYPE_LIMITS = {
    "general_care": 3,
    "medication_caution": 2,
    "follow_up": 2,
}

# 안전하지 않은 표현 필터
# recommendation은 건강관리 안내 수준이어야 하므로
# 확정 진단/복용 변경/강한 치료 지시 문구는 걸러낸다.
FORBIDDEN_PHRASES = [
    "복용을 중단",
    "약을 중단",
    "용량을 늘리",
    "용량을 줄이",
    "복용량을 바꾸",
    "확진",
    "진단됩니다",
    "반드시 치료",
    "치료해야 합니다",
]


@dataclass
class RecommendationCandidate:
    """
    추천 생성 중간 단계에서 사용하는 후보 데이터 구조.

    Attributes:
        type:
            내부 표준 recommendation type 또는 원본 type
        content:
            사용자에게 보여줄 추천 문구
        source:
            후보가 생성된 출처
        score:
            후보 점수(우선순위 비교 시 사용)
        disease_id:
            매칭된 질환 ID
        guideline_id:
            매칭된 guideline ID
        drug_name:
            관련 약물명
        metadata:
            기타 디버깅/추적용 메타데이터
    """

    type: str
    content: str
    source: str
    score: float = 0.0
    disease_id: int | None = None
    guideline_id: int | None = None
    drug_name: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


def normalize_recommendation_type(value: str | None) -> str:
    """
    recommendation_type 값을 내부 표준 타입으로 정규화한다.

    Args:
        value:
            원본 추천 타입 문자열

    Returns:
        str:
            general_care / medication_caution / follow_up 중 하나 또는 기본값
    """
    if not value:
        return "general_care"

    key = value.strip().lower()
    return TYPE_ALIASES.get(key, "general_care")


def normalize_text(text: str) -> str:
    """
    dedup 비교를 위한 텍스트 정규화 함수.

    처리 내용:
    - 양끝 공백 제거
    - 소문자화
    - 연속 공백 축소
    - 기본 문장부호 제거
    - 자주 나오는 표현 차이 일부 통일

    Args:
        text:
            원본 추천 문구

    Returns:
        str:
            비교용 정규화 문자열
    """
    normalized = text.strip().lower()
    normalized = re.sub(r"\s+", " ", normalized)
    normalized = re.sub(r"[!?,.;:]+", "", normalized)

    replacements = {
        "드시기 바랍니다": "드세요",
        "섭취하시기 바랍니다": "섭취하세요",
        "권장됩니다": "권장",
        "주의하시기 바랍니다": "주의하세요",
        "충분한 수분 섭취": "수분 섭취",
        "의료진과 상의하세요": "의료진과 상담하세요",
        "전문의와 상의하세요": "의료진과 상담하세요",
    }

    for old, new in replacements.items():
        normalized = normalized.replace(old, new)

    return normalized


def similarity(a: str, b: str) -> float:
    """
    두 문장의 문자열 유사도를 계산한다.

    Args:
        a:
            비교 문장 1
        b:
            비교 문장 2

    Returns:
        float:
            0~1 사이 유사도 점수
    """
    return SequenceMatcher(None, normalize_text(a), normalize_text(b)).ratio()


def candidate_priority(candidate: RecommendationCandidate) -> tuple[int, float]:
    """
    후보 우선순위를 비교하기 위한 값 생성.

    1차 비교: source priority
    2차 비교: score

    Args:
        candidate:
            추천 후보

    Returns:
        tuple[int, float]:
            정렬/비교용 우선순위 값
    """
    return (
        SOURCE_PRIORITY.get(candidate.source, 0),
        candidate.score,
    )


def normalize_candidates(
    candidates: list[RecommendationCandidate],
) -> list[RecommendationCandidate]:
    """
    후보 리스트를 정규화한다.

    처리 내용:
    - 빈 content 제거
    - type 정규화

    Args:
        candidates:
            원본 후보 목록

    Returns:
        list[RecommendationCandidate]:
            정규화된 후보 목록
    """
    normalized: list[RecommendationCandidate] = []

    for candidate in candidates:
        content = candidate.content.strip()
        if not content:
            continue

        normalized.append(
            RecommendationCandidate(
                type=normalize_recommendation_type(candidate.type),
                content=content,
                source=candidate.source,
                score=candidate.score,
                disease_id=candidate.disease_id,
                guideline_id=candidate.guideline_id,
                drug_name=candidate.drug_name,
                metadata=candidate.metadata,
            )
        )

    return normalized


def dedup_exact(
    candidates: list[RecommendationCandidate],
) -> list[RecommendationCandidate]:
    """
    같은 type + 같은 normalized text를 exact duplicate로 보고 제거한다.

    같은 key가 여러 개면 source priority와 score가 더 높은 후보를 남긴다.

    Args:
        candidates:
            후보 목록

    Returns:
        list[RecommendationCandidate]:
            exact dedup 후 후보 목록
    """
    best_by_key: dict[tuple[str, str], RecommendationCandidate] = {}

    for candidate in candidates:
        key = (candidate.type, normalize_text(candidate.content))
        existing = best_by_key.get(key)

        if existing is None:
            best_by_key[key] = candidate
            continue

        if candidate_priority(candidate) > candidate_priority(existing):
            best_by_key[key] = candidate

    return list(best_by_key.values())


def dedup_near(
    candidates: list[RecommendationCandidate],
    threshold: float = 0.82,
) -> list[RecommendationCandidate]:
    """
    type이 같고 문장 유사도가 threshold 이상이면 near duplicate로 보고 제거한다.

    우선순위가 높은 후보부터 남기므로,
    direct guideline이 vector fallback보다 남을 가능성이 높다.

    Args:
        candidates:
            후보 목록
        threshold:
            유사 문장으로 판단할 기준값

    Returns:
        list[RecommendationCandidate]:
            near dedup 후 후보 목록
    """
    sorted_candidates = sorted(
        candidates,
        key=candidate_priority,
        reverse=True,
    )

    result: list[RecommendationCandidate] = []

    for candidate in sorted_candidates:
        duplicate_found = False

        for kept in result:
            if candidate.type != kept.type:
                continue

            if similarity(candidate.content, kept.content) >= threshold:
                duplicate_found = True
                break

        if not duplicate_found:
            result.append(candidate)

    return result


def limit_per_type(
    candidates: list[RecommendationCandidate],
) -> list[RecommendationCandidate]:
    """
    recommendation type별 최대 개수를 제한한다.

    예:
    - general_care 최대 3개
    - medication_caution 최대 2개
    - follow_up 최대 2개

    Args:
        candidates:
            후보 목록

    Returns:
        list[RecommendationCandidate]:
            개수 제한 적용 후 후보 목록
    """
    grouped: dict[str, list[RecommendationCandidate]] = {}

    for candidate in sorted(candidates, key=candidate_priority, reverse=True):
        grouped.setdefault(candidate.type, []).append(candidate)

    result: list[RecommendationCandidate] = []

    # 주요 type 먼저 순서 보장
    for rec_type in ("general_care", "medication_caution", "follow_up"):
        items = grouped.get(rec_type, [])
        if not items:
            continue

        limit = TYPE_LIMITS.get(rec_type, 2)
        result.extend(items[:limit])

    # 혹시 새 type이 생겨도 기본 limit으로 보존
    for rec_type, items in grouped.items():
        if rec_type in {"general_care", "medication_caution", "follow_up"}:
            continue

        limit = TYPE_LIMITS.get(rec_type, 2)
        result.extend(items[:limit])

    return result


def validate_recommendation_content(text: str) -> bool:
    """
    추천 문구가 안전한 표현인지 검사한다.

    Args:
        text:
            추천 문구

    Returns:
        bool:
            허용 가능하면 True
    """
    normalized = normalize_text(text)
    return not any(phrase in normalized for phrase in FORBIDDEN_PHRASES)


def filter_safe_recommendations(
    candidates: list[RecommendationCandidate],
) -> list[RecommendationCandidate]:
    """
    금지 표현이 포함된 추천 후보를 제거한다.

    Args:
        candidates:
            후보 목록

    Returns:
        list[RecommendationCandidate]:
            안전 필터 통과 후보 목록
    """
    return [candidate for candidate in candidates if validate_recommendation_content(candidate.content)]


def dedup_recommendations(
    candidates: list[RecommendationCandidate],
) -> list[RecommendationCandidate]:
    """
    규칙 기반 정제 파이프라인.

    순서:
    1. type/content 정규화
    2. exact duplicate 제거
    3. near duplicate 제거
    4. type별 개수 제한
    5. 안전 필터

    Args:
        candidates:
            원본 후보 목록

    Returns:
        list[RecommendationCandidate]:
            정제된 후보 목록
    """
    step1 = normalize_candidates(candidates)
    step2 = dedup_exact(step1)
    step3 = dedup_near(step2)
    step4 = limit_per_type(step3)
    step5 = filter_safe_recommendations(step4)
    return step5


def should_run_llm_refinement(
    candidates: list[RecommendationCandidate],
) -> bool:
    """
    LLM 후처리가 필요한지 판단한다.

    현재 기준:
    - 후보가 4개 이상이면 실행
    - exact normalized text 중복이 있으면 실행

    Args:
        candidates:
            정제 후 후보 목록

    Returns:
        bool:
            LLM refinement 필요 여부
    """
    if len(candidates) >= 4:
        return True

    normalized_texts = [normalize_text(c.content) for c in candidates]
    return len(normalized_texts) != len(set(normalized_texts))


# recommendation 후보 정리 전용 시스템 프롬프트
SYSTEM_PROMPT = """
당신은 건강관리 안내 문구를 정리하는 보조 시스템입니다.

역할:
- 입력된 추천 후보 문구를 중복 없이 정리합니다.
- 의미가 유사한 문구는 1개로 통합합니다.
- 생활관리/복약 주의 수준에서만 자연스럽게 표현합니다.
- 의학적 진단, 처방 변경, 확정적 치료 지시는 금지합니다.

반드시 지킬 규칙:
- 새로운 의학적 사실을 추가하지 마세요.
- 입력 문구에 없는 내용을 추론하여 추가하지 마세요.
- '진단', '확진', '약을 중단하세요', '복용량을 바꾸세요' 같은 표현을 쓰지 마세요.
- 필요 시 '증상이 지속되거나 악화되면 의료진과 상담하세요' 수준으로만 마무리하세요.
- 결과는 JSON 배열로만 반환하세요.
"""


def build_llm_user_prompt(
    candidates: list[RecommendationCandidate],
) -> str:
    """
    recommendation refinement용 사용자 프롬프트를 생성한다.

    Args:
        candidates:
            정제 대상 후보 목록

    Returns:
        str:
            LLM 입력용 프롬프트
    """
    lines: list[str] = []

    for idx, candidate in enumerate(candidates, start=1):
        lines.append(f'{idx}. type="{candidate.type}", source="{candidate.source}", content="{candidate.content}"')

    joined = "\n".join(lines)

    return f"""
다음 추천 후보들을 중복 없이 3~5개로 정리하세요.

후보:
{joined}

출력 형식:
[
  {{
    "type": "general_care",
    "content": "..."
  }}
]

설명 없이 JSON 배열만 반환하세요.
"""


async def refine_recommendations_with_llm(
    candidates: list[RecommendationCandidate],
) -> list[RecommendationCandidate]:
    """
    recommendation 후보를 LLM으로 후처리한다.

    처리 내용:
    - 중복 의미 문구 통합
    - 표현 정리
    - 결과 JSON 파싱
    - 실패 시 원본 후보 그대로 반환

    Args:
        candidates:
            규칙 기반 정제 후 후보 목록

    Returns:
        list[RecommendationCandidate]:
            LLM 후처리 결과 또는 fallback 후보 목록
    """
    if not candidates:
        return []

    try:
        response_text = await recommendation_chat_completion(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=build_llm_user_prompt(candidates),
        )
    except Exception:
        return candidates

    try:
        items = json.loads(response_text)
    except Exception:
        return candidates

    if not isinstance(items, list):
        return candidates

    refined: list[RecommendationCandidate] = []

    for item in items:
        if not isinstance(item, dict):
            continue

        rec_type = normalize_recommendation_type(item.get("type"))
        content = str(item.get("content", "")).strip()

        if not content:
            continue

        refined.append(
            RecommendationCandidate(
                type=rec_type,
                content=content,
                source="llm_refined",
            )
        )

    if not refined:
        return candidates

    return dedup_recommendations(refined)


async def finalize_recommendations(
    candidates: list[RecommendationCandidate],
    enable_llm_refinement: bool = False,
) -> list[RecommendationCandidate]:
    """
    recommendation 후보를 최종 정제한다.

    처리 순서:
    1. rule-based dedup
    2. 옵션에 따라 LLM refinement
    3. LLM 결과에도 다시 dedup 적용

    Args:
        candidates:
            원본 후보 목록
        enable_llm_refinement:
            LLM 후처리 사용 여부

    Returns:
        list[RecommendationCandidate]:
            최종 추천 후보 목록
    """
    deduped = dedup_recommendations(candidates)

    if not enable_llm_refinement:
        return deduped

    if not should_run_llm_refinement(deduped):
        return deduped

    refined = await refine_recommendations_with_llm(deduped)

    return dedup_recommendations(refined)
