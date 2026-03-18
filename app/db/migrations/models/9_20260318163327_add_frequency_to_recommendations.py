from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "recommendations" ADD COLUMN IF NOT EXISTS "frequency" VARCHAR(30);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "recommendations" DROP COLUMN IF EXISTS "frequency";"""
