
# Feature Specification: API de Reportes y Documentación Interactiva para el Panel de Administración

**Rama del Feature**: `001-reportes-fastapi`

**Creado**: 2026-09-07 (fusionado con `002-swagger-docs` el 2026-09-15)

**Estado**: Borrador

**Área de propiedad**: C — Notificaciones + Admin (componente `reportes-fastapi`)

**Comportamiento offline**: No aplica. Este es un módulo interno de solo administración, siempre
online; el Principio II (offline-first) de la constitución raíz rige exclusivamente para lo
personal del usuario final y no se hereda a este módulo.

**Modelo de datos**: No se modifica el esquema PostgreSQL ni se agregan estructuras de Redis
nuevas fuera de lo ya descripto. Este feature consume de solo lectura el esquema ya definido en
`postgre.sql` / `indexes.sql` (`dim_users`, `fact_user_activity`, `fact_app_usage`,
`fact_challenges`, `fact_tasks`, `fact_user_groups`), poblado nocturnamente por un proceso ETL
externo a este repo. Ninguna de las tablas `dim_*` / `fact_*` se escribe desde este módulo.
Además, este feature incorpora una capa de caché de solo lectura (Redis, read-through) delante de
PostgreSQL para servir los 13 reportes ya agregados; esta caché no reemplaza ni modifica el
esquema PostgreSQL, y se invalida tras cada corrida del ETL (ver FR-022). `indexes.sql` contiene
únicamente índices de PostgreSQL, no una tabla de caché. La documentación interactiva (Swagger
UI/OpenAPI) tampoco modifica ningún esquema; solo agrega metadatos sobre los endpoints ya
definidos.

**Entrada**: Descripción del usuario: "API de Reportes para el Panel de Administración — 13
reportes de solo lectura/agregación sobre PostgreSQL ya poblado por ETL, más autenticación propia
de administrador para el Panel Admin (React), sin tocar Firestore ni el esquema de datos." +
"Quiero que los endpoints se prueben con Swagger; al finalizar cada endpoint me debe dejar
probarlos con Swagger." (feature `002-swagger-docs`, fusionado aquí).

## Clarifications

### Sesión 2026-09-07 (API de reportes)

- Q: ¿Cómo se van a almacenar y gestionar las cuentas de administrador que usan el Panel Admin? (FR-020) → A: Un único administrador con credenciales fijas guardadas en variables de entorno (usuario y hash de contraseña).
- Q: ¿Cuánto tiempo debe durar la sesión/token de administrador antes de expirar automáticamente? → A: La sesión expira a las 00:00 (medianoche) del día en curso, sin importar la hora de login; el admin debe volver a autenticarse cada día.
- Q: ¿Cuál es la zona horaria de referencia para definir la medianoche (expiración de sesión) y para agrupar los filtros de período (diario/semanal/mensual)? → A: **[Reemplazado, ver entrada siguiente]** Se decidió inicialmente Argentina/UTC-3 fija, pero esta decisión fue revisada en una pregunta posterior de la misma sesión.
- Q: Al filtrar el reporte de usuarios por país (FR-015), dado que `dim_users` no tiene columna de región, ¿cómo se soporta el filtro por región? → A: No se soporta filtro por región; el endpoint solo admite filtro por país puntual (o sin filtro, para ver todos los países).
- Q: ¿Cuál es la zona horaria real a usar para la expiración de sesión (medianoche) y para agrupar los filtros de período? → A: No es una zona horaria fija del servidor; se usa la zona horaria vigente en el momento (la del cliente/admin al momento de la solicitud), no Argentina/UTC-3 fija como se había definido antes.
- Q: ¿Los 13 reportes se sirven calculando la agregación en cada request contra PostgreSQL, o existe una capa de caché de datos ya agregados? → A: Existe una capa de caché (Redis, read-through) que guarda el resultado ya calculado de cada reporte con un TTL; en cache-hit se devuelve el valor cacheado sin tocar PostgreSQL, en cache-miss se calcula contra PostgreSQL y se guarda en caché. La caché se invalida (todas las claves de reportes) después de cada corrida del ETL nocturno. `indexes.sql` sigue siendo solo índices sobre PostgreSQL, no una tabla de caché.
- Q: El código ya implementado (`analytics_service.py`, método `users_by_registration_period`) calcula los rangos de fecha usando UTC fijo, contradiciendo la decisión de zona horaria vigente del cliente. ¿Cuál prevalece? → A: Prevalece la especificación (zona horaria vigente del cliente/admin al momento de la solicitud); el código ya implementado que use UTC fijo (u otra zona fija) para filtros de período o expiración de sesión queda marcado como una discrepancia conocida a corregir durante `/plan`/`/implement`, no se revierte la spec.
- Q: El código ya implementado (`analytics_repository.py`, método `users_by_gender`) agrupa dinámicamente por el valor crudo de la columna `gender` (sin categorías fijas ni bucket "sin dato"), contradiciendo FR-014 que exige exactamente 3 categorías fijas ("Hombre", "Mujer", "No binario") + "sin dato". ¿Cuál prevalece? → A: Prevalece la especificación (3 categorías fijas + "sin dato"); el código ya implementado (`users_by_gender()`) queda marcado como una discrepancia conocida a corregir durante `/plan`/`/implement`, no se revierte la spec.
- Q: El código ya implementado (`analytics_service.py::tasks_summary`, `analytics_repository.py`) no soporta ningún filtro de estado y siempre calcula ambos promedios (todas + completadas) sin distinguir "no completadas", contradiciendo FR-009. ¿Cuál prevalece? → A: Prevalece la especificación (filtro de estado real: completadas/no completadas/todas); el código ya implementado queda marcado como una discrepancia conocida a corregir durante `/plan`/`/implement`, incluyendo agregar un método de repositorio para "no completadas" (`status != 'completed'`), no se revierte la spec.
- Q: El código ya implementado (`analytics_repository.py`, método `top_five_apps_by_screen_time`) no tiene ningún criterio de desempate secundario en su `ORDER BY`, contradiciendo el edge case que exige un desempate determinístico (ej. alfabético). ¿Cuál prevalece? → A: Prevalece la especificación (desempate determinístico); el código ya implementado queda marcado como una discrepancia conocida a corregir durante `/plan`/`/implement` (agregar `ORDER BY avg_minutes DESC, app_label ASC`), no se revierte la spec.
- Q: El código ya implementado (`analytics_router.py`) no valida rangos de edad inválidos en `/screen-time/age-range` (ejecuta la consulta tal cual) y responde 200 con `{"error": ...}` en el cuerpo cuando falta `period_key` en `/users/active`, en vez de 422, contradiciendo FR-019 y el edge case de validación de rango de edad. ¿Cuál prevalece? → A: Prevalece la especificación (422 con mensaje descriptivo ante filtros inválidos); el código ya implementado queda marcado como una discrepancia conocida a corregir durante `/plan`/`/implement` (agregar validación explícita de `min_age <= max_age`, valores no negativos, y `period_key` requerido/válido, respondiendo 422 en vez de 200), no se revierte la spec.
- Q: La spec nunca especifica los valores exactos de `fact_tasks.status`; el código asume implícitamente que "no completada" equivale al valor literal `pending`, en vez de "cualquier valor distinto de `completed`". ¿Cómo se documenta/resuelve? → A: Se documenta explícitamente en Supuestos que "no completadas" se define como `status != 'completed'` (más flexible/robusto que asumir un valor fijo `pending`); el filtro "no completadas" del endpoint de tareas debe usar esta definición, no un valor hardcodeado, y el código (`analytics_router.py`, mapeo `not-completed -> pending`) queda marcado como discrepancia conocida a corregir durante `/plan`/`/implement`.
- Q: El código ya implementado devuelve los 5 reportes de gráfico (top 5 apps, dispositivos, género, país, antigüedad de registro) como listas de objetos por ítem (formato "tabla cruda"), en vez de arrays paralelos `labels`/`values`, contradiciendo FR-016. ¿Cuál prevalece? → A: Prevalece la especificación (formato `labels`/`values`); los 5 endpoints ya implementados quedan marcados como discrepancia conocida a corregir durante `/plan`/`/implement` para transformar su respuesta al formato `{"labels": [...], "values": [...]}` (con arrays paralelos adicionales para datos como `percentage` cuando aplique), no se revierte la spec.

### Sesión 2026-09-08 (documentación interactiva Swagger)

- Q: ¿Qué alcance tiene "probar con Swagger": solo que la UI interactiva exista y liste los endpoints, o que cada endpoint sea efectivamente ejecutable ("Try it out") desde Swagger UI con respuestas reales del servicio (incluyendo, cuando aplique, autenticación de administrador)? → A: Debe ser completamente ejecutable ("Try it out") para cada endpoint, incluyendo poder autenticarse como administrador y usar esa sesión para probar los endpoints protegidos, no solo una lista de documentación estática.
- Q: El endpoint de login de administrador (FR-001/002/020) todavía no está implementado. ¿La documentación Swagger debe esperar a que ese login exista, o se agrega aquí un login propio? → A: Se agrega un login mínimo de administrador **exclusivamente para fines de prueba** (no forma parte del alcance final del proyecto); el proyecto final tendrá una sección separada de login/registro para usuarios finales, donde el administrador podrá registrarse. Este login de prueba es temporal y desacoplado de ese flujo final, solo para poder ejercitar la Historia de Usuario 6 desde Swagger UI mientras el login definitivo no exista.
- Q: FR-030 (ex FR-009 de `002-swagger-docs`) exige poder habilitar/deshabilitar Swagger UI según el entorno sin cambios de código, pero no existe hoy ningún mecanismo de configuración de entorno en el servicio (`config.py` no tiene un campo `environment`/`debug`). ¿Cómo se resuelve? → A: Se agrega un requisito explícito (FR-032): debe existir una variable de entorno configurable (ej. `ENVIRONMENT` o `ENABLE_DOCS`) que el servicio lea para decidir si expone la documentación interactiva, con un comportamiento seguro-por-defecto si no se especifica; el nombre exacto de la variable se define en `/plan`.
- Q: FR-031 (ex FR-010) exige un login de prueba con "credenciales fijas simples", pero no especifica si esas credenciales deben leerse de variables de entorno o pueden estar hardcodeadas en el código, dado que `config.py` no tiene ningún campo `admin_user`/`admin_password`. ¿Cómo se resuelve? → A: Las credenciales del login de prueba también DEBEN leerse de variables de entorno (ej. `TEST_ADMIN_USER`/`TEST_ADMIN_PASSWORD`), nunca hardcodeadas en el código, manteniendo consistencia con la buena práctica ya establecida de no hardcodear credenciales, aun siendo este login desechable/temporal.

## Escenarios de Usuario y Pruebas *(obligatorio)*

### Historia de Usuario 1 - Visión general de usuarios y actividad (Prioridad: P1)

Como administrador de la plataforma, quiero ver de un vistazo cuántos usuarios hay registrados en
total y cuántos están activos en distintos períodos (diario/semanal/mensual/total), para entender
la salud general de adopción y uso del producto sin necesidad de consultar la base de datos
manualmente.

**Por qué esta prioridad**: Es el indicador más básico y de mayor demanda para cualquier panel de
administración; sin autenticación y sin estos dos reportes (total de usuarios, usuarios activos)
el resto de los reportes carecen de contexto de referencia.

**Prueba Independiente**: Con el admin autenticado, se puede llamar al endpoint de conteo total de
usuarios y al de usuarios activos con cada valor de período soportado, y verificar que los números
devueltos coincidan con un conteo manual sobre `dim_users` y `fact_user_activity` para un dataset
de prueba conocido.

**Escenarios de Aceptación**:

1. **Dado** existen 100 filas en `dim_users`, **Cuando** el admin autenticado solicita el total de
   usuarios registrados, **Entonces** la API responde 100.
2. **Dado** 30 usuarios distintos tienen al menos un registro en `fact_user_activity` con
   `activity_date` dentro de los últimos 7 días, **Cuando** el admin solicita usuarios activos con
   filtro "semanal", **Entonces** la API responde 30.
3. **Dado** el admin solicita usuarios activos con filtro "total" (sin acotar fecha), **Cuando** se
   ejecuta la consulta, **Entonces** la API responde la cantidad de usuarios distintos con al menos un
   registro histórico en `fact_user_activity`.
4. **Dado** un usuario no autenticado (sin credenciales o token inválido), **Cuando** intenta
   acceder a cualquier endpoint de reportes, **Entonces** la API responde 401 y no expone ningún dato.

---

