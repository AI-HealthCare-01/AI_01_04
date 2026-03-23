from __future__ import annotations

import logging
import re
from typing import Any, cast

from fastapi import HTTPException
from starlette import status

from app.core import config
from app.dtos.recommendations import RecommendationType, RecommendationUpdateRequest
from app.integrations.openai.client import chat_completion
from app.repositories.disease_repository import DiseaseRepository
from app.repositories.drug_repository import DrugRepository
from app.repositories.recommendation_repository import RecommendationRepository
from app.repositories.scan_repository import ScanRepository
from app.repositories.vector_document_repository import VectorDocumentRepository
from app.services.embedding import encode
from app.services.recommendation_refiner import (
    RecommendationCandidate,
    finalize_recommendations,
)

logger = logging.getLogger(__name__)


def _normalize_rec_type(raw: Any) -> RecommendationType:
    """
    DB에 저장된 recommendation_type 값을 API 응답용 표준 타입으로 변환한다.

    예:
    - general_care -> lifestyle
    - medication_caution -> warning
    - follow_up -> followup
    """
    s = str(raw or "").strip().lower()

    exact_map = {
        "lifestyle": "lifestyle",
        "general_care": "lifestyle",
        "daily_care": "lifestyle",
        "self_care": "lifestyle",
        "general": "lifestyle",
        "medication": "medication",
        "medication_caution": "warning",
        "drug_caution": "warning",
        "warning": "warning",
        "caution": "warning",
        "followup": "followup",
        "follow_up": "followup",
        "follow-up": "followup",
        "monitoring": "followup",
        "visit": "followup",
        "hospital_visit": "followup",
    }

    if s in exact_map:
        return cast(RecommendationType, exact_map[s])

    if "medication" in s and "caution" in s:
        return "warning"
    if "drug" in s and "caution" in s:
        return "warning"
    if "warn" in s or "caution" in s:
        return "warning"
    if "follow" in s or "monitor" in s or "visit" in s:
        return "followup"
    if "drug" in s or "medicine" in s or "medication" in s:
        return "medication"
    return "lifestyle"


def _rec_to_response_dict(rec: Any) -> dict[str, Any]:
    """
    Recommendation ORM 객체를 API 응답용 dict로 변환한다.
    """
    return {
        "id": rec.id,
        "recommendation_type": _normalize_rec_type(getattr(rec, "recommendation_type", None)),
        "content": rec.content,
        "frequency": getattr(rec, "frequency", None),
        "score": getattr(rec, "score", None),
        "is_selected": bool(getattr(rec, "is_selected", False)),
        "rank": getattr(rec, "rank", None),
    }


