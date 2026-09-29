# 🚀 Cómo levantar y ejecutar el proyecto — API de Reportes (`001-reportes-fastapi`)

Guía con los comandos **en orden** para levantar todo el entorno desde cero: base de datos,
servidor, y probar los endpoints desde Swagger UI.

> Ejecutar todo desde la raíz del repo, ajustando la ruta si hace falta.

---

## 0. Variables de referencia

```bash
cd Analitycs
```

---

## 1. Levantar PostgreSQL + Redis con Docker

> Se usan puertos alternativos (**5433**/**6380**) porque el 5432/6379 pueden estar ocupados por
> otro Postgres/Redis local. Si tenés los puertos libres, podés omitir las variables
> `POSTGRES_PORT`/`REDIS_PORT` y usar los defaults (5432/6379).

```bash
cd Analitycs
POSTGRES_PORT=5433 REDIS_PORT=6380 docker compose up -d
```

Verificar que ambos estén `healthy`:

```bash
docker ps --filter "name=analytics_" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

---

## 2. Aplicar el esquema de base de datos

> La imagen de Docker ya crea la base `anti_procrastinacion` automáticamente, por eso se salta la
> línea `CREATE DATABASE` del script original (línea 1-17).

```bash
cd Analitycs
tail -n +18 postgre.sql | docker exec -i analytics_postgres psql -U analytics_user -d anti_procrastinacion
```

Aplicar los índices:

```bash
docker exec -i analytics_postgres psql -U analytics_user -d anti_procrastinacion -f - < indexes.sql
```

---

## 3. Aplicar datos de prueba (fixture)

```bash
docker exec -i analytics_postgres psql -U analytics_user -d anti_procrastinacion \
  -f - < service/tests/fixtures/postgres_fixture.sql
```

---

## 4. Configurar el `.env` del servicio

Crear/editar `Analitycs/service/.env` (si no existe, copiar `.env.example`):

```bash
cd Analitycs/service
cp .env.example .env
```

Y completar (o pegar) estos valores mínimos para desarrollo local:

```dotenv
POSTGRES_HOST=localhost
POSTGRES_PORT=5433
POSTGRES_DB=anti_procrastinacion
POSTGRES_USER=analytics_user
POSTGRES_PASSWORD=changeme

REDIS_HOST=localhost
REDIS_PORT=6380
REDIS_DB=0

ENVIRONMENT=development

ADMIN_USERNAME=admin
ADMIN_PASSWORD_HASH=$2b$12$QjSwx0WpdMSXtA0.y3t2lO3zf8FslN7ZcZrdM8fI806uGY5sUu1T.

TEST_ADMIN_USER=tester
TEST_ADMIN_PASSWORD=Tester12345

DEFAULT_CLIENT_TIMEZONE=UTC

ETL_CACHE_INVALIDATION_SECRET=dev-only-secret-cambiar-en-produccion
```

> Con ese hash, la contraseña del admin real (`admin`) es **`Admin12345`**.
> El login de prueba (`tester`) usa **`Tester12345`**.

---

## 5. Crear entorno virtual e instalar dependencias

```bash
cd Analitycs/service
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## 6. Correr los tests (opcional, recomendado antes de levantar el servidor)

```bash
cd Analitycs/service
source .venv/bin/activate

# Rápido, con mocks (no requiere PostgreSQL/Redis)
python -m pytest tests -v -m "not postgres"

# Completo, incluyendo tests que consultan PostgreSQL real (requiere pasos 1-3 ya hechos)
python -m pytest tests -v
```

---

## 7. Levantar el servidor (Swagger UI)

```bash
cd Analitycs/service
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

Si preferís correrlo en background:

```bash
cd Analitycs/service
nohup .venv/bin/uvicorn app.main:app --port 8000 > /tmp/uvicorn.log 2>&1 & disown
```

Verificar que levantó:

```bash
curl -s http://localhost:8000/health
```

---

## 8. Abrir Swagger UI

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

### Flujo de prueba en Swagger:

1. Ejecutar `POST /api/admin/auth/test-login` con **Try it out**:
   ```json
   {
     "username": "tester",
     "password": "Tester12345",
     "timezone": "America/Argentina/Buenos_Aires"
   }
   ```
2. Copiar el `access_token` de la respuesta.
3. Click en **Authorize** 🔒 (arriba a la derecha), pegar:
   ```
   Bearer <access_token>
   ```
4. Ejecutar cualquier endpoint del tag `analytics` — debería responder `200` con datos reales.
5. Sin token, esos mismos endpoints responden `401`.

---

## 9. Probar endpoints por consola (alternativa a Swagger)

```bash
# 1) Obtener token
TOKEN=$(curl -s -X POST http://localhost:8000/api/admin/auth/test-login \
  -H "Content-Type: application/json" \
  -d '{"username":"tester","password":"Tester12345","timezone":"UTC"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# 2) Probar un endpoint protegido
curl -s http://localhost:8000/api/admin/analytics/users/total \
  -H "Authorization: Bearer $TOKEN"

curl -s http://localhost:8000/api/admin/analytics/apps/top5 \
  -H "Authorization: Bearer $TOKEN"

curl -s http://localhost:8000/api/admin/analytics/gender \
  -H "Authorization: Bearer $TOKEN"
```

---

## 9.5. Ver los datos de la base en tiempo real

### Opción A — Consola interactiva de psql dentro del contenedor

```bash
docker exec -it analytics_postgres psql -U analytics_user -d anti_procrastinacion
```

Una vez dentro, comandos útiles:

```sql
\dt                          -- listar tablas
\d dim_users                 -- ver estructura de una tabla
SELECT * FROM dim_users;     -- ver datos
SELECT * FROM fact_app_usage ORDER BY usage_date DESC LIMIT 20;
\watch 2                     -- re-ejecuta el último SELECT cada 2 segundos (live!)
\q                            -- salir
```

Ejemplo de "vista en vivo" (re-ejecuta la consulta cada 2s hasta que canceles con `Ctrl+C`):

```sql
SELECT * FROM fact_tasks ORDER BY task_id DESC LIMIT 10;
\watch 2
```

### Opción B — Un solo comando desde fuera del contenedor (sin entrar a psql)

```bash
docker exec -it analytics_postgres psql -U analytics_user -d anti_procrastinacion -c "SELECT * FROM dim_users;"
```

Para que se refresque solo, usá `watch` de Linux (fuera de psql):

```bash
watch -n 2 'docker exec analytics_postgres psql -U analytics_user -d anti_procrastinacion -c "SELECT * FROM fact_app_usage ORDER BY usage_date DESC LIMIT 10;"'
```

### Opción C — Cliente gráfico (DBeaver, TablePlus, pgAdmin, extensión de VS Code)

Conectate con estos datos (los mismos del `.env`):

| Campo    | Valor                  |
|----------|------------------------|
| Host     | `localhost`            |
| Puerto   | `5433`                 |
| Base     | `anti_procrastinacion` |
| Usuario  | `analytics_user`       |
| Password | (la que configuraste en `postgre.sql` / Docker) |

> 💡 Tip VS Code: instalá la extensión **PostgreSQL** (o **SQLTools**), creá una conexión con esos
> datos, y vas a poder navegar las tablas y ver los datos actualizándose sin usar la terminal.

### Ver los logs del contenedor en vivo (consultas que se ejecutan)

```bash
docker logs -f analytics_postgres
```

### Ver Redis en tiempo real (cache)

```bash
docker exec -it analytics_redis redis-cli
# dentro de redis-cli:
KEYS admin:analytics:*
MONITOR   # muestra cada comando que llega en vivo (Ctrl+C para salir)
```

---

## 10. Apagar todo al terminar

```bash
# Detener el servidor
pkill -f "uvicorn app.main"

# Detener los contenedores (conserva los datos)
cd Analitycs
docker compose down

# O eliminar también los datos (reinicio limpio la próxima vez)
docker compose down -v
```

---

## 🔁 Resumen — Comandos en orden (copiar/pegar todo junto)

```bash
# 1. Levantar infraestructura
cd Analitycs
POSTGRES_PORT=5433 REDIS_PORT=6380 docker compose up -d
sleep 5

# 2. Esquema + índices + datos de prueba
tail -n +18 postgre.sql | docker exec -i analytics_postgres psql -U analytics_user -d anti_procrastinacion
docker exec -i analytics_postgres psql -U analytics_user -d anti_procrastinacion -f - < indexes.sql
docker exec -i analytics_postgres psql -U analytics_user -d anti_procrastinacion -f - < service/tests/fixtures/postgres_fixture.sql

# 3. Entorno Python
cd service
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 4. Tests (opcional)
python -m pytest tests -v -m "not postgres"

# 5. Levantar servidor
uvicorn app.main:app --reload --port 8000
```

Luego abrir http://localhost:8000/docs y seguir el flujo de la sección 8.


# Ver todas las tablas
docker exec -it analytics_postgres psql -U analytics_user -d anti_procrastinacion -c "\dt"

# Ver usuarios
docker exec -it analytics_postgres psql -U analytics_user -d anti_procrastinacion -c "SELECT * FROM dim_users;"

# Ver actividad de usuarios
docker exec -it analytics_postgres psql -U analytics_user -d anti_procrastinacion -c "SELECT * FROM fact_user_activity;"

# Ver uso de apps
docker exec -it analytics_postgres psql -U analytics_user -d anti_procrastinacion -c "SELECT * FROM fact_app_usage;"

# Ver challenges
docker exec -it analytics_postgres psql -U analytics_user -d anti_procrastinacion -c "SELECT * FROM fact_challenges;"

# Ver tareas
docker exec -it analytics_postgres psql -U analytics_user -d anti_procrastinacion -c "SELECT * FROM fact_tasks;"

# Entrar en modo interactivo (para ir escribiendo consultas libremente)
docker exec -it analytics_postgres psql -U analytics_user -d anti_procrastinacion