from datetime import date

class DashboardService:

    async def get_summary(self, user):
        """
        Dashboard 요약 정보 생성
        """

        # TODO: 실제 Repository 연동 예정

        # 현재는 placeholder
        return {
            "recent_prescription": None,
            "remaining_medication_days": 0,
            "today_medication_completed": False,
            "today_health_completed": False,
        }