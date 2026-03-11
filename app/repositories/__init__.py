"""
Repository 레이어

- 도메인별 Repository: user_id 스코프 적용 (user 데이터)
- 마스터 데이터: Disease, Drug - user 스코프 불필요
"""

from app.repositories.chatbot_repository import ChatbotRepository
from app.repositories.disease_repository import DiseaseRepository
from app.repositories.medication_intake_repository import MedicationIntakeRepository
from app.repositories.prescription_repository import PrescriptionRepository
from app.repositories.recommendation_repository import RecommendationRepository
from app.repositories.user_credential_repository import UserCredentialRepository
from app.repositories.user_repository import UserRepository


__all__ = [
    "UserRepository",
    "UserCredentialRepository",
    "DiseaseRepository",
    "PrescriptionRepository",
    "MedicationIntakeRepository",
    "ChatbotRepository",
    "RecommendationRepository",
    "VectorDocumentRepository",
]
