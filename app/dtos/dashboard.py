from pydantic import BaseModel
from typing import Optional

class DashboardSummaryResponse(BaseModel):
    recent_prescription: Optional[dict]
    remaining_medication_days: int
    today_medication_completed: bool
    today_health_completed: bool