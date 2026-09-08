-- ============================================================================
-- Base de datos: anti_procrastinacion
-- Módulo: Panel Admin / Analytics
-- Fuente de datos: ETL (Firebase/Firestore -> PostgreSQL)
-- Convención de timestamps: epoch milliseconds (BIGINT), según constitution.md
--   Sección 3. Fechas puras (día calendario) usan TEXT 'YYYY-MM-DD'.
--
-- NOTA DE ARQUITECTURA (ver Analitycs/README.md para el detalle completo):
--   Este esquema reemplaza/actualiza al descripto en
--   ModeloDeDatos/modelo_admin.md (que usaba TIMESTAMPTZ/DATE y no tenía
--   fact_user_activity ni fact_tasks). Se documentó el conflicto en ese
--   archivo y en ModeloDeDatos/der_admin.md en vez de sobrescribirlos
--   silenciosamente.
-- ============================================================================

CREATE DATABASE anti_procrastinacion;
-- \c anti_procrastinacion

-- ============================================================================
-- 1. dim_users — Perfil demográfico y de registro del usuario
-- ============================================================================
CREATE TABLE IF NOT EXISTS dim_users (
    user_id         VARCHAR(128)    PRIMARY KEY,       -- mismo UID de Firebase Auth
    display_name    VARCHAR(100),
    email           VARCHAR(255),
    gender          VARCHAR(30),                        -- valor libre, no hardcodeado (ej: "Hombre","Mujer","Rarito", NULL)
    age             SMALLINT,
    country         VARCHAR(100),
    device          VARCHAR(150),                       -- ej: "Samsung Galaxy A54"
    registered_at   BIGINT,                              -- epoch ms
    first_login_at  BIGINT,                              -- epoch ms
    last_login_at   BIGINT                                -- epoch ms
);

-- ============================================================================
-- 2. fact_user_activity — Un registro por usuario/día en que hubo actividad.
--    Permite calcular usuarios activos por día/semana/mes.
-- ============================================================================
CREATE TABLE IF NOT EXISTS fact_user_activity (
    id              BIGSERIAL       PRIMARY KEY,
    user_id         VARCHAR(128)    NOT NULL REFERENCES dim_users(user_id),
    activity_date   TEXT            NOT NULL,            -- 'YYYY-MM-DD'
    CONSTRAINT uq_user_activity UNIQUE (user_id, activity_date)
);

-- ============================================================================
-- 3. fact_app_usage — Tiempo de pantalla agregado por día/usuario/app.
-- ============================================================================
CREATE TABLE IF NOT EXISTS fact_app_usage (
    id              BIGSERIAL       PRIMARY KEY,
    user_id         VARCHAR(128)    NOT NULL REFERENCES dim_users(user_id),
    usage_date      TEXT            NOT NULL,            -- 'YYYY-MM-DD'
    package_name    VARCHAR(255),
    app_label       VARCHAR(100),
    minutes_used    INTEGER,
    over_limit      BOOLEAN         DEFAULT FALSE,
    limit_min       INTEGER,
    recorded_at     BIGINT,                               -- epoch ms
    CONSTRAINT uq_app_usage_daily UNIQUE (user_id, usage_date, package_name)
);

-- ============================================================================
-- 4. fact_challenges — Desafíos/competencias por usuario.
-- ============================================================================
CREATE TABLE IF NOT EXISTS fact_challenges (
    id              BIGSERIAL       PRIMARY KEY,
    user_id         VARCHAR(128)    NOT NULL REFERENCES dim_users(user_id),
    group_id        VARCHAR(128),
    challenge_id    VARCHAR(128)    NOT NULL,
    title           VARCHAR(255),
    start_date      TEXT,                                 -- 'YYYY-MM-DD'
    end_date        TEXT,                                 -- 'YYYY-MM-DD'
    status          VARCHAR(30),                          -- 'completed' | 'expired' | 'active'
    points_reward   INTEGER,
    points_earned   INTEGER,
    completed_at    BIGINT,                                -- epoch ms
    recorded_at     BIGINT,                                -- epoch ms
    CONSTRAINT uq_user_challenge UNIQUE (user_id, challenge_id)
);

-- ============================================================================
-- 5. fact_tasks — Tareas por usuario.
-- ============================================================================
CREATE TABLE IF NOT EXISTS fact_tasks (
    id              BIGSERIAL       PRIMARY KEY,
    user_id         VARCHAR(128)    NOT NULL REFERENCES dim_users(user_id),
    task_id         VARCHAR(128)    NOT NULL,
    title           VARCHAR(255),
    status          VARCHAR(30),                          -- 'pending' | 'completed' | ...
    created_at      BIGINT,                                -- epoch ms
    completed_at    BIGINT,                                -- epoch ms
    recorded_at     BIGINT,                                -- epoch ms
    CONSTRAINT uq_user_task UNIQUE (user_id, task_id)
);

-- ============================================================================
-- 6. fact_user_groups — Participación de usuarios en grupos.
--    Un usuario puede abandonar y volver a entrar: la clave natural incluye
--    joined_at para no perder el historial de membresías.
-- ============================================================================
CREATE TABLE IF NOT EXISTS fact_user_groups (
    id              BIGSERIAL       PRIMARY KEY,
    user_id         VARCHAR(128)    NOT NULL REFERENCES dim_users(user_id),
    group_id        VARCHAR(128)    NOT NULL,
    group_name      VARCHAR(200),
    joined_at       BIGINT,                                -- epoch ms
    left_at         BIGINT,                                -- epoch ms, NULL si sigue activo
    is_active       BOOLEAN         DEFAULT TRUE,
    CONSTRAINT uq_user_group_membership UNIQUE (user_id, group_id, joined_at)
);
