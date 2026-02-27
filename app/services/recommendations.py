from app.dtos.recommendations import RecommendationUpdateRequest


class RecommendationService:
    async def get_for_scan(self, user_id: int, scan_id: int) -> dict:
        # TODO:
        # 1) scan_id가 user_id 소유인지 확인 (repo)
        # 2) scan 결과(진단명/약물) 조회
        # 3) 질병 가이드라인 + 약물 주의사항 기반으로 추천 후보 생성/조회
        return {
            "scan_id": scan_id,
            "items": [],  # RecommendationResponse 리스트 형태
        }

    async def update(self, user_id: int, recommendation_id: int, data: RecommendationUpdateRequest) -> dict:
        # TODO:
        # 1) recommendation_id가 user_id 소유인지 확인
        # 2) content/필드 업데이트
        return {
            "id": recommendation_id,
            "content": data.content,
            "is_selected": data.is_selected,
        }

    async def delete(self, user_id: int, recommendation_id: int) -> None:
        # TODO:
        # 1) 소유권 확인
        # 2) 삭제 또는 status=revoked 처리
        return None

    async def save_for_scan(self, user_id: int, scan_id: int) -> dict:
        # TODO:
        # 1) scan_id 소유권 확인
        # 2) 선택된 추천들을 active로 반영
        return {
            "scan_id": scan_id,
            "saved": True,
            "saved_count": 0,
        }
