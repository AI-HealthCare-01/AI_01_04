from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "medi_chat" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "patient_id" VARCHAR(50) NOT NULL,
    "disease_code" VARCHAR(20),
    "medications" TEXT,
    "advice" TEXT,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS "idx_medi_chat_patient_774dc3" ON "medi_chat" ("patient_id");
        CREATE TABLE IF NOT EXISTS "health_chat" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "patient_id" VARCHAR(50) NOT NULL,
    "user_question" TEXT NOT NULL,
    "advice" TEXT NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS "idx_health_chat_patient_53559b" ON "health_chat" ("patient_id");
        ALTER TABLE "vector_documents" ALTER COLUMN "embedding" TYPE TEXT USING "embedding"::TEXT;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "vector_documents" ALTER COLUMN "embedding" TYPE vector(1536) USING "embedding"::vector(1536);
        DROP TABLE IF EXISTS "health_chat";
        DROP TABLE IF EXISTS "medi_chat";"""


MODELS_STATE = (
    "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"
    "DBeaGS7skvj+/H9QP5CJ"
)