### Historia de Usuario 2 - Reportes demográficos y de engagement por usuario (Prioridad: P2)

Como administrador, quiero ver reportes agregados por características demográficas (edad, género,
país, dispositivo, antigüedad) y de engagement por usuario (tiempo en pantalla por rango de edad,
promedio de competencias y tareas por usuario), con los filtros correspondientes, para poder
segmentar la base de usuarios y detectar patrones de uso.

**Por qué esta prioridad**: Estos reportes dependen de que exista el reporte base de usuarios (US1)
pero agregan valor analítico más profundo; son el cuerpo principal del panel de reportes
demográficos que el admin usa para decisiones de producto.

**Prueba Independiente**: Con datos de prueba con edades, géneros, países y dispositivos conocidos, se
puede llamar a cada endpoint demográfico (rango de edad libre, género, país, dispositivo,
antigüedad, edad promedio) y verificar que los valores devueltos (promedios, conteos,
porcentajes) coincidan con el cálculo esperado manualmente, incluyendo el caso de valores `NULL`.

**Escenarios de Aceptación**:

1. **Dado** usuarios con edades entre 18 y 65 en `dim_users` y registros de tiempo de uso en
   `fact_app_usage`, **Cuando** el admin solicita el promedio de tiempo en pantalla filtrando por
   rango de edad 18-25, **Entonces** la API responde el promedio calculado solo sobre usuarios cuya
   edad está en ese rango.
2. **Dado** usuarios con `gender` en los valores soportados ("Hombre", "Mujer", "No binario",
   `NULL`), **Cuando** el admin solicita el reporte de porcentaje por género, **Entonces** la API
   devuelve un desglose fijo con exactamente esas 3 categorías (más "sin dato" para `NULL`) con
   sus porcentajes sumando 100% sobre la población considerada.
3. **Dado** el admin solicita el reporte de usuarios por país filtrando por un país puntual
   (ej. "Argentina"), **Cuando** se ejecuta la consulta, **Entonces** la API responde la cantidad de
   usuarios de ese país y su porcentaje respecto al total global de usuarios.
4. **Dado** el admin solicita el reporte de usuarios agrupados por antigüedad desde el registro
   con filtro "último mes", **Cuando** se ejecuta la consulta, **Entonces** la API responde una
   estructura de datos agrupada por bucket temporal (ej. por semana) lista para graficar como
   barras, cubriendo solo el rango solicitado.
5. **Dado** el admin solicita el promedio de tareas por usuario con filtro de estado
   "completadas", **Cuando** se ejecuta la consulta, **Entonces** la API responde tanto el promedio de
   tareas totales por usuario como el promedio de tareas completadas por usuario, calculado solo
   sobre las tareas cuyo estado coincide con el filtro donde aplique.

---

### Historia de Usuario 3 - Rankings y comparativas de competencias/apps (Prioridad: P3)

Como administrador, quiero ver rankings comparativos (top apps por tiempo en pantalla, total y
promedio de competencias por usuario, promedio de desafíos completados por usuario, total de
competencias), para identificar qué apps generan más consumo de tiempo y qué tan efectivo es el
sistema de desafíos/gamificación.

**Por qué esta prioridad**: Aporta valor analítico pero es menos crítico para la operación diaria del
admin que los conteos y filtros demográficos de US1/US2; puede entregarse en una iteración
posterior sin bloquear el valor ya entregado por las historias anteriores.

**Prueba Independiente**: Con datos de prueba de `fact_app_usage` y `fact_challenges` conocidos, se
puede llamar al endpoint de top 5 apps y verificar el orden y los valores promedio devueltos, y
llamar a los endpoints de competencias para verificar que el reporte de "promedio completadas por
usuario" (filtrado por `status = 'completed'`) sea explícitamente distinto del reporte de
"promedio total de competencias por usuario" (sin filtrar por estado).

**Escenarios de Aceptación**:

1. **Dado** existen registros de `fact_app_usage` para más de 5 apps distintas con distintos
   promedios de `minutes_used`, **Cuando** el admin solicita el top 5 de apps con mayor promedio de
   tiempo en pantalla, **Entonces** la API responde exactamente 5 apps ordenadas de mayor a menor
   promedio.
2. **Dado** existen registros en `fact_challenges` con distintos valores de `status`, **Cuando** el
   admin solicita el promedio de competencias por usuario (reporte general, sin filtro de estado)
   y por separado el promedio de desafíos completados por usuario (`status = 'completed'`),
   **Entonces** la API devuelve dos valores distintos y claramente etiquetados que no se pueden
   confundir entre sí.
3. **Dado** el admin solicita la cantidad total de competencias, **Cuando** se ejecuta la consulta,
   **Entonces** la API responde el conteo total de filas en `fact_challenges` sin filtrar por usuario
   ni estado.

---

### Historia de Usuario 4 - Explorar y entender los endpoints disponibles (Prioridad: P1)

Como desarrollador o QA del equipo, quiero abrir una URL de documentación interactiva (Swagger UI)
y ver listados todos los endpoints del servicio de reportes, agrupados de forma clara, con la
descripción de sus parámetros, tipos de respuesta y códigos HTTP posibles, para poder entender
rápidamente qué hace cada endpoint sin leer el código fuente.

**Por qué esta prioridad**: Es el valor mínimo indispensable de la documentación: sin esto no hay
forma de descubrir la API de forma autoguiada. Habilita al resto de las historias de
documentación.

**Prueba independiente**: Se puede probar completamente abriendo la URL de Swagger UI del
servicio y verificando visualmente que aparecen todos los endpoints esperados, agrupados por
sección (usuarios, tareas, competencias, dispositivos, etc.), con sus parámetros documentados.

**Escenarios de Aceptación**:

1. **Dado** que el servicio de reportes está corriendo, **Cuando** un desarrollador abre la URL
   de documentación interactiva en el navegador, **Entonces** ve una página de Swagger UI con
   todos los endpoints del servicio listados y agrupados por categoría.
2. **Dado** que el desarrollador está viendo la documentación, **Cuando** expande un endpoint
   cualquiera, **Entonces** ve sus parámetros de entrada (query params, body si aplica), los
   posibles códigos de respuesta HTTP, y un ejemplo del cuerpo de respuesta.

---

### Historia de Usuario 5 - Ejecutar (probar) cualquier endpoint directamente desde Swagger (Prioridad: P1)

