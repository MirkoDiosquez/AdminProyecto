-- ============================================================================
-- Índices — optimización de consultas de Analytics
-- Ejecutar después de postgre.sql
-- ============================================================================

-- dim_users
CREATE INDEX IF NOT EXISTS idx_dim_users_country       ON dim_users(country);
CREATE INDEX IF NOT EXISTS idx_dim_users_gender        ON dim_users(gender);
CREATE INDEX IF NOT EXISTS idx_dim_users_age           ON dim_users(age);
CREATE INDEX IF NOT EXISTS idx_dim_users_device        ON dim_users(device);
CREATE INDEX IF NOT EXISTS idx_dim_users_registered_at ON dim_users(registered_at);

-- fact_user_activity
CREATE INDEX IF NOT EXISTS idx_fua_user_id       ON fact_user_activity(user_id);
CREATE INDEX IF NOT EXISTS idx_fua_activity_date ON fact_user_activity(activity_date);

-- fact_app_usage
CREATE INDEX IF NOT EXISTS idx_fap_user_id      ON fact_app_usage(user_id);
CREATE INDEX IF NOT EXISTS idx_fap_usage_date   ON fact_app_usage(usage_date);
CREATE INDEX IF NOT EXISTS idx_fap_package_name ON fact_app_usage(package_name);

-- fact_challenges
CREATE INDEX IF NOT EXISTS idx_fch_user_id      ON fact_challenges(user_id);
CREATE INDEX IF NOT EXISTS idx_fch_status       ON fact_challenges(status);
CREATE INDEX IF NOT EXISTS idx_fch_group_id     ON fact_challenges(group_id);
CREATE INDEX IF NOT EXISTS idx_fch_challenge_id ON fact_challenges(challenge_id);

-- fact_tasks
CREATE INDEX IF NOT EXISTS idx_ft_user_id    ON fact_tasks(user_id);
CREATE INDEX IF NOT EXISTS idx_ft_status     ON fact_tasks(status);
CREATE INDEX IF NOT EXISTS idx_ft_created_at ON fact_tasks(created_at);

-- fact_user_groups
CREATE INDEX IF NOT EXISTS idx_fug_user_id   ON fact_user_groups(user_id);
CREATE INDEX IF NOT EXISTS idx_fug_group_id  ON fact_user_groups(group_id);
CREATE INDEX IF NOT EXISTS idx_fug_is_active ON fact_user_groups(is_active);
