from __future__ import annotations

from app.services.recommendation_refiner import (
    RecommendationCandidate,
    dedup_recommendations,
    finalize_recommendations,
    normalize_recommendation_type,
)


def test_normalize_recommendation_type_aliases() -> None:
    assert normalize_recommendation_type("general") == "general_care"
    assert normalize_recommendation_type("lifestyle") == "general_care"
    assert normalize_recommendation_type("warning") == "medication_caution"
    assert normalize_recommendation_type("followup") == "follow_up"
    assert normalize_recommendation_type(None) == "general_care"


def test_dedup_exact_keeps_higher_priority_source() -> None:
    candidates = [
        RecommendationCandidate(
            type="general",
            content="충분한 수분 섭취를 하세요.",
            source="vector_fallback",
            score=0.7,
        ),
        RecommendationCandidate(
            type="general_care",
            content="충분한 수분 섭취를 하세요.",
            source="direct_guideline",
            score=0.9,
        ),
    ]

    result = dedup_recommendations(candidates)

    assert len(result) == 1
    assert result[0].source == "direct_guideline"
    assert result[0].type == "general_care"


def test_dedup_near_removes_similar_sentence() -> None:
    candidates = [
        RecommendationCandidate(
            type="general_care",
            content="물을 자주 마시고 무리하지 않도록 하세요.",
            source="vector_fallback",
            score=0.72,
        ),
        RecommendationCandidate(
            type="general_care",
            content="물을 자주 마시고 무리하지 않도록 하세요",
            source="direct_guideline",
            score=0.95,
        ),
    ]

    result = dedup_recommendations(candidates)

    assert len(result) == 1
    assert result[0].source == "direct_guideline"


def test_limit_per_type_general_care_max_three() -> None:
    candidates = [
        RecommendationCandidate(
            type="general_care",
            content="물을 충분히 마시세요.",
            source="direct_guideline",
            score=1.0,
        ),
        RecommendationCandidate(
            type="general_care",
            content="염분 섭취를 줄이세요.",
            source="direct_guideline",
            score=0.99,
        ),
        RecommendationCandidate(
            type="general_care",
            content="규칙적으로 가벼운 운동을 하세요.",
            source="direct_guideline",
            score=0.98,
        ),
        RecommendationCandidate(
            type="general_care",
            content="수면 시간을 일정하게 유지하세요.",
            source="direct_guideline",
            score=0.97,
        ),
        RecommendationCandidate(
            type="general_care",
            content="카페인 섭취를 줄여보세요.",
            source="direct_guideline",
            score=0.96,
        ),
    ]

    result = dedup_recommendations(candidates)

    assert len(result) == 3
    assert all(item.type == "general_care" for item in result)


def test_forbidden_phrase_filtered() -> None:
    candidates = [
        RecommendationCandidate(
            type="medication_caution",
            content="약을 중단하고 상태를 보세요.",
            source="medication_rule",
            score=1.0,
        ),
        RecommendationCandidate(
            type="medication_caution",
            content="복용 중 불편한 증상이 있으면 의료진과 상담하세요.",
            source="medication_rule",
            score=0.9,
        ),
    ]

    result = dedup_recommendations(candidates)

    assert len(result) == 1
    assert "의료진과 상담" in result[0].content


async def test_finalize_recommendations_without_llm() -> None:
    candidates = [
        RecommendationCandidate(
            type="general",
            content="충분한 수분 섭취를 하세요.",
            source="vector_fallback",
            score=0.7,
        ),
        RecommendationCandidate(
            type="general_care",
            content="충분한 수분 섭취를 하세요.",
            source="direct_guideline",
            score=0.95,
        ),
    ]

    result = await finalize_recommendations(
        candidates,
        enable_llm_refinement=False,
    )

    assert len(result) == 1
    assert result[0].source == "direct_guideline"
