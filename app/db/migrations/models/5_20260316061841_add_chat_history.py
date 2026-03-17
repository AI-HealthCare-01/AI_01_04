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
        ALTER TABLE "scans" ALTER COLUMN "unrecognized_drugs" TYPE JSONB USING "unrecognized_drugs"::JSONB;
        ALTER TABLE "scans" ALTER COLUMN "drugs" TYPE JSONB USING "drugs"::JSONB;
        ALTER TABLE "scans" ALTER COLUMN "ocr_raw" TYPE JSONB USING "ocr_raw"::JSONB;
        ALTER TABLE "scans" ALTER COLUMN "diagnosis_list" TYPE JSONB USING "diagnosis_list"::JSONB;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "scans" ALTER COLUMN "unrecognized_drugs" TYPE JSONB USING "unrecognized_drugs"::JSONB;
        ALTER TABLE "scans" ALTER COLUMN "drugs" TYPE JSONB USING "drugs"::JSONB;
        ALTER TABLE "scans" ALTER COLUMN "ocr_raw" TYPE JSONB USING "ocr_raw"::JSONB;
        ALTER TABLE "scans" ALTER COLUMN "diagnosis_list" TYPE JSONB USING "diagnosis_list"::JSONB;
        DROP TABLE IF EXISTS "medi_chat";
        DROP TABLE IF EXISTS "health_chat";"""


MODELS_STATE = (
    "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"
)
