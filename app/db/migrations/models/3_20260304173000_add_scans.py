from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "scans" (
            "id" SERIAL NOT NULL PRIMARY KEY,
            "status" VARCHAR(30) NOT NULL DEFAULT 'uploaded',
            "analyzed_at" TIMESTAMPTZ,
            "document_date" VARCHAR(10),
            "diagnosis" TEXT,
            "drugs" JSONB NOT NULL DEFAULT '[]',
            "raw_text" TEXT,
            "ocr_raw" JSONB,
            "file_path" TEXT NOT NULL,
            "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            "user_id" BIGINT NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS "idx_scans_user_id_d51f17" ON "scans" ("user_id", "id");
        CREATE INDEX IF NOT EXISTS "idx_scans_user_id_8ef2cb" ON "scans" ("user_id", "created_at");
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "scans";
    """


MODELS_STATE = ""
