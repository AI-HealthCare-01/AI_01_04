from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "users" ALTER COLUMN "id" TYPE BIGINT USING "id"::BIGINT;
        ALTER TABLE "users" ADD COLUMN IF NOT EXISTS "profile_image_url" VARCHAR(500);
        ALTER TABLE "users" ADD COLUMN IF NOT EXISTS "last_login" TIMESTAMPTZ;
        ALTER TABLE "users" ADD COLUMN IF NOT EXISTS "is_active" BOOL NOT NULL DEFAULT True;
        ALTER TABLE "users" ADD COLUMN IF NOT EXISTS "birthday" DATE NOT NULL;
        ALTER TABLE "users" ADD COLUMN IF NOT EXISTS "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP;
        ALTER TABLE "users" ADD COLUMN IF NOT EXISTS "is_admin" BOOL NOT NULL DEFAULT False;
        ALTER TABLE "users" ADD COLUMN IF NOT EXISTS "hashed_password" VARCHAR(128) NOT NULL;
        ALTER TABLE "users" DROP COLUMN IF EXISTS "birth_date";
        ALTER TABLE "users" DROP COLUMN IF EXISTS "nickname";
        ALTER TABLE "users" DROP COLUMN IF EXISTS "role";
        ALTER TABLE "users" ALTER COLUMN "gender" SET NOT NULL;
        ALTER TABLE "users" ALTER COLUMN "name" TYPE VARCHAR(20) USING "name"::VARCHAR(20);
        ALTER TABLE "user_credentials" ALTER COLUMN "user_id" TYPE BIGINT USING "user_id"::BIGINT;
        ALTER TABLE "user_auth_providers" ALTER COLUMN "user_id" TYPE BIGINT USING "user_id"::BIGINT;
        ALTER TABLE "medication_intake_logs" ADD "intake_date" DATE NOT NULL;
        ALTER TABLE "medication_intake_logs" ADD "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP;
        ALTER TABLE "medication_intake_logs" ADD "slot_label" VARCHAR(30);
        ALTER TABLE "medication_intake_logs" ALTER COLUMN "intake_datetime" DROP NOT NULL;
        ALTER TABLE "prescriptions" ALTER COLUMN "user_id" TYPE BIGINT USING "user_id"::BIGINT;
        ALTER TABLE "chatbot_sessions" ALTER COLUMN "user_id" TYPE BIGINT USING "user_id"::BIGINT;
        ALTER TABLE "user_current_features" ALTER COLUMN "user_id" TYPE BIGINT USING "user_id"::BIGINT;
        ALTER TABLE "user_feature_snapshots" ALTER COLUMN "user_id" TYPE BIGINT USING "user_id"::BIGINT;
        ALTER TABLE "recommendations" ALTER COLUMN "user_id" TYPE BIGINT USING "user_id"::BIGINT;
        ALTER TABLE "recommendation_batches" ALTER COLUMN "user_id" TYPE BIGINT USING "user_id"::BIGINT;
        ALTER TABLE "recommendation_feedback" ALTER COLUMN "user_id" TYPE BIGINT USING "user_id"::BIGINT;
        ALTER TABLE "user_active_recommendations" ALTER COLUMN "user_id" TYPE BIGINT USING "user_id"::BIGINT;
        CREATE INDEX IF NOT EXISTS "idx_medication__intake__ccd0e0" ON "medication_intake_logs" ("intake_date", "status");
        CREATE INDEX IF NOT EXISTS "idx_medication__intake__dbfc1a" ON "medication_intake_logs" ("intake_date");"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP INDEX IF EXISTS "idx_medication__intake__dbfc1a";
        DROP INDEX IF EXISTS "idx_medication__intake__ccd0e0";
        ALTER TABLE "users" ALTER COLUMN "id" TYPE INT USING "id"::INT;
        ALTER TABLE "users" ADD "birth_date" DATE;
        ALTER TABLE "users" ADD "nickname" VARCHAR(50);
        ALTER TABLE "users" ADD "role" VARCHAR(5) NOT NULL DEFAULT 'USER';
        ALTER TABLE "users" DROP COLUMN IF EXISTS "profile_image_url";
        ALTER TABLE "users" DROP COLUMN IF EXISTS "last_login";
        ALTER TABLE "users" DROP COLUMN IF EXISTS "is_active";
        ALTER TABLE "users" DROP COLUMN IF EXISTS "birthday";
        ALTER TABLE "users" DROP COLUMN IF EXISTS "updated_at";
        ALTER TABLE "users" DROP COLUMN IF EXISTS "is_admin";
        ALTER TABLE "users" DROP COLUMN IF EXISTS "hashed_password";
        ALTER TABLE "users" ALTER COLUMN "gender" DROP NOT NULL;
        ALTER TABLE "users" ALTER COLUMN "name" TYPE VARCHAR(100) USING "name"::VARCHAR(100);
        ALTER TABLE "prescriptions" ALTER COLUMN "user_id" TYPE INT USING "user_id"::INT;
        ALTER TABLE "chatbot_sessions" ALTER COLUMN "user_id" TYPE INT USING "user_id"::INT;
        ALTER TABLE "recommendations" ALTER COLUMN "user_id" TYPE INT USING "user_id"::INT;
        ALTER TABLE "user_credentials" ALTER COLUMN "user_id" TYPE INT USING "user_id"::INT;
        ALTER TABLE "user_auth_providers" ALTER COLUMN "user_id" TYPE INT USING "user_id"::INT;
        ALTER TABLE "medication_intake_logs" DROP COLUMN "intake_date";
        ALTER TABLE "medication_intake_logs" DROP COLUMN "updated_at";
        ALTER TABLE "medication_intake_logs" DROP COLUMN "slot_label";
        ALTER TABLE "medication_intake_logs" ALTER COLUMN "intake_datetime" SET NOT NULL;
        ALTER TABLE "recommendation_batches" ALTER COLUMN "user_id" TYPE INT USING "user_id"::INT;
        ALTER TABLE "user_current_features" ALTER COLUMN "user_id" TYPE INT USING "user_id"::INT;
        ALTER TABLE "user_feature_snapshots" ALTER COLUMN "user_id" TYPE INT USING "user_id"::INT;
        ALTER TABLE "recommendation_feedback" ALTER COLUMN "user_id" TYPE INT USING "user_id"::INT;
        ALTER TABLE "user_active_recommendations" ALTER COLUMN "user_id" TYPE INT USING "user_id"::INT;
        COMMENT ON COLUMN "users"."role" IS 'USER: USER\nADMIN: ADMIN';"""


MODELS_STATE = (
    "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"
    "oC"
)
