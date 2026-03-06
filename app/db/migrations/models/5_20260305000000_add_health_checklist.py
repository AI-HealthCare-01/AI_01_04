from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "health_checklist_templates" (
            "id" SERIAL PRIMARY KEY,
            "label" VARCHAR(100) NOT NULL,
            "is_active" BOOL NOT NULL DEFAULT True,
            "sort_order" INT NOT NULL DEFAULT 0,
            "created_at" TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            "updated_at" TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        CREATE TABLE IF NOT EXISTS "health_checklist_logs" (
            "id" SERIAL PRIMARY KEY,
            "date" DATE NOT NULL,
            "status" VARCHAR(20) NOT NULL,
            "checked_at" TIMESTAMPTZ,
            "created_at" TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            "updated_at" TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            "template_id" INT NOT NULL REFERENCES "health_checklist_templates" ("id") ON DELETE CASCADE,
            "user_id" INT NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS "idx_health_checklist_logs_user_date" ON "health_checklist_logs" ("user_id", "date");
        CREATE INDEX IF NOT EXISTS "idx_health_checklist_logs_date_status" ON "health_checklist_logs" ("date", "status");
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "health_checklist_logs";
        DROP TABLE IF EXISTS "health_checklist_templates";
    """


MODELS_STATE = ""
