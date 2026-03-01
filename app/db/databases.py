from fastapi import FastAPI
from tortoise import Tortoise
from tortoise.contrib.fastapi import register_tortoise

from app.core import config

TORTOISE_APP_MODELS = [
    "aerich.models",
    "app.models.users",
    "app.models.user_credentials",
    "app.models.user_auth_providers",
    "app.models.diseases",  # Disease, DiseaseGuideline
    "app.models.drugs",
    "app.models.prescriptions",  # Prescription, PrescriptionMemo, MedicationIntakeLog
    "app.models.chatbot",  # ChatbotSession, ChatbotMessage, ChatbotSessionSummary
    "app.models.vector_documents",
    "app.models.user_features",  # UserFeatureSnapshot, UserCurrentFeatures
    "app.models.recommendations",  # RecommendationBatch, Recommendation, UserActiveRecommendation, RecommendationFeedback
]

TORTOISE_ORM = {
    "connections": {
        "default": {
            "engine": "tortoise.backends.asyncpg",
            "credentials": {
                "host": config.DB_HOST,
                "port": config.DB_PORT,
                "user": config.DB_USER,
                "password": config.DB_PASSWORD,
                "database": config.DB_NAME,
                # asyncpg는 connect_timeout 미지원 (MySQL/asyncmy 전용)
                "maxsize": config.DB_CONNECTION_POOL_MAXSIZE,
            },
        },
    },
    "apps": {
        "models": {
            "models": TORTOISE_APP_MODELS,
        },
    },
    "timezone": "Asia/Seoul",
}


def initialize_tortoise(app: FastAPI) -> None:
    Tortoise.init_models(TORTOISE_APP_MODELS, "models")
    register_tortoise(app, config=TORTOISE_ORM)
