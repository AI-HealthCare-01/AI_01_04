from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "health_checklist_templates" (
            "id" SERIAL NOT NULL PRIMARY KEY,
            "label" VARCHAR(100) NOT NULL,
            "is_active" BOOL NOT NULL DEFAULT True,
            "sort_order" INT NOT NULL DEFAULT 0,
            "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        COMMENT ON TABLE "health_checklist_templates" IS '건강관리 체크리스트 템플릿(마스터)';

        CREATE TABLE IF NOT EXISTS "health_checklist_logs" (
            "id" SERIAL NOT NULL PRIMARY KEY,
            "date" DATE NOT NULL,
            "status" VARCHAR(20) NOT NULL,
            "checked_at" TIMESTAMPTZ,
            "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            "template_id" INT NOT NULL REFERENCES "health_checklist_templates" ("id") ON DELETE CASCADE,
            "user_id" BIGINT NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS "idx_health_chec_date_ec545b" ON "health_checklist_logs" ("date");
        CREATE INDEX IF NOT EXISTS "idx_health_chec_user_id_dac411" ON "health_checklist_logs" ("user_id", "date");
        CREATE INDEX IF NOT EXISTS "idx_health_chec_date_bb2557" ON "health_checklist_logs" ("date", "status");

        COMMENT ON TABLE "health_checklist_logs" IS '사용자 일자별 건강관리 로그';
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "health_checklist_logs";
        DROP TABLE IF EXISTS "health_checklist_templates";
    """


MODELS_STATE = (
    "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"
    "pBr2K50MxyYZfE98f/ARMJgAE="
)
