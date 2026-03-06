from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "scans"
        ADD COLUMN IF NOT EXISTS "document_type" VARCHAR(30) NOT NULL DEFAULT 'prescription';

        ALTER TABLE "scans"
        ADD COLUMN IF NOT EXISTS "clinical_note" TEXT;

        CREATE INDEX IF NOT EXISTS "idx_scans_user_id_document_type"
        ON "scans" ("user_id", "document_type");
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP INDEX IF EXISTS "idx_scans_user_id_document_type";

        ALTER TABLE "scans"
        DROP COLUMN IF EXISTS "clinical_note";

        ALTER TABLE "scans"
        DROP COLUMN IF EXISTS "document_type";
    """
