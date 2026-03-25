"""추천 서비스 - 복수 진단 / 질병코드 매핑 테스트."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from tortoise.contrib.test import TestCase

from app.models.diseases import Disease, DiseaseCodeMapping, DiseaseGuideline
from app.models.scans import Scan
from app.models.users import User
from app.services.recommendations import RecommendationService


async def _make_user(email: str) -> User:
    return await User.create(
        email=email,
        name="테스터",
        phone_number="01012345678",
        birthday="1990-01-01",
    )


class TestParseDiagnosisEntry(TestCase):
    """_parse_diagnosis_entry 단위 테스트."""

    def setUp(self) -> None:
        self.svc = RecommendationService()

    async def test_code_and_name(self):
        """'I109 고혈압' → ('I109', '고혈압')"""
        code, name = self.svc._parse_diagnosis_entry("I109 기타 및 상세불명의 원발성 고혈압")
        assert code == "I109"
        assert name == "기타 및 상세불명의 원발성 고혈압"

    async def test_code_only(self):
        """'E118' → ('E118', None)"""
        code, name = self.svc._parse_diagnosis_entry("E118")
        assert code == "E118"
        assert name is None

    async def test_name_only(self):
        """'고혈압' → (None, '고혈압')"""
        code, name = self.svc._parse_diagnosis_entry("고혈압")
        assert code is None
        assert name == "고혈압"

    async def test_empty(self):
        """빈 문자열 → (None, None)"""
        code, name = self.svc._parse_diagnosis_entry("")
        assert code is None
        assert name is None

    async def test_none(self):
        code, name = self.svc._parse_diagnosis_entry(None)
        assert code is None
        assert name is None

    async def test_code_with_5_digits(self):
        """'E1180 합병증을 동반하지 않은 2형 당뇨병' → ('E1180', ...)"""
        code, name = self.svc._parse_diagnosis_entry("E1180 합병증을 동반하지 않은 2형 당뇨병")
        assert code == "E1180"
        assert "당뇨병" in name

    async def test_lowercase_code(self):
        """소문자 코드도 대문자로 변환."""
        code, name = self.svc._parse_diagnosis_entry("i109 고혈압")
        assert code == "I109"


class TestBuildGuidelineWithMapping(TestCase):
    """_build_guideline_recommendations - 질병코드 매핑 fallback 테스트."""

    async def test_direct_disease_match(self):
        """Disease 테이블에 직접 매칭되면 해당 가이드라인 반환."""
        disease = await Disease.create(name="고혈압", kcd_code="I10")
        await DiseaseGuideline.create(
            disease=disease,
            category="general_care",
            content="염분 섭취를 줄이세요",
        )

        svc = RecommendationService()
        candidates = await svc._build_guideline_recommendations(diagnosis="고혈압")

        assert len(candidates) >= 1
        assert any("염분" in c.content for c in candidates)

    async def test_code_mapping_fallback(self):
        """Disease 직접 매칭 실패 시 DiseaseCodeMapping → anchor 가이드라인 반환."""
        anchor_disease = await Disease.create(name="당뇨병", kcd_code="E14")
        await DiseaseGuideline.create(
            disease=anchor_disease,
            category="general_care",
            content="혈당을 정기적으로 측정하세요",
        )
        await DiseaseCodeMapping.create(
            code="E118",
            name="2형 당뇨병",
            mapped_code="E14",
            mapped_name="당뇨병",
            is_anchor=False,
        )

        svc = RecommendationService()
        candidates = await svc._build_guideline_recommendations(diagnosis="E118 2형 당뇨병")

        assert len(candidates) >= 1
        assert any("혈당" in c.content for c in candidates)
        assert any(c.metadata.get("anchor_code") == "E14" for c in candidates)

    async def test_no_match_returns_empty(self):
        """매칭 안 되면 빈 리스트 반환."""
        svc = RecommendationService()
        candidates = await svc._build_guideline_recommendations(diagnosis="Z999 존재하지않는코드")
        assert candidates == []


class TestBuildPrescriptionMultiDiagnosis(TestCase):
    """_build_prescription_recommendations - 복수 진단 테스트."""

    async def test_multiple_diagnoses_collect_guidelines(self):
        """여러 진단에서 각각 가이드라인을 수집한다."""
        d1 = await Disease.create(name="고혈압", kcd_code="I10")
        await DiseaseGuideline.create(disease=d1, category="general_care", content="염분을 줄이세요")

        d2 = await Disease.create(name="당뇨병", kcd_code="E14")
        await DiseaseGuideline.create(disease=d2, category="general_care", content="혈당을 관리하세요")

        svc = RecommendationService()
        candidates = await svc._build_prescription_recommendations(
            diagnosis_list=["고혈압", "당뇨병"],
            drugs=["아스피린"],
        )

        contents = [c.content for c in candidates]
        assert any("염분" in c for c in contents), "고혈압 가이드라인 포함"
        assert any("혈당" in c for c in contents), "당뇨병 가이드라인 포함"

    async def test_empty_diagnosis_list_with_drugs(self):
        """진단 없이 약물만 있으면 AI/가이드라인 없이 빈 리스트 반환."""
        svc = RecommendationService()
        with patch.object(svc, "_generate_ai_recommendations", new=AsyncMock(return_value=[])):
            candidates = await svc._build_prescription_recommendations(
                diagnosis_list=[],
                drugs=["타이레놀", "아스피린"],
            )

        assert len(candidates) == 0

    async def test_single_diagnosis_with_code(self):
        """단일 진단(코드+이름 형태)도 정상 처리."""
        disease = await Disease.create(name="급성 상기도감염", kcd_code="J06")
        await DiseaseGuideline.create(
            disease=disease,
            category="general_care",
            content="충분한 휴식을 취하세요",
        )
        await DiseaseCodeMapping.create(
            code="J06",
            name="급성 상기도감염",
            mapped_code="J06",
            mapped_name="급성 상기도감염",
            is_anchor=True,
        )

        svc = RecommendationService()
        with patch.object(svc, "_generate_ai_recommendations", new=AsyncMock(return_value=[])):
            candidates = await svc._build_prescription_recommendations(
                diagnosis_list=["J06 급성 상기도감염"],
                drugs=[],
            )

        assert any("휴식" in c.content for c in candidates)


class TestBuildMedicalRecordMultiDiagnosis(TestCase):
    """_build_medical_record_recommendations - 복수 진단 테스트."""

    async def test_multiple_diagnoses_with_clinical_note(self):
        """복수 진단 + clinical_note 조합 처리."""
        d1 = await Disease.create(name="편두통", kcd_code="G43")
        await DiseaseGuideline.create(disease=d1, category="general_care", content="유발인자를 피하세요")

        svc = RecommendationService()
        with patch.object(svc, "_generate_ai_recommendations", new=AsyncMock(return_value=[])):
            candidates = await svc._build_medical_record_recommendations(
                diagnosis_list=["편두통"],
                clinical_note="두통 빈도 증가, 스트레스 관리 필요",
            )

        contents = [c.content for c in candidates]
        assert any("유발인자" in c for c in contents)
        # clinical_note가 있으면 lifestyle/warning 후보도 추가됨
        types = [c.type for c in candidates]
        assert "general_care" in types or "lifestyle" in types


class TestGetForScanMultiDiagnosis(TestCase):
    """get_for_scan - diagnosis_list 통합 테스트."""

    async def test_uses_diagnosis_list(self):
        """scan의 diagnosis_list를 사용하여 추천을 생성한다."""
        user = await _make_user("multi_diag@example.com")
        disease = await Disease.create(name="고혈압", kcd_code="I10")
        await DiseaseGuideline.create(
            disease=disease,
            category="general_care",
            content="염분 섭취를 줄이세요",
        )

        scan = await Scan.create(
            user=user,
            file_path="test.jpg",
            status="done",
            diagnosis_list=["고혈압"],
            drugs=["아스피린"],
        )

        svc = RecommendationService()
        with patch.object(svc, "_search_vector_guidelines", new=AsyncMock(return_value=[])):
            result = await svc.get_for_scan(user_id=user.id, scan_id=scan.id)

        assert result["scan_id"] == scan.id
        assert len(result["items"]) >= 1

    async def test_falls_back_to_single_diagnosis(self):
        """diagnosis_list가 비어있으면 diagnosis(단수) fallback."""
        user = await _make_user("single_diag@example.com")
        scan = await Scan.create(
            user=user,
            file_path="test.jpg",
            status="done",
            diagnosis="감기",
            diagnosis_list=[],
            drugs=[],
        )

        svc = RecommendationService()
        with patch.object(svc, "_search_vector_guidelines", new=AsyncMock(return_value=[])):
            result = await svc.get_for_scan(user_id=user.id, scan_id=scan.id)

        assert result["scan_id"] == scan.id
        # fallback으로 "감기" 기반 추천이 생성되어야 함
        assert len(result["items"]) >= 1