class RecommendationService:
    """
    scan 기반 recommendation 생성/조회/저장/피드백 서비스.

    현재 구조:
    1. scan 데이터에서 추천 후보를 수집
    2. 후보를 rule-based dedup 및 optional LLM refinement로 정제
    3. 최종 후보만 Recommendation 레코드로 저장
    """

    def __init__(self) -> None:
        self.recommendation_repo = RecommendationRepository()
        self.scan_repo = ScanRepository()
        self.vector_doc_repo = VectorDocumentRepository()
        self.disease_repo = DiseaseRepository()
        self.drug_repo = DrugRepository()

    def _normalize_document_type(self, raw: Any) -> str:
        """
        document_type 값을 내부 사용값으로 정규화한다.
        """
        value = str(raw or "prescription").strip().lower()
        if value in {"prescription", "medical_record"}:
            return value
        return "prescription"

    def _looks_like_disease_code(self, value: str | None) -> bool:
        """
        문자열이 질병분류코드(KCD/ICD) 형식인지 대략 판별한다.

        예:
        - B15
        - I10
        - E119
        - M545
        """
        if not value:
            return False

        text = value.strip().upper()
        return bool(re.fullmatch(r"[A-Z]\d{2,4}", text))

    def _normalize_diagnosis_text(self, diagnosis: str | None) -> str | None:
        """
        OCR/AI 결과의 diagnosis 문자열을 질환 매칭용으로 정리한다.

        처리 예:
        - '고혈압 의증' -> '고혈압'
        - '편두통?' -> '편두통'
        - '당뇨 의심' -> '당뇨'

        Notes:
            현재는 단순 노이즈 제거 수준이며,
            추후 synonym 매핑이나 표준화 사전으로 확장 가능하다.
        """
        if not diagnosis:
            return None

        value = diagnosis.strip()
        if not value:
            return None

        noise_patterns = [
            r"\s*의증\b",
            r"\s*의심\b",
            r"\s*추정\b",
            r"\?",
            r"\s*suspected\b",
        ]

        for pattern in noise_patterns:
            value = re.sub(pattern, "", value, flags=re.IGNORECASE)

        value = re.sub(r"\s+", " ", value).strip()
        return value or None

    def _build_vector_query(
        self,
        *,
        diagnosis: str | None,
        disease_name: str | None,
        drugs: list[str],
        clinical_note: str | None = None,
    ) -> str:
        """
        vector search용 질의 문자열을 생성한다.

        구성 요소:
        - disease_name
        - diagnosis
        - clinical_note
        - 약물명 일부
        """
        parts: list[str] = []

        if disease_name:
            parts.append(disease_name)

        if diagnosis and diagnosis != disease_name:
            parts.append(diagnosis)

        if clinical_note:
            parts.append(clinical_note)

        if drugs:
            parts.extend(drugs[:5])

        return " ".join(part for part in parts if part).strip()

    def _parse_diagnosis_entry(self, entry: str | None) -> tuple[str | None, str | None]:
        """
        diagnosis_list 항목에서 질병코드와 질병명을 분리한다.

        예:
        - 'I109 기타 및 상세불명의 원발성 고혈압' → ('I109', '기타 및 상세불명의 원발성 고혈압')
        - 'E118 합병증을 동반하지 않은 2형 당뇨병' → ('E118', '합병증을 동반하지 않은 2형 당뇨병')
        - '고혈압' → (None, '고혈압')
        - 'I10' → ('I10', None)
        """
        if not entry or not entry.strip():
            return None, None

        text = entry.strip()
        match = re.match(r"^([A-Za-z]\d{2,5})\s+(.*)", text)
        if match:
            return match.group(1).upper(), match.group(2).strip() or None

        if self._looks_like_disease_code(text):
            return text.upper(), None

        return None, text

    async def _match_disease(self, diagnosis: str | None) -> Any | None:
        """
        diagnosis 문자열을 Disease에 매칭한다.

        우선순위:
        1. icd/kcd code 형태면 코드 매칭
        2. 이름 정확 일치
        3. 이름 부분 일치
        """
        value = self._normalize_diagnosis_text(diagnosis)
        if not value:
            return None

        if self._looks_like_disease_code(value):
            disease = await self.disease_repo.get_by_kcd_code(value.upper())
            if disease:
                return disease

        disease = await self.disease_repo.get_by_name(value)
        if disease:
            return disease

        diseases = await self.disease_repo.list_by_name_contains(value, limit=1)
        if diseases:
            return diseases[0]

        return None

    def _create_recommendation_candidate(
        self,
        *,
        recommendation_type: str,
        source: str,
        content: str,
        score: float,
        disease_id: int | None = None,
        guideline_id: int | None = None,
        drug_name: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> RecommendationCandidate:
        """
        중간 단계에서 사용할 recommendation 후보를 생성한다.
        """
        return RecommendationCandidate(
            type=recommendation_type,
            content=content,
            source=source,
            score=score,
            disease_id=disease_id,
            guideline_id=guideline_id,
            drug_name=drug_name,
            metadata=metadata or {},
        )

    async def _create_recommendation(
        self,
        *,
        user_id: int,
        batch_id: int,
        scan_id: int,
        recommendation_type: str,
        source: str,
        content: str,
        score: float,
        rank: int,
        frequency: str | None = None,
        status_value: str = "active",
    ) -> Any | None:
        """
        Recommendation 레코드 1건을 DB에 생성한다.
        """
        return await self.recommendation_repo.create_recommendation(
            user_id=user_id,
            batch_id=batch_id,
            scan_id=scan_id,
            recommendation_type=recommendation_type,
            source=source,
            content=content,
            frequency=frequency,
            score=score,
            rank=rank,
            status=status_value,
        )

    async def _save_candidates(
        self,
        *,
        user_id: int,
        scan_id: int,
        batch_id: int,
        candidates: list[RecommendationCandidate],
        status_value: str = "candidate",
    ) -> list[Any]:
        """
        최종 정제된 recommendation 후보를 DB에 저장한다.
        """
        created: list[Any] = []

        for rank, candidate in enumerate(candidates, start=1):
            rec = await self._create_recommendation(
                user_id=user_id,
                batch_id=batch_id,
                scan_id=scan_id,
                recommendation_type=candidate.type,
                source=candidate.source,
                content=candidate.content,
                score=candidate.score,
                frequency=candidate.frequency,
                rank=rank,
                status_value=status_value,
            )
            if rec:
                created.append(rec)

        return created

    async def _build_guideline_recommendations(
        self,
        *,
        diagnosis: str | None,
    ) -> list[RecommendationCandidate]:
        """
        diagnosis를 Disease에 매칭한 뒤 guideline 기반 후보를 생성한다.

        매칭 우선순위:
        1. 기존 Disease 직접 매칭 (이름/코드)
        2. 질병코드 매핑 테이블을 통한 anchor 코드 → guideline 조회
        """
        candidates: list[RecommendationCandidate] = []
        normalized = self._normalize_diagnosis_text(diagnosis)
        if not normalized:
            return candidates

        # 1) 기존 직접 매칭
        disease = await self._match_disease(normalized)
        if disease:
            guidelines = await self.disease_repo.get_guidelines_by_disease(disease.id)
            if guidelines:
                for gl in guidelines:
                    candidates.append(
                        self._create_recommendation_candidate(
                            recommendation_type=getattr(gl, "category", "general_care"),
                            source="direct_guideline",
                            content=getattr(gl, "content", ""),
                            score=0.95,
                            disease_id=disease.id,
                            guideline_id=getattr(gl, "id", None),
                            metadata={"matched_from": normalized},
                        )
                    )
                return candidates

        # 2) 질병코드 매핑 테이블 fallback
        code, _name = self._parse_diagnosis_entry(diagnosis)
        if code:
            anchor = await self.disease_repo.resolve_anchor_code(code)
            if anchor:
                anchor_code, anchor_name = anchor
                guidelines = await self.disease_repo.get_guidelines_by_anchor_code(anchor_code)
                for gl in guidelines:
                    candidates.append(
                        self._create_recommendation_candidate(
                            recommendation_type=getattr(gl, "category", "general_care"),
                            source="direct_guideline",
                            content=getattr(gl, "content", ""),
                            score=0.93,
                            guideline_id=getattr(gl, "id", None),
                            metadata={
                                "matched_from": normalized,
                                "original_code": code,
                                "anchor_code": anchor_code,
                                "anchor_name": anchor_name,
                            },
                        )
                    )

        return candidates

    async def _search_vector_guidelines(
        self,
        *,
        diagnosis: str | None,
        drugs: list[str],
        clinical_note: str | None = None,
        top_k: int = 3,
    ) -> list[RecommendationCandidate]:
        """
        vector_documents에서 유사 guideline을 검색해 후보로 변환한다.

        Notes:
            현재는 반환 type을 followup으로 두고 있으나,
            추후 vector 문서 메타데이터(category 등)가 정리되면 타입도 함께 반영 가능하다.
        """
        normalized_diagnosis = self._normalize_diagnosis_text(diagnosis)
        matched_disease = await self._match_disease(normalized_diagnosis)
        disease_name = getattr(matched_disease, "name", None) if matched_disease else None

        query = self._build_vector_query(
            diagnosis=normalized_diagnosis,
            disease_name=disease_name,
            drugs=drugs,
            clinical_note=clinical_note,
        )

        if not query:
            return []

        similar_docs: list[Any] = []
        try:
            vector = encode(query)
            similar_docs = await self.vector_doc_repo.search_similar(
                vector,
                reference_type="disease_guideline",
                top_k=top_k,
            )
        except Exception:
            logger.exception("vector similarity search failed")
            return []

        candidates: list[RecommendationCandidate] = []

        for doc in similar_docs:
            content = getattr(doc, "content", None)
            if not isinstance(content, str) or not content.strip():
                continue

            candidates.append(
                self._create_recommendation_candidate(
                    recommendation_type="followup",
                    source="vector_fallback",
                    content=content,
                    score=0.9,
                    metadata={
                        "matched_from": normalized_diagnosis or clinical_note,
                        "reference_type": getattr(doc, "reference_type", None),
                        "reference_id": getattr(doc, "reference_id", None),
                    },
                )
            )

        return candidates

    async def _fetch_drug_details(self, drug_names: list[str]) -> list[dict[str, Any]]:
        """약물명 목록으로 DB에서 상세정보를 조회한다."""
        details: list[dict[str, Any]] = []
        for name in drug_names[:10]:
            name = name.strip()
            if not name:
                continue
            rows = await self.drug_repo.search_by_name(name, limit=1)
            if not rows:
                # OCR 오타 보정: 점→정
                import re as _re

                corrected = _re.sub(r"점(\d|$)", r"정\1", name)
                if corrected != name:
                    rows = await self.drug_repo.search_by_name(corrected, limit=1)
            if rows:
                d = rows[0]
                details.append(
                    {
                        "name": d.name,
                        "efficacy": d.efficacy,
                        "dosage": d.dosage,
                        "caution": " ".join(filter(None, [d.caution_1, d.caution_2]))[:300]
                        if (d.caution_1 or d.caution_2)
                        else None,
                        "main_ingredient": d.main_ingredient,
                    }
                )
            else:
                details.append({"name": name})
        return details

    async def _generate_ai_recommendations(
        self,
        *,
        diagnosis_list: list[str],
        guideline_texts: list[str],
        drug_details: list[dict[str, Any]],
    ) -> list[RecommendationCandidate]:
        """OpenAI를 활용해 진단+가이드라인+약물정보 기반 구체적 추천을 생성한다."""
        diag_str = ", ".join(d.strip() for d in diagnosis_list if d.strip())
        gl_str = "\n".join(f"- {t}" for t in guideline_texts[:15]) if guideline_texts else "(가이드라인 없음)"
        drug_str = ""
        for dd in drug_details:
            parts = [f"약물명: {dd['name']}"]
            if dd.get("efficacy"):
                parts.append(f"효능: {dd['efficacy'][:150]}")
            if dd.get("dosage"):
                parts.append(f"용법: {dd['dosage'][:150]}")
            if dd.get("caution"):
                parts.append(f"주의사항: {dd['caution'][:150]}")
            drug_str += "\n".join(parts) + "\n---\n"

        system_prompt = """당신은 환자의 건강관리 목표를 추천하는 AI 건강 어시스턴트입니다.

규칙:
- 환자의 진단명, 가이드라인, 처방약 정보를 종합하여 실천 가능한 건강관리 목표를 추천하세요.
- 각 추천은 구체적이고 실천 가능한 행동 지침이어야 합니다. (예: "하루 물 1.5L 마시기", "식후 30분 걷기")
- 약물 정보가 있으면 해당 약의 부작용 주의사항이나 생활습관 주의점을 반영하세요.
- 절대 금지: 약물 복용법/용법용량 안내 (예: "1일 2회 복용하세요", "식사와 함께 복용하세요", "아침저녁 복용" 등). 복용법은 이미 처방전에서 설정되어 있으므로 추천에 포함하지 마세요.
- 의학적 진단이나 처방 변경 지시는 절대 하지 마세요.
- 결과는 반드시 JSON 배열로만 반환하세요. 설명 없이 JSON만 출력하세요.

출력 형식:
[
  {"type": "lifestyle", "content": "...", "frequency": "daily"},
  {"type": "warning", "content": "...", "frequency": "as_needed"},
  {"type": "followup", "content": "...", "frequency": "monthly"}
]

type 종류: lifestyle(식이/운동/생활습관), warning(부작용/주의사항), followup(정기검진/추적관찰)
frequency 종류: daily, weekly, 3_per_week, every_other_day, monthly, as_needed

5~8개의 추천을 생성하세요. lifestyle 추천을 주로 포함하고, 약물 복용법 안내는 제외하세요."""

        user_prompt = f"""환자 정보:
- 진단명: {diag_str}
- 처방약: {drug_str if drug_str.strip() else "(없음)"}

관련 가이드라인:
{gl_str}

위 정보를 종합하여 이 환자에게 맞는 건강관리 목표를 추천해주세요."""

        try:
            response = await chat_completion(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.3,
            )
            import json

            # JSON 블록 추출
            text = response.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
            items = json.loads(text)
            if not isinstance(items, list):
                return []

            candidates: list[RecommendationCandidate] = []
            for item in items:
                if not isinstance(item, dict) or not item.get("content"):
                    continue
                candidates.append(
                    self._create_recommendation_candidate(
                        recommendation_type=item.get("type", "lifestyle"),
                        source="ai_generated",
                        content=item["content"].strip(),
                        score=0.9,
                        metadata={"frequency": item.get("frequency", "daily")},
                    )
                )
            return candidates
        except Exception:
            logger.exception("AI recommendation generation failed")
            return []

    async def _build_prescription_recommendations(
        self,
        *,
        diagnosis_list: list[str],
        drugs: list[str],
    ) -> list[RecommendationCandidate]:
        """
        처방전 scan 결과를 바탕으로 recommendation 후보를 생성한다.

        1. 각 진단별 guideline 수집
        2. 약물 상세정보 DB 조회
        3. 가이드라인+약물정보를 OpenAI에 전달하여 구체적 추천 생성
        4. AI 실패 시 가이드라인 기반 fallback
        """
        # 1) 각 진단별 guideline 수집
        guideline_texts: list[str] = []
        guideline_candidates: list[RecommendationCandidate] = []
        for diag_entry in diagnosis_list:
            if not isinstance(diag_entry, str) or not diag_entry.strip():
                continue
            gl_cands = await self._build_guideline_recommendations(diagnosis=diag_entry.strip())
            if gl_cands:
                guideline_candidates.extend(gl_cands)
                guideline_texts.extend(c.content for c in gl_cands)

        # 2) 약물 상세정보 조회
        drug_details = await self._fetch_drug_details(drugs)

        # 3) AI 기반 추천 생성
        ai_candidates = await self._generate_ai_recommendations(
            diagnosis_list=diagnosis_list,
            guideline_texts=guideline_texts,
            drug_details=drug_details,
        )

        if ai_candidates:
            return ai_candidates

        # 4) AI 실패 시 가이드라인 기반 fallback
        if guideline_candidates:
            return guideline_candidates

        # 5) 가이드라인도 없으면 vector fallback
        first_diag = self._normalize_diagnosis_text(diagnosis_list[0] if diagnosis_list else None)
        if first_diag:
            vector_candidates = await self._search_vector_guidelines(
                diagnosis=first_diag,
                drugs=drugs,
                top_k=3,
            )
            if vector_candidates:
                return vector_candidates

        # 6) 최종 fallback
        if diagnosis_list:
            diag_summary = ", ".join(d.strip() for d in diagnosis_list[:3] if isinstance(d, str) and d.strip())
            if diag_summary:
                return [
                    self._create_recommendation_candidate(
                        recommendation_type="followup",
                        source="scan.diagnosis",
                        content=f"진단 정보 '{diag_summary}' 기준으로 생활관리 및 추적 관찰 항목을 확인해보세요.",
                        score=0.6,
                    )
                ]

        return []

    async def _build_medical_record_recommendations(
        self,
        *,
        diagnosis_list: list[str],
        clinical_note: str | None,
    ) -> list[RecommendationCandidate]:
        """
        진료기록지 scan 결과를 기반으로 recommendation 후보를 생성한다.
        """
        guideline_texts: list[str] = []
        guideline_candidates: list[RecommendationCandidate] = []

        for diag_entry in diagnosis_list:
            if not isinstance(diag_entry, str) or not diag_entry.strip():
                continue
            gl_cands = await self._build_guideline_recommendations(diagnosis=diag_entry.strip())
            if gl_cands:
                guideline_candidates.extend(gl_cands)
                guideline_texts.extend(c.content for c in gl_cands)

        ai_candidates = await self._generate_ai_recommendations(
            diagnosis_list=diagnosis_list,
            guideline_texts=guideline_texts,
            drug_details=[],
        )

        if ai_candidates:
            return ai_candidates

        if guideline_candidates:
            return guideline_candidates

        first_diag = self._normalize_diagnosis_text(diagnosis_list[0] if diagnosis_list else None)
        normalized_clinical_note = (
            clinical_note.strip() if isinstance(clinical_note, str) and clinical_note.strip() else None
        )
        if first_diag or normalized_clinical_note:
            vector_candidates = await self._search_vector_guidelines(
                diagnosis=first_diag,
                drugs=[],
                clinical_note=normalized_clinical_note,
                top_k=3,
            )
            if vector_candidates:
                return vector_candidates

        if diagnosis_list:
            diag_summary = ", ".join(d.strip() for d in diagnosis_list[:3] if isinstance(d, str) and d.strip())
            if diag_summary:
                return [
                    self._create_recommendation_candidate(
                        recommendation_type="followup",
                        source="scan.medical_record.diagnosis",
                        content=f"진단 정보 '{diag_summary}' 기준으로 증상 변화와 경과를 관찰하고 필요한 추적 진료 일정을 확인해보세요.",
                        score=0.9,
                    )
                ]

        return []

    async def _build_fallback_recommendation(
        self,
        *,
        document_type: str,
    ) -> list[RecommendationCandidate]:
        """
        추천 후보를 만들기 어려운 경우 기본 fallback 후보를 생성한다.
        """
        if document_type == "medical_record":
            content = (
                "진료기록지에서 진단명이나 핵심 진료 내용을 충분히 추출하지 못했어요. "
                "증상 기록을 정리하고 기본적인 건강관리 가이드를 먼저 확인해보세요."
            )
            source = "scan.medical_record"
        else:
            content = "스캔 결과에서 진단/약물 정보를 찾지 못했어요. 텍스트 보정 또는 수동 입력 후 다시 시도해 주세요."
            source = "scan"

        return [
            self._create_recommendation_candidate(
                recommendation_type="lifestyle",
                source=source,
                content=content,
                score=0.1,
            )
        ]

    def _extract_scan_fields(self, scan: dict[str, Any]) -> tuple[list[str], str | None, list[str]]:
        """scan dict에서 diagnosis_list, clinical_note, drugs를 추출한다."""
        diagnosis_list_raw = scan.get("diagnosis_list") or []
        if not diagnosis_list_raw:
            single = scan.get("diagnosis")
            if isinstance(single, str) and single.strip():
                diagnosis_list_raw = [single.strip()]
        diagnosis_list: list[str] = [d for d in diagnosis_list_raw if isinstance(d, str) and d.strip()]

        clinical_note_raw = scan.get("clinical_note")
        clinical_note = (
            clinical_note_raw.strip() if isinstance(clinical_note_raw, str) and clinical_note_raw.strip() else None
        )

        drugs_raw = scan.get("drugs") or []
        drugs: list[str] = []
        if isinstance(drugs_raw, list):
            for d in drugs_raw:
                if isinstance(d, str) and d.strip():
                    drugs.append(d.strip())
                elif isinstance(d, dict) and d.get("name", "").strip():
                    drugs.append(d["name"].strip())

        return diagnosis_list, clinical_note, drugs

    async def get_for_scan(self, user_id: int, scan_id: int) -> dict[str, Any]:
        """
        특정 scan의 recommendation을 조회하거나, 없으면 새로 생성한다.
        """
        scan = await self.scan_repo.get_by_id_for_user(user_id, scan_id)
        if not scan:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="scan not found")

        existing = await self.recommendation_repo.list_by_user_scan(user_id=user_id, scan_id=scan_id)
        if existing:
            return {"scan_id": scan_id, "items": [_rec_to_response_dict(r) for r in existing]}

        document_type = self._normalize_document_type(scan.get("document_type"))
        diagnosis_list, clinical_note, drugs = self._extract_scan_fields(scan)

        batch = await self.recommendation_repo.create_batch(
            user_id=user_id,
            retrieval_strategy=f"scan-{document_type}-multi-diag-v3",
        )

        if document_type == "medical_record":
            candidates = list(
                await self._build_medical_record_recommendations(
                    diagnosis_list=diagnosis_list,
                    clinical_note=clinical_note,
                )
            )
        else:
            candidates = list(
                await self._build_prescription_recommendations(
                    diagnosis_list=diagnosis_list,
                    drugs=drugs,
                )
            )

        if not candidates:
            candidates = list(await self._build_fallback_recommendation(document_type=document_type))

        final_candidates = await finalize_recommendations(
            candidates,
            enable_llm_refinement=getattr(config, "ENABLE_LLM_REFINEMENT", False),
        )

        created = await self._save_candidates(
            user_id=user_id,
            scan_id=scan_id,
            batch_id=batch.id,
            candidates=final_candidates,
            status_value="candidate",
        )

        return {"scan_id": scan_id, "items": [_rec_to_response_dict(r) for r in created]}

    async def list_by_user(self, user_id: int, limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
        """
        사용자의 recommendation 목록을 조회한다.
        """
        try:
            recs = await self.recommendation_repo.list_by_user(user_id, limit=limit, offset=offset)
            return [_rec_to_response_dict(r) for r in recs]
        except Exception as e:
            logger.exception("list_by_user failed")
            raise HTTPException(status_code=500, detail="서버 내부 오류가 발생했습니다.") from e

    async def list_active(self, user_id: int) -> list[dict[str, Any]]:
        """
        사용자의 active recommendation 목록을 조회한다 (content 중복 제거).
        """
        try:
            active_recs = await self.recommendation_repo.list_active_for_user(user_id)
            seen_contents: set[str] = set()
            result: list[dict[str, Any]] = []
            for ar in active_recs:
                rec = ar.recommendation
                content_key = (rec.content or "").strip()
                if content_key in seen_contents:
                    continue
                seen_contents.add(content_key)
                result.append(_rec_to_response_dict(rec))
            return result
        except Exception as e:
            logger.exception("list_active failed")
            raise HTTPException(status_code=500, detail="서버 내부 오류가 발생했습니다.") from e

    async def update(self, user_id: int, recommendation_id: int, data: RecommendationUpdateRequest) -> dict[str, Any]:
        """
        recommendation 내용을 수정하거나 선택 여부를 갱신한다.
        """
        try:
            rec = await self.recommendation_repo.get_recommendation_for_user(user_id, recommendation_id)
            if not rec:
                raise HTTPException(status_code=404, detail="Recommendation not found")

            update_fields: list[str] = []
            if data.content is not None:
                rec.content = data.content
                update_fields.append("content")
            if data.is_selected is not None:
                rec.is_selected = data.is_selected
                update_fields.append("is_selected")

            if update_fields:
                await rec.save(update_fields=update_fields)

            return _rec_to_response_dict(rec)
        except HTTPException:
            raise
        except Exception as e:
            logger.exception("update failed")
            raise HTTPException(status_code=500, detail="서버 내부 오류가 발생했습니다.") from e

    async def delete(self, user_id: int, recommendation_id: int) -> None:
        """
        recommendation을 삭제 상태(revoked)로 변경한다.
        """
        try:
            rec = await self.recommendation_repo.get_recommendation_for_user(user_id, recommendation_id)
            if not rec:
                raise HTTPException(status_code=404, detail="Recommendation not found")

            rec.status = "revoked"
            await rec.save(update_fields=["status"])
        except HTTPException:
            raise
        except Exception as e:
            logger.exception("delete failed")
            raise HTTPException(status_code=500, detail="서버 내부 오류가 발생했습니다.") from e

    async def save_for_scan(self, user_id: int, scan_id: int) -> dict[str, Any]:
        """
        scan 기반 recommendation을 active recommendation으로 반영한다.
        기존 active 추천을 보존하고 새 추천만 추가한다.
        """
        try:
            recs = await self.recommendation_repo.list_by_user_scan(user_id=user_id, scan_id=scan_id)

            if not recs:
                generated = await self.get_for_scan(user_id=user_id, scan_id=scan_id)
                target_ids = [it["id"] for it in (generated.get("items") or [])]
            else:
                active_recs = [r for r in recs if r.status != "revoked"]
                selected = [r.id for r in active_recs if r.is_selected is True]
                all_ids = [r.id for r in active_recs]
                target_ids = selected or all_ids

            # 기존 active 추천 ID 수집 (중복 방지)
            existing_active = await self.recommendation_repo.list_active_for_user(user_id)
            existing_active_ids = {ar.recommendation_id for ar in existing_active}
            new_ids = [rid for rid in target_ids if rid not in existing_active_ids]

            await self.recommendation_repo.assign_active_many(user_id=user_id, recommendation_ids=new_ids)

            # 활성화된 추천은 like, revoked된 추천은 dislike 피드백 자동 기록
            revoked_ids = {r.id for r in recs if r.status == "revoked"} if recs else set()
            for rid in target_ids:
                await self.recommendation_repo.add_feedback(user_id, rid, feedback_type="like")
            for rid in revoked_ids:
                await self.recommendation_repo.add_feedback(user_id, rid, feedback_type="dislike")

            return {"scan_id": scan_id, "saved": True, "saved_count": len(new_ids)}
        except HTTPException:
            raise
        except Exception as e:
            logger.exception("save_for_scan failed")
            raise HTTPException(status_code=500, detail="서버 내부 오류가 발생했습니다.") from e

    async def add_feedback(self, user_id: int, recommendation_id: int, feedback_type: str) -> dict[str, Any]:
        """
        recommendation 피드백을 저장한다.
        """
        try:
            fb = await self.recommendation_repo.add_feedback(user_id, recommendation_id, feedback_type=feedback_type)
            if not fb:
                raise HTTPException(status_code=404, detail="Recommendation not found")

            return {
                "recommendation_id": recommendation_id,
                "feedback_type": feedback_type,
                "created_at": fb.created_at.isoformat() if fb.created_at else None,
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.exception("add_feedback failed")
            raise HTTPException(status_code=500, detail="서버 내부 오류가 발생했습니다.") from e
