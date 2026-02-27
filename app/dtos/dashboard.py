from pydantic import BaseModel


class DashboardSummaryResponse(BaseModel):
    recent_prescription: dict | None
    remaining_medication_days: int
    today_medication_completed: bool
    today_health_completed: bool
