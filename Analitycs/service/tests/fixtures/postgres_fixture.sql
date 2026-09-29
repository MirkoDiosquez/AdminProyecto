-- Fixture minima de datos conocidos para tests de integracion (T004).
-- Aplicar sobre una base de datos de TEST (nunca produccion) antes de correr
-- `pytest tests/integration`. Cubre los 13 reportes con variaciones deliberadas:
--   - gender: 'Hombre', 'Mujer', 'No binario', 'otro' (fuera de catalogo) y NULL -> "sin dato"
--   - age: rango 18-65 + NULL (para promedio con exclusion de NULL)
--   - country: 'Argentina', 'Brasil', 'Chile' + NULL
--   - device: 'android' (la app solo existe para Android, no hay usuarios 'ios')
--   - registered_at: distintas antiguedades (para registration-period)
--   - fact_app_usage: >= 6 apps distintas, 2 de ellas con avg_minutes empatado
--     (para probar desempate alfabetico por app_label en top5)
--   - fact_challenges: status 'active'/'completed'/'expired' variados
--   - fact_tasks: status 'completed' y otros valores distintos de 'pending' (ej. 'in_progress')
--     para validar que "no completada" es status != 'completed', no un literal fijo.

TRUNCATE fact_tasks, fact_challenges, fact_app_usage, fact_user_activity, dim_users RESTART IDENTITY CASCADE;

INSERT INTO dim_users (user_id, gender, age, country, device, registered_at) VALUES
  ('u1', 'Hombre',    20, 'Argentina', 'android', 1700000000000),
  ('u2', 'Mujer',     22, 'Argentina', 'android', 1705000000000),
  ('u3', 'No binario',30, 'Brasil',    'android', 1710000000000),
  ('u4', 'otro',      40, 'Chile',     'android', 1715000000000),
  ('u5', NULL,        NULL, NULL,      'android', 1720000000000);

INSERT INTO fact_user_activity (user_id, activity_date) VALUES
  ('u1', to_char(current_date, 'YYYY-MM-DD')),
  ('u2', to_char(current_date - 3, 'YYYY-MM-DD')),
  ('u3', to_char(current_date - 40, 'YYYY-MM-DD'));

-- Apps u1..u6 con u5/u6 empatadas en avg_minutes (ej. 50.0) para probar desempate alfabetico.
INSERT INTO fact_app_usage (user_id, usage_date, package_name, app_label, minutes_used) VALUES
  ('u1', to_char(current_date, 'YYYY-MM-DD'), 'com.a', 'Alpha',   10),
  ('u1', to_char(current_date, 'YYYY-MM-DD'), 'com.b', 'Beta',    20),
  ('u1', to_char(current_date, 'YYYY-MM-DD'), 'com.c', 'Gamma',   30),
  ('u1', to_char(current_date, 'YYYY-MM-DD'), 'com.d', 'Delta',   40),
  ('u1', to_char(current_date, 'YYYY-MM-DD'), 'com.e', 'Zeta',    50),
  ('u1', to_char(current_date, 'YYYY-MM-DD'), 'com.f', 'Epsilon', 50);

INSERT INTO fact_challenges (user_id, challenge_id, status) VALUES
  ('u1', 'ch-1', 'completed'),
  ('u1', 'ch-2', 'active'),
  ('u2', 'ch-3', 'completed'),
  ('u2', 'ch-4', 'expired');

INSERT INTO fact_tasks (user_id, task_id, status) VALUES
  ('u1', 'tk-1', 'completed'),
  ('u1', 'tk-2', 'in_progress'),
  ('u2', 'tk-3', 'completed');
