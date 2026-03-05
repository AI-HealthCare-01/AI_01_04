from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "scans" (
            "id" SERIAL NOT NULL PRIMARY KEY,
            "status" VARCHAR(20) NOT NULL DEFAULT 'uploaded',
            "file_path" VARCHAR(500) NOT NULL,
            "analyzed_at" TIMESTAMPTZ,
            "document_date" VARCHAR(20),
            "diagnosis" VARCHAR(200),
            "drugs" JSONB NOT NULL DEFAULT '[]',
            "raw_text" TEXT,
            "ocr_raw" JSONB,
            "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            "user_id" BIGINT NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE
        );
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "scans";
    """
