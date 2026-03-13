from pydantic import BaseModel
from typing import List, Optional

class ChatRequest(BaseModel):
    # 필수 필드
    patient_id: str
    
    # 선택 필드 (데이터가 없어도 에러가 나지 않음)
    disease_code: Optional[str] = None
    medications: Optional[List[str]] = []
    user_question: Optional[str] = None
    mode: Optional[str] = "medication"

class ChatResponse(BaseModel):
    chat_answer: str
    report: Optional[dict] = None