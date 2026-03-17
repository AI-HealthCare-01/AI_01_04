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
        ALTER TABLE "drugs" ADD "raw_material_en" TEXT;
        ALTER TABLE "drugs" ADD "caution_2" TEXT;
        ALTER TABLE "drugs" ADD "efficacy" TEXT;
        ALTER TABLE "drugs" ADD "storage" TEXT;
        ALTER TABLE "drugs" ADD "change_log" TEXT;
        ALTER TABLE "drugs" ADD "main_ingredient" TEXT;
        ALTER TABLE "drugs" ADD "raw_material" TEXT;
        ALTER TABLE "drugs" ADD "dosage" TEXT;
        ALTER TABLE "drugs" ADD "caution_1" TEXT;
        ALTER TABLE "drugs" ADD "caution_3" TEXT;
        ALTER TABLE "drugs" ADD "caution_4" TEXT;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "drugs" DROP COLUMN "raw_material_en";
        ALTER TABLE "drugs" DROP COLUMN "caution_2";
        ALTER TABLE "drugs" DROP COLUMN "efficacy";
        ALTER TABLE "drugs" DROP COLUMN "storage";
        ALTER TABLE "drugs" DROP COLUMN "change_log";
        ALTER TABLE "drugs" DROP COLUMN "main_ingredient";
        ALTER TABLE "drugs" DROP COLUMN "raw_material";
        ALTER TABLE "drugs" DROP COLUMN "dosage";
        ALTER TABLE "drugs" DROP COLUMN "caution_1";
        ALTER TABLE "drugs" DROP COLUMN "caution_3";
        ALTER TABLE "drugs" DROP COLUMN "caution_4";
        DROP TABLE IF EXISTS "medi_chat";
        DROP TABLE IF EXISTS "health_chat";"""


MODELS_STATE = (
    "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"
)
