from pydantic import BaseModel


class ChatRequest(BaseModel):
    # 필수 필드
    patient_id: str

    # 선택 필드 (데이터가 없어도 에러가 나지 않음)
    disease_code: str | None = None
    medications: list[str] | None = []
    user_question: str | None = None
    mode: str | None = "medication"


class ChatResponse(BaseModel):
    chat_answer: str
    report: dict | None = None