Como desarrollador o QA, quiero poder presionar "Try it out", completar los parámetros necesarios
y ejecutar cualquier endpoint directamente desde la misma página de Swagger UI, para verificar su
comportamiento real contra el servicio corriendo, sin necesidad de usar herramientas externas
(Postman, curl, etc.).

**Por qué esta prioridad**: Es el requisito explícito del usuario ("al finalizar cada endpoint me
debe dejar probarlos con Swagger"); sin ejecución real, la documentación es solo referencia
pasiva y no cumple el objetivo de "probar".

**Prueba independiente**: Se puede probar completamente seleccionando cualquier endpoint en
Swagger UI, presionando "Try it out", completando los parámetros de ejemplo, ejecutando la
solicitud, y verificando que la respuesta real (código HTTP + cuerpo JSON) se muestra en la misma
página.

**Escenarios de Aceptación**:

1. **Dado** un endpoint público (que no requiere sesión de administrador, si existiera alguno),
   **Cuando** el usuario presiona "Try it out", completa los parámetros y ejecuta, **Entonces**
   Swagger UI muestra la respuesta real del servicio (código HTTP y cuerpo) sin errores de CORS
   ni de conexión.
2. **Dado** un endpoint protegido por sesión de administrador, **Cuando** el usuario aún no se
   autenticó, **Entonces** al ejecutar recibe una respuesta 401 visible en Swagger UI (no un
   error de red opaco), consistente con el comportamiento real de la API.
3. **Dado** que el usuario ya se autenticó (ver Historia de Usuario 6) desde la misma página,
   **Cuando** ejecuta un endpoint protegido con "Try it out", **Entonces** la sesión obtenida se
   adjunta automáticamente a la solicitud y el endpoint responde con datos reales (200 con el
   reporte correspondiente), no 401.

---

### Historia de Usuario 6 - Autenticarse como administrador desde la misma documentación (Prioridad: P2)

Como desarrollador o QA, quiero poder ejecutar el endpoint de login de administrador desde
Swagger UI y que la credencial de sesión resultante quede disponible para probar automáticamente
el resto de los endpoints protegidos, sin tener que copiar/pegar manualmente un token en cada
solicitud.

**Por qué esta prioridad**: Mejora significativamente la experiencia de prueba end-to-end, pero
la Historia de Usuario 5 ya es parcialmente utilizable (para endpoints sin protección o pegando
el token a mano) sin esta historia, por eso es P2.

**Prueba independiente**: Se puede probar completamente ejecutando el endpoint de login con
credenciales válidas desde Swagger UI, usando el botón de autorización (candado) para cargar la
credencial de sesión obtenida, y luego verificando que un endpoint protegido devuelve 200 al
ejecutarse sin pasos manuales adicionales.

**Escenarios de Aceptación**:

1. **Dado** que el usuario conoce las credenciales de administrador de prueba, **Cuando**
   ejecuta el endpoint de login desde Swagger UI con "Try it out", **Entonces** recibe la
   credencial de sesión en la respuesta.
2. **Dado** que el usuario obtuvo una credencial de sesión, **Cuando** la carga en el mecanismo
   de autorización de Swagger UI (ej. botón "Authorize"), **Entonces** todas las solicitudes
   posteriores hechas desde "Try it out" incluyen automáticamente esa credencial (ej. header
   `Authorization`), sin que el usuario deba pegarla en cada endpoint por separado.
3. **Dado** que la sesión cargada expiró (ver FR-002, expiración a medianoche), **Cuando** el
   usuario ejecuta cualquier endpoint protegido desde Swagger UI, **Entonces** recibe 401 de
   forma visible, indicando que debe volver a autenticarse y recargar la credencial de sesión en
   el mecanismo de autorización.

---

### Casos Límite

- ¿Qué sucede si el rango de edad libre ingresado por el admin es inválido (mínimo mayor que
  máximo, o valores negativos)? El sistema debe responder 422 con un mensaje claro, sin exponer
  detalles internos.
  **Discrepancia conocida**: el endpoint `/screen-time/age-range` en
  `service/app/routers/analytics_router.py` actualmente no valida `min_age`/`max_age` (ejecuta la
  consulta SQL tal cual, sin chequear `min_age <= max_age` ni valores negativos). Prevalece esta
  especificación; debe corregirse durante `/plan`/`/implement` agregando la validación y la
  respuesta 422 correspondiente.
- ¿Cómo se comporta el promedio de tiempo en pantalla por rango de edad si no hay ningún usuario
  con edad en ese rango o con datos de uso? El sistema debe responder un resultado vacío/0
  explícito, nunca un error, y distinguir "sin datos" de "promedio 0".
- ¿Cómo se tratan los usuarios con `age`, `gender` o `country` en `NULL` al calcular promedios y
  porcentajes? Deben excluirse del cálculo de promedio/porcentaje pero visibilizarse aparte como
  categoría "sin dato" cuando el reporte es de tipo distribución (género, país), para que el admin
  entienda que la suma de categorías puede no cubrir el 100% de la población si se excluyen del
  numerador pero sí del denominador reportado. *(Ver sección Supuestos para el detalle completo.)*
- ¿Qué pasa si el admin filtra por un país que no tiene ningún usuario asociado? El sistema debe
  responder 0 usuarios y 0% sin error.
- ¿Qué pasa si dos o más apps empatan en promedio de tiempo en pantalla al calcular el top 5? El
  sistema debe aplicar un criterio de desempate determinístico (ej. orden alfabético del nombre de
  app) para que la respuesta sea estable entre llamadas.
  **Discrepancia conocida**: `top_five_apps_by_screen_time()` en
  `service/app/repositories/analytics_repository.py` actualmente solo tiene
  `ORDER BY avg_minutes DESC LIMIT 5`, sin desempate secundario. Prevalece esta especificación;
  debe corregirse durante `/plan`/`/implement` agregando `ORDER BY avg_minutes DESC, app_label ASC`
  (o `package_name ASC`) para garantizar un orden determinístico.
- ¿Qué pasa si las credenciales de administrador son incorrectas repetidas veces? El sistema debe
  responder 401 de forma consistente sin revelar si el usuario existe o no, sin bloqueos de cuenta
  fuera de alcance de esta especificación.
- ¿Qué pasa si un token/sesión de administrador expiró (incluyendo la expiración automática a
  las 00:00)? El sistema debe responder 401 y el Panel Admin debe poder distinguir esto de
  credenciales inválidas para redirigir a un nuevo login.
- ¿Qué pasa si Swagger UI está deshabilitado o inaccesible en un entorno de producción? Debe
  seguir existiendo la posibilidad de habilitarlo explícitamente en entornos de desarrollo/QA sin
  requerir cambios de código, y estar deshabilitado o protegido en producción según se defina en
  `/plan` (fuera del alcance de negocio decidir esto en detalle aquí).
- ¿Qué pasa si un endpoint nuevo se agrega al servicio sin documentar sus parámetros? Debe
  aparecer igual en Swagger UI (por generación automática desde el framework), aunque con
  descripciones mínimas; no debe romper la carga de la página de documentación.
- ¿Qué pasa si el usuario intenta ejecutar un endpoint con parámetros inválidos desde "Try it
  out"? Debe mostrar la respuesta real de error (422) del servicio, igual que si se llamara desde
  cualquier otro cliente HTTP.
- ¿Qué pasa si dos personas prueban simultáneamente desde distintas pestañas/navegadores con
  distintas sesiones de administrador? Dado que solo existe una cuenta de administrador (ver
  FR-020), ambas sesiones son válidas de forma independiente mientras no expiren; no hay conflicto
  de datos porque los endpoints son de solo lectura.

## Requisitos *(obligatorio)*

### Requisitos Funcionales — API de Reportes

- **FR-001**: El sistema DEBE proveer un endpoint de login para administradores que reciba usuario
  y contraseña y devuelva una credencial de sesión (token) reutilizable en el resto de los
  endpoints de reportes.
- **FR-002**: El sistema DEBE exigir una credencial de sesión de administrador válida para acceder
  a cualquier endpoint de reportes; las solicitudes sin credencial válida DEBEN responder 401.
  La sesión/token emitido en el login DEBE expirar automáticamente a las 00:00 (medianoche) del
  día en curso **según la zona horaria vigente del cliente/admin al momento de la solicitud**
  (no una zona horaria fija del servidor), independientemente de la hora en que se haya iniciado
  sesión; una vez expirada, el sistema DEBE responder 401 y el admin DEBE volver a autenticarse
  para obtener una nueva sesión válida para el nuevo día. El mecanismo exacto para que el cliente
  comunique su zona horaria vigente (ej. header HTTP, parámetro de login) se define durante
  `/plan`.
- **FR-003**: El sistema DEBE proveer un endpoint que devuelva la cantidad total de usuarios
  registrados en `dim_users`.
- **FR-004**: El sistema DEBE proveer un endpoint que devuelva la cantidad de usuarios activos
  (al menos 1 registro en `fact_user_activity` en el período), soportando filtro de período:
  diario, semanal, mensual y total (sin acotar).
- **FR-005**: El sistema DEBE proveer un endpoint que devuelva el promedio de tiempo en pantalla
  (a partir de `fact_app_usage.minutes_used`) filtrando por un rango de edad libre (mínima y
  máxima) ingresado por el admin.
- **FR-006**: El sistema DEBE proveer un endpoint que devuelva el promedio de cantidad de
  competencias (`fact_challenges`) por usuario, sin filtrar por estado.
- **FR-007**: El sistema DEBE proveer un endpoint que devuelva la cantidad total de competencias
  registradas en `fact_challenges`.
- **FR-008**: El sistema DEBE proveer un endpoint que devuelva el top 5 de apps con mayor promedio
  de tiempo en pantalla, a partir de `fact_app_usage`, agrupado por app.
- **FR-009**: El sistema DEBE proveer un endpoint que devuelva, en una misma respuesta, el
  promedio de tareas por usuario y el promedio de tareas realizadas (completadas) por usuario,
  soportando un filtro de estado (completadas / no completadas / todas) que determina qué
  subconjunto de `fact_tasks` se usa para cada cálculo.
  **Discrepancia conocida**: `AnalyticsService.tasks_summary()` (en
  `service/app/services/analytics_service.py`) actualmente no recibe ningún parámetro de filtro
  y siempre calcula ambos promedios sobre todas las tareas y sobre las completadas; además
  `AnalyticsRepository` no tiene un método para el promedio de tareas **no completadas** por
  usuario. Prevalece esta especificación; durante `/plan`/`/implement` se debe: (a) agregar el
  parámetro de filtro de estado a `tasks_summary`, y (b) agregar el método de repositorio
  correspondiente para "no completadas" (`status != 'completed'`, no un valor literal fijo como
  `'pending'` — ver también el mapeo hardcodeado en `analytics_router.py::tasks_by_status`, que
  también debe corregirse para usar `!= 'completed'` en vez de asumir `'pending'`).
- **FR-010**: El sistema DEBE proveer un endpoint que devuelva la cantidad de usuarios agrupados
  por `dim_users.device`.
- **FR-011**: El sistema DEBE proveer un endpoint que devuelva usuarios agrupados por antigüedad
  desde `dim_users.registered_at`, en un formato listo para graficar como barras, soportando
  filtro de rango temporal (última semana, último mes, último año, u otro rango equivalente).
- **FR-012**: El sistema DEBE proveer un endpoint que devuelva el promedio de edad de los usuarios
  (`dim_users.age`), excluyendo del cálculo los valores `NULL`.
- **FR-013**: El sistema DEBE proveer un endpoint que devuelva el promedio de desafíos
  **completados** por usuario (`fact_challenges` con `status = 'completed'`), claramente
  diferenciado del reporte de FR-006.
- **FR-014**: El sistema DEBE proveer un endpoint que devuelva el porcentaje de usuarios por
  género (`dim_users.gender`), calculado sobre un conjunto **fijo y hardcodeado** de 3 categorías
  soportadas: "Hombre", "Mujer" y "No binario", más una categoría adicional "sin dato" para los
  registros con `gender` en `NULL` o con un valor que no coincida exactamente con las 3
  categorías soportadas.
  **Discrepancia conocida**: el método `users_by_gender()` en
  `service/app/repositories/analytics_repository.py` actualmente agrupa dinámicamente por el
  valor crudo de la columna `gender` (sin categorías fijas ni bucket "sin dato"). Prevalece esta
  especificación; el método debe corregirse durante `/plan`/`/implement` para forzar el
  agrupamiento a las 3 categorías fijas + "sin dato".
- **FR-015**: El sistema DEBE proveer un endpoint que devuelva el porcentaje de usuarios por país
  (`dim_users.country`), soportando filtro **únicamente por país puntual** (no por región, ya que
  el esquema de `dim_users` no tiene columna de región); si no se envía filtro, la respuesta
  cubre todos los países presentes en los datos. Cuando el filtro es un país puntual, la
  respuesta DEBE incluir tanto la cantidad de usuarios de ese país como su porcentaje respecto al
  total global de usuarios.
- **FR-016**: Los endpoints pensados para graficar (barras/torta: usuarios por antigüedad, top 5
  apps, porcentaje por género, porcentaje por país, usuarios por dispositivo) DEBEN devolver los
  datos en un formato de "labels + values" ya listo para renderizar un gráfico, en vez de tablas
  crudas.
  **Discrepancia conocida**: los 5 endpoints ya implementados (`top_five_apps`, `users_by_device`,
  `users_by_gender`, `users_by_country`, `users_by_registration_period` en
  `service/app/services/analytics_service.py`) actualmente devuelven listas de objetos por ítem
  (formato tabla cruda), no arrays paralelos `labels`/`values`. Prevalece esta especificación;
  deben corregirse durante `/plan`/`/implement` para responder `{"labels": [...], "values": [...]}`
  (con arrays paralelos adicionales para datos secundarios como `percentage` cuando aplique).
- **FR-017**: El sistema DEBE responder únicamente con datos que, en última instancia, provienen
  de PostgreSQL (tablas `dim_*`/`fact_*` ya definidas), ya sea leídos directamente o servidos
  desde la capa de caché descripta en FR-022; ningún endpoint de este feature DEBE leer de
  Firestore en tiempo real ni escribir sobre las tablas `dim_*`/`fact_*`.
- **FR-018**: Todos los endpoints de este feature DEBEN responder JSON consistente y usar códigos
  HTTP semánticos (401 sin credencial válida, 403 si aplica un caso de autorización insuficiente,
  404 si un recurso solicitado no existe, 422 ante parámetros de filtro inválidos, 500 ante
  errores no controlados), y en ningún caso DEBEN exponer detalles internos (stack traces, nombres
  de tablas, mensajes de error de la base de datos) en la respuesta al cliente.
- **FR-019**: El sistema DEBE validar parámetros de filtro (rangos de edad, rangos temporales,
  valores de período/estado) antes de ejecutar la consulta agregada, respondiendo 422 con un
  mensaje descriptivo si el filtro es inválido (ej. edad mínima mayor que máxima).
  **Discrepancia conocida**: en `service/app/routers/analytics_router.py`, el endpoint
  `/screen-time/age-range` no valida `min_age`/`max_age` antes de ejecutar la consulta, y el
  endpoint `/users/active` responde 200 con `{"error": "period_key es requerido..."}` en el
  cuerpo (en vez de 422) cuando falta `period_key`. Prevalece esta especificación; ambos casos
  deben corregirse durante `/plan`/`/implement` para responder 422 de forma consistente.
- **FR-020**: El sistema de autenticación de administrador DEBE basarse en una **única cuenta de
  administrador con credenciales fijas** (usuario y contraseña) configuradas mediante variables de
  entorno del servicio; la contraseña DEBE almacenarse siempre hasheada (nunca en texto plano),
  y el sistema DEBE validar el login comparando contra el hash correspondiente. No existe una
  tabla de administradores en PostgreSQL ni soporte para múltiples cuentas de administrador en
  esta iteración.
- **FR-021**: Todos los reportes con filtro de período (diario/semanal/mensual/último mes/último
  año, etc.) DEBEN agrupar y calcular los rangos de fecha usando **la zona horaria vigente del
  cliente/admin al momento de la solicitud** (no una zona horaria fija del servidor), de forma
  consistente con la zona horaria usada para la expiración de sesión (FR-002).
  **Discrepancia conocida**: la implementación actual de `users_by_registration_period` en
  `analytics_service.py` usa UTC fijo (`dt.datetime.now(dt.timezone.utc)`); esto DEBE corregirse
  durante `/plan`/`/implement` para aceptar y usar la zona horaria vigente del cliente, no
  revertir este requisito.
- **FR-022**: El sistema DEBE servir los 13 reportes a través de una capa de caché de solo
  lectura (read-through) previa a PostgreSQL: en un acierto de caché ("cache-hit") DEBE devolver
  el valor ya agregado sin ejecutar la consulta contra PostgreSQL; en un fallo de caché
  ("cache-miss") DEBE calcular el resultado contra PostgreSQL, guardarlo en la caché con un
  tiempo de vida (TTL) definido según la naturaleza del reporte (reportes de alta variabilidad,
  ej. usuarios activos por día, con TTL corto; reportes de distribución que cambian poco, ej.
  género o país, con TTL más largo), y devolverlo. El proceso ETL nocturno DEBE invalidar
  explícitamente (push directo, no solo esperar la expiración natural del TTL) todas las claves
  de caché de reportes inmediatamente al finalizar cada corrida, de modo que ningún reporte
  muestre datos de más de un ciclo ETL de antigüedad. Las tablas/índices definidos en
  `indexes.sql` son exclusivamente índices de PostgreSQL y no forman parte de esta capa de
  caché.

### Requisitos Funcionales — Documentación Interactiva (Swagger)

- **FR-023**: El sistema DEBE exponer una página de documentación interactiva (Swagger UI) en una
  URL conocida y accesible mientras el servicio esté corriendo en entornos de desarrollo/QA.
- **FR-024**: La página de documentación interactiva DEBE listar automáticamente todos los
  endpoints expuestos por el servicio de reportes (los 13 reportes más el endpoint de login de
  administrador), agrupados por categoría/tag, sin requerir mantenimiento manual de una lista
  separada.
- **FR-025**: Cada endpoint listado DEBE mostrar, como mínimo: método HTTP, ruta, parámetros de
  entrada esperados (query params y/o cuerpo), los códigos de respuesta HTTP posibles, y un
  ejemplo de la estructura de la respuesta exitosa.
- **FR-026**: El sistema DEBE permitir ejecutar ("Try it out") cualquier endpoint directamente
  desde la página de documentación interactiva, contra la instancia real del servicio en
  ejecución, mostrando la respuesta real (código HTTP + cuerpo) en la misma página.
- **FR-027**: El sistema DEBE proveer, dentro de la misma página de documentación interactiva, un
  mecanismo para que el usuario cargue la credencial de sesión de administrador obtenida del
  endpoint de login (ej. mediante el botón "Authorize" estándar de Swagger UI), de forma que las
  ejecuciones posteriores de endpoints protegidos incluyan automáticamente esa credencial sin
  intervención manual adicional por solicitud.
- **FR-028**: Al ejecutar desde "Try it out" un endpoint protegido sin una credencial de sesión
  válida cargada, el sistema DEBE mostrar en la página de documentación la respuesta real 401 del
  servicio (no un error genérico de red ni de CORS).
- **FR-029**: Al ejecutar desde "Try it out" un endpoint con parámetros inválidos, el sistema
  DEBE mostrar la respuesta real de error (422) del servicio, igual que a través de cualquier
  otro cliente HTTP.
- **FR-030**: La documentación interactiva NO DEBE requerir edición manual duplicada cada vez que
  se agregue, modifique o elimine un endpoint del servicio; debe reflejar automáticamente los
  endpoints existentes en cada momento.
- **FR-031**: Dado que el login de administrador definitivo (FR-001/002/020) puede no estar
  implementado al momento de ejecutar la documentación interactiva, el sistema DEBE proveer un
  endpoint de login de administrador **mínimo y exclusivamente de prueba** (credenciales fijas
  simples leídas de variables de entorno dedicadas —p. ej. `TEST_ADMIN_USER`/
  `TEST_ADMIN_PASSWORD`—, nunca hardcodeadas en el código, aunque sin necesariamente cumplir
  todos los demás requisitos de seguridad de FR-020, como el hasheo de contraseña), únicamente
  para poder emitir una credencial de sesión utilizable en el mecanismo "Authorize" de Swagger UI
  y así ejercitar la Historia de Usuario 6. Este endpoint de prueba: (a) NO forma parte del
  alcance final del proyecto, (b) NO reemplaza ni debe confundirse con el login definitivo de
  administrador (FR-001/002/020) ni con la sección de login/registro de usuarios finales del
  proyecto final (donde el administrador podrá registrarse), y (c) DEBE quedar claramente
  identificado (ej. en su descripción/tag en Swagger UI) como "solo para pruebas", para que no se
  use por error como mecanismo de autenticación de producción.
- **FR-032**: El sistema DEBE leer de una variable de entorno (ej. `ENVIRONMENT` o
  `ENABLE_DOCS`), configurable sin cambios de código, el valor que determina si la documentación
  interactiva (Swagger UI) y su documento OpenAPI subyacente quedan expuestos o no; por defecto,
  en ausencia de configuración explícita, el sistema DEBE comportarse de forma seguro-por-defecto
  (ej. expuesto en desarrollo, oculto si no se especifica el entorno como desarrollo/QA).

### Entidades Clave

- **Administrador (Admin)**: Cuenta única e interna que usa el Panel Admin, definida vía
  variables de entorno del servicio (usuario + hash de contraseña), sin persistencia en
  PostgreSQL. No se relaciona con `dim_users` (que representa usuarios finales de la app, no
  administradores).
- **Usuario final (proyección de lectura de `dim_users`)**: Perfil demográfico y de registro de
  cada usuario de la app (edad, género, país, dispositivo, fecha de registro). Es la entidad base
  sobre la que se calculan casi todos los reportes.
- **Actividad diaria (proyección de lectura de `fact_user_activity`)**: Un registro por usuario y
  día en que hubo actividad; base del cálculo de "usuarios activos".
- **Uso de apps (proyección de lectura de `fact_app_usage`)**: Minutos de uso por usuario, día y
  app; base del cálculo de tiempo en pantalla y del ranking de apps.
- **Competencia/Desafío (proyección de lectura de `fact_challenges`)**: Desafío en el que participa
  un usuario, con estado (`active`/`completed`/`expired`); base de los reportes de competencias.
- **Tarea (proyección de lectura de `fact_tasks`)**: Tarea de un usuario con estado
  (`pending`/`completed`/etc.); base del reporte de tareas por usuario.
- **Reporte**: Resultado agregado (conteo, promedio, porcentaje, o serie de labels+values)
  producido por un endpoint de este feature a partir de una o más de las entidades anteriores,
  con los filtros que correspondan según el punto de la lista de alcance.
- **Entrada de caché de reporte**: Copia temporal (con TTL) del resultado ya calculado de un
  reporte, almacenada en Redis y servida en lugar de recalcular contra PostgreSQL; no es una
  fuente de verdad, se invalida completamente tras cada corrida del ETL nocturno (ver FR-022).
- **Documento OpenAPI**: Descripción estructurada (generada automáticamente por el framework del
  servicio) de todos los endpoints, sus parámetros, tipos de datos y respuestas posibles; es la
  fuente que consume Swagger UI para renderizarse.
- **Sesión de administrador (de prueba o definitiva)**: Credencial obtenida del endpoint de login
  (temporal de pruebas, FR-031, o definitivo, FR-001/002/020, según cuál esté disponible),
  cargada en el mecanismo de autorización de Swagger UI para probar endpoints protegidos sin
  pasos manuales adicionales.

## Criterios de Éxito *(obligatorio)*

### Resultados Medibles — API de Reportes

- **SC-001**: El administrador puede autenticarse y obtener acceso a los 13 reportes en menos de
  10 segundos desde el login exitoso.
- **SC-002**: Cada uno de los 13 reportes definidos en el alcance responde con datos correctos y
  consistentes con el estado de PostgreSQL en el 100% de los casos verificados contra un dataset
  de prueba conocido (sin discrepancias respecto al cálculo manual esperado).
- **SC-003**: El 100% de las solicitudes sin credencial de administrador válida son rechazadas
  (401) sin exponer ningún dato de reporte.
- **SC-004**: El 100% de las solicitudes con parámetros de filtro inválidos (rangos de edad
  inválidos, valores de período/estado no soportados) reciben una respuesta 422 con mensaje claro,
  sin provocar errores 500 ni caídas del servicio.
- **SC-005**: Ningún endpoint de este feature modifica ninguna fila de las tablas `dim_*`/`fact_*`;
  esto es verificable comparando un snapshot de la base antes y después de ejercitar todos los
  endpoints.
- **SC-006**: Los reportes marcados como "para graficar" (top apps, antigüedad, género, país,
  dispositivo) llegan al Panel Web en un formato que este puede renderizar directamente como
  gráfico de barras o torta sin transformación adicional de estructura de datos.
- **SC-007**: El 100% de las sesiones de administrador dejan de ser válidas después de las 00:00
  (según la zona horaria vigente del cliente/admin al momento de la solicitud) del día en que
  fueron emitidas, sin importar la hora de login; una solicitud realizada con una sesión de un
  día anterior (en esa misma zona horaria) es rechazada (401) en el 100% de los casos
  verificados.
- **SC-008**: Ningún reporte muestra datos con más de un ciclo ETL de antigüedad; el 100% de las
  claves de caché de reportes quedan invalidadas dentro de los primeros minutos posteriores a la
  finalización de cada corrida del ETL, verificable comparando el resultado de un reporte antes y
  después de una corrida de prueba del ETL con datos nuevos.

### Resultados Medibles — Documentación Interactiva

- **SC-009**: Un desarrollador o QA que nunca vio el código puede, únicamente con la URL de
  Swagger UI, identificar los 13 reportes y el endpoint de login, y describir correctamente sus
  parámetros de entrada, en menos de 5 minutos.
- **SC-010**: El 100% de los endpoints del servicio de reportes pueden ejecutarse exitosamente
  ("Try it out") desde Swagger UI y devolver la misma respuesta que se obtendría llamándolos con
  cualquier otro cliente HTTP (ej. `curl`), para el mismo conjunto de parámetros.
- **SC-011**: Un usuario puede autenticarse y probar un endpoint protegido completo (login +
  carga de sesión + ejecución de un reporte protegido) sin salir de la página de Swagger UI ni
  usar herramientas externas, en menos de 2 minutos.
- **SC-012**: Agregar un endpoint nuevo al servicio no requiere ninguna edición manual adicional
  en un archivo de documentación separado para que aparezca en Swagger UI; aparece
  automáticamente tras reiniciar el servicio.

## Supuestos

- El Panel Admin (React) es el único consumidor de esta API; no hay otros clientes previstos en
  esta iteración.
- El almacenamiento de credenciales de administrador vive dentro del alcance de este módulo (no
  depende de Firebase Auth, que es exclusivo de usuarios finales); el mecanismo exacto (cuenta
  única con credenciales en variables de entorno, contraseña hasheada) y la duración de sesión
  (expiración a las 00:00 del día en curso) se definieron en la sesión de clarificación del
  2026-09-07 (ver FR-002 y FR-020).
- La zona horaria de referencia para agrupar `activity_date`, `usage_date` y `registered_at` en
  los filtros por período (diario/semanal/mensual/último mes/último año), así como para la
  expiración de sesión de administrador, **no es fija**: se usa la zona horaria vigente del
  cliente/admin al momento de la solicitud, según se redefinió en la sesión de clarificación del
  2026-09-07 (ver FR-002 y FR-021). El mecanismo exacto por el cual el cliente comunica su zona
  horaria (ej. header HTTP, parámetro en el login) se define durante `/plan`.
- El reporte de usuarios por país (FR-015) no soporta filtro por región; solo admite filtro por
  país puntual o ausencia de filtro (todos los países), ya que el esquema de `dim_users` no
  cuenta con una columna o tabla de región, según se definió en la sesión de clarificación del
  2026-09-07.
- Para los cálculos de promedio y porcentaje, los registros con `age`, `gender` o `country` en
  `NULL` se excluyen del numerador del cálculo, pero los reportes de tipo distribución (género,
  país) exponen una categoría explícita "sin dato" en vez de omitir silenciosamente esos usuarios,
  de modo que el admin pueda ver cuántos registros carecen de ese dato.
- Los reportes que devuelven listas potencialmente grandes (ej. usuarios por país si hay muchos
  países distintos) no requieren paginación en esta primera iteración porque el número de valores
  distintos de país/dispositivo/género es acotado en la práctica (decenas, no miles); si el volumen
  real supera lo esperado, se revisará en una iteración posterior.
- El formato exacto (shape del JSON) de cada uno de los 13 endpoints se define en detalle durante
  `/plan`, respetando el principio general de este spec: "labels + values" para reportes de
  gráfico, valores agregados simples para el resto.
- No hay requisito de autorización granular por rol (todos los administradores autenticados tienen
  acceso a todos los reportes); si en el futuro se necesitan roles distintos, será una extensión
  posterior fuera de este alcance.
- Los 13 reportes se sirven mediante una capa de caché de solo lectura (Redis, read-through) que
  guarda cada resultado ya agregado con un TTL diferenciado según la variabilidad del reporte.
- El framework HTTP usado por el servicio (FastAPI) genera automáticamente el documento OpenAPI y
  expone Swagger UI de forma nativa; la documentación interactiva se apoya en esa capacidad nativa
  en vez de construir una solución de documentación desde cero.
- El mecanismo de autorización de Swagger UI (botón "Authorize") es suficiente para cumplir el
  requisito de "cargar la sesión una vez y probar el resto de los endpoints"; no se requiere un
  flujo de autenticación visual adicional fuera de lo que Swagger UI ofrece por defecto.
- El nombre exacto de la variable de entorno (ej. `ENVIRONMENT`, `ENABLE_DOCS`), sus valores
  posibles, y el comportamiento seguro-por-defecto exacto se definen con precisión durante
  `/plan` (ver FR-032); lo que este spec fija como requisito de negocio es que dicho control
  exista y sea configurable sin cambios de código, no el nombre/formato literal de la variable.
- La documentación interactiva no introduce nuevos endpoints de negocio; únicamente garantiza que
  los endpoints ya definidos en este mismo feature sean descubribles y ejecutables desde Swagger
  UI.
- El endpoint de login de administrador de prueba (FR-031) es **estrictamente temporal y de
  alcance de prueba**: no forma parte de la versión final del proyecto. El proyecto final NO
  contempla login/registro en este módulo de reportes; existe una sección separada del sistema
  (fuera de este repo/módulo) donde los usuarios finales inician sesión y donde el administrador
  podrá registrarse. Este login de prueba se retira o se reemplaza cuando ese flujo definitivo
  esté disponible, sin que su existencia temporal condicione el diseño final de autenticación del
  proyecto.
  