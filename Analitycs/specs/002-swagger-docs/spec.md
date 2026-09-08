
# Feature Specification: Documentación Interactiva Swagger para la API de Reportes

**Rama del Feature**: `002-swagger-docs`

**Creado**: 2026-09-08

**Estado**: Borrador

**Área de propiedad**: C — Notificaciones + Admin (componente `reportes-fastapi`)

**Comportamiento offline**: No aplica. Este feature es de soporte a desarrollo/QA sobre un módulo
interno de administración, siempre online.

**Modelo de datos**: No se modifica ningún esquema. Este feature no agrega, cambia ni elimina
tablas de PostgreSQL ni estructuras de Redis; únicamente agrega/mejora metadatos de
documentación (OpenAPI) sobre los endpoints ya definidos (o a definir) del feature
`001-reportes-fastapi`.

**Entrada**: Descripción del usuario: "Quiero que los endpoints se prueben con Swagger; al
finalizar cada endpoint me debe dejar probarlos con Swagger."

## Clarifications

### Sesión 2026-09-08

- Q: ¿Qué alcance tiene "probar con Swagger": solo que la UI interactiva exista y liste los
  endpoints, o que cada endpoint sea efectivamente ejecutable ("Try it out") desde Swagger UI
  con respuestas reales del servicio (incluyendo, cuando aplique, autenticación de administrador)? → A: Debe ser completamente ejecutable ("Try it out") para cada endpoint, incluyendo poder
  autenticarse como administrador y usar esa sesión para probar los endpoints protegidos, no solo
  una lista de documentación estática.
- Q: El endpoint de login de administrador de `001-reportes-fastapi` (FR-001/002/020) todavía no
  está implementado. ¿Este feature (`002-swagger-docs`) debe esperar a que ese login exista, o
  se agrega aquí un login propio? → A: Se agrega en este feature un login mínimo de administrador
  **exclusivamente para fines de prueba** (no forma parte del alcance final del proyecto); el
  proyecto final tendrá una sección separada de login/registro para usuarios finales, donde el
  administrador podrá registrarse por esa vía. Este login de prueba es temporal y desacoplado de
  ese flujo final, solo para poder ejercitar Historia de Usuario 3 desde Swagger UI mientras el
  login definitivo no exista.
- Q: FR-009 exige poder habilitar/deshabilitar Swagger UI según el entorno sin cambios de código,
  pero no existe hoy ningún mecanismo de configuración de entorno en el servicio (`config.py` no
  tiene un campo `environment`/`debug`). ¿Cómo se resuelve? → A: Se agrega un requisito explícito
  (FR-011): debe existir una variable de entorno configurable (ej. `ENVIRONMENT` o `ENABLE_DOCS`)
  que el servicio lea para decidir si expone la documentación interactiva, con un comportamiento
  seguro-por-defecto si no se especifica; el nombre exacto de la variable se define en `/plan`.
- Q: FR-010 exige un login de prueba con "credenciales fijas simples", pero no especifica si esas
  credenciales deben leerse de variables de entorno o pueden estar hardcodeadas en el código,
  dado que `config.py` no tiene ningún campo `admin_user`/`admin_password`. ¿Cómo se resuelve? →
  A: Las credenciales del login de prueba también DEBEN leerse de variables de entorno (ej.
  `TEST_ADMIN_USER`/`TEST_ADMIN_PASSWORD`), nunca hardcodeadas en el código, manteniendo
  consistencia con la buena práctica ya establecida en `001-reportes-fastapi` de no hardcodear
  credenciales, aun siendo este login desechable/temporal.

## Escenarios de Usuario y Pruebas *(obligatorio)*

### Historia de Usuario 1 - Explorar y entender los endpoints disponibles (Prioridad: P1)

Como desarrollador o QA del equipo, quiero abrir una URL de documentación interactiva (Swagger UI)
y ver listados todos los endpoints del servicio de reportes, agrupados de forma clara, con la
descripción de sus parámetros, tipos de respuesta y códigos HTTP posibles, para poder entender
rápidamente qué hace cada endpoint sin leer el código fuente.

**Por qué esta prioridad**: Es el valor mínimo indispensable: sin esto no hay forma de descubrir
la API de forma autoguiada. Habilita a cualquier otra historia de este feature.

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

### Historia de Usuario 2 - Ejecutar (probar) cualquier endpoint directamente desde Swagger (Prioridad: P1)

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
3. **Dado** que el usuario ya se autenticó (ver Historia de Usuario 3) desde la misma página,
   **Cuando** ejecuta un endpoint protegido con "Try it out", **Entonces** la sesión obtenida se
   adjunta automáticamente a la solicitud y el endpoint responde con datos reales (200 con el
   reporte correspondiente), no 401.

---

### Historia de Usuario 3 - Autenticarse como administrador desde la misma documentación (Prioridad: P2)

Como desarrollador o QA, quiero poder ejecutar el endpoint de login de administrador desde
Swagger UI y que la credencial de sesión resultante quede disponible para probar automáticamente
el resto de los endpoints protegidos, sin tener que copiar/pegar manualmente un token en cada
solicitud.

**Por qué esta prioridad**: Mejora significativamente la experiencia de prueba end-to-end, pero
la Historia de Usuario 2 ya es parcialmente utilizable (para endpoints sin protección o pegando
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
3. **Dado** que la sesión cargada expiró (ver FR-002 del feature `001-reportes-fastapi`,
   expiración a medianoche), **Cuando** el usuario ejecuta cualquier endpoint protegido desde
   Swagger UI, **Entonces** recibe 401 de forma visible, indicando que debe volver a autenticarse
   y recargar la credencial de sesión en el mecanismo de autorización.

---

### Casos Límite

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
  FR-020 de `001-reportes-fastapi`), ambas sesiones son válidas de forma independiente mientras
  no expiren; no hay conflicto de datos porque los endpoints son de solo lectura.

## Requisitos *(obligatorio)*

### Requisitos Funcionales

- **FR-001**: El sistema DEBE exponer una página de documentación interactiva (Swagger UI) en una
  URL conocida y accesible mientras el servicio esté corriendo en entornos de desarrollo/QA.
- **FR-002**: La página de documentación interactiva DEBE listar automáticamente todos los
  endpoints expuestos por el servicio de reportes (los 13 reportes de `001-reportes-fastapi` más
  el endpoint de login de administrador), agrupados por categoría/tag, sin requerir
  mantenimiento manual de una lista separada.
- **FR-003**: Cada endpoint listado DEBE mostrar, como mínimo: método HTTP, ruta, parámetros de
  entrada esperados (query params y/o cuerpo), los códigos de respuesta HTTP posibles, y un
  ejemplo de la estructura de la respuesta exitosa.
- **FR-004**: El sistema DEBE permitir ejecutar ("Try it out") cualquier endpoint directamente
  desde la página de documentación interactiva, contra la instancia real del servicio en
  ejecución, mostrando la respuesta real (código HTTP + cuerpo) en la misma página.
- **FR-005**: El sistema DEBE proveer, dentro de la misma página de documentación interactiva, un
  mecanismo para que el usuario cargue la credencial de sesión de administrador obtenida del
  endpoint de login (ej. mediante el botón "Authorize" estándar de Swagger UI), de forma que las
  ejecuciones posteriores de endpoints protegidos incluyan automáticamente esa credencial sin
  intervención manual adicional por solicitud.
- **FR-006**: Al ejecutar desde "Try it out" un endpoint protegido sin una credencial de sesión
  válida cargada, el sistema DEBE mostrar en la página de documentación la respuesta real 401 del
  servicio (no un error genérico de red ni de CORS).
- **FR-007**: Al ejecutar desde "Try it out" un endpoint con parámetros inválidos, el sistema
  DEBE mostrar la respuesta real de error (422) del servicio, igual que a través de cualquier
  otro cliente HTTP.
- **FR-008**: La documentación interactiva NO DEBE requerir edición manual duplicada cada vez que
  se agregue, modifique o elimine un endpoint del servicio; debe reflejar automáticamente los
  endpoints existentes en cada momento.
- **FR-009**: El sistema DEBE permitir habilitar o deshabilitar el acceso a la documentación
  interactiva según el entorno (desarrollo/QA vs. producción), sin requerir cambios de código
  para alternar entre ambos modos.
- **FR-010**: Dado que el login de administrador definitivo (`001-reportes-fastapi`, FR-001/002/
  020) puede no estar implementado al momento de ejecutar este feature, el sistema DEBE proveer
  un endpoint de login de administrador **mínimo y exclusivamente de prueba** (credenciales fijas
  simples leídas de variables de entorno dedicadas —p. ej. `TEST_ADMIN_USER`/
  `TEST_ADMIN_PASSWORD`—, nunca hardcodeadas en el código, aunque sin necesariamente cumplir
  todos los demás requisitos de seguridad de FR-020, como el hasheo de contraseña), únicamente
  para poder emitir una credencial de sesión utilizable en el mecanismo "Authorize" de Swagger UI
  y así ejercitar la Historia de Usuario 3. Este endpoint de prueba: (a) NO forma parte del
  alcance final del proyecto, (b) NO reemplaza ni debe confundirse con el login definitivo de
  administrador de `001-reportes-fastapi` ni con la sección de login/registro de usuarios finales
  del proyecto final (donde el administrador podrá registrarse), y (c) DEBE quedar claramente
  identificado (ej. en su descripción/tag en Swagger UI) como "solo para pruebas", para que no se
  use por error como mecanismo de autenticación de producción.
- **FR-011**: El sistema DEBE leer de una variable de entorno (ej. `ENVIRONMENT` o
  `ENABLE_DOCS`), configurable sin cambios de código, el valor que determina si la documentación
  interactiva (Swagger UI) y su documento OpenAPI subyacente quedan expuestos o no; por defecto,
  en ausencia de configuración explícita, el sistema DEBE comportarse de forma seguro-por-defecto
  (ej. expuesto en desarrollo, oculto si no se especifica el entorno como desarrollo/QA).

### Entidades Clave

- **Documento OpenAPI**: Descripción estructurada (generada automáticamente por el framework del
  servicio) de todos los endpoints, sus parámetros, tipos de datos y respuestas posibles; es la
  fuente que consume Swagger UI para renderizarse.
- **Sesión de administrador (de prueba, ver FR-010, o reutilizada de `001-reportes-fastapi` si ya
  existe)**: Credencial obtenida del endpoint de login (temporal de pruebas o definitivo, según
  cuál esté disponible), cargada en el mecanismo de autorización de Swagger UI para probar
  endpoints protegidos sin pasos manuales adicionales.

## Criterios de Éxito *(obligatorio)*

### Resultados Medibles

- **SC-001**: Un desarrollador o QA que nunca vio el código puede, únicamente con la URL de
  Swagger UI, identificar los 13 reportes y el endpoint de login, y describir correctamente sus
  parámetros de entrada, en menos de 5 minutos.
- **SC-002**: El 100% de los endpoints del servicio de reportes pueden ejecutarse exitosamente
  ("Try it out") desde Swagger UI y devolver la misma respuesta que se obtendría llamándolos con
  cualquier otro cliente HTTP (ej. `curl`), para el mismo conjunto de parámetros.
- **SC-003**: Un usuario puede autenticarse y probar un endpoint protegido completo (login +
  carga de sesión + ejecución de un reporte protegido) sin salir de la página de Swagger UI ni
  usar herramientas externas, en menos de 2 minutos.
- **SC-004**: Agregar un endpoint nuevo al servicio no requiere ninguna edición manual adicional
  en un archivo de documentación separado para que aparezca en Swagger UI; aparece
  automáticamente tras reiniciar el servicio.

## Supuestos

- El framework HTTP usado por el servicio (FastAPI) genera automáticamente el documento OpenAPI y
  expone Swagger UI de forma nativa; este feature se apoya en esa capacidad nativa en vez de
  construir una solución de documentación desde cero.
- El mecanismo de autorización de Swagger UI (botón "Authorize") es suficiente para cumplir el
  requisito de "cargar la sesión una vez y probar el resto de los endpoints"; no se requiere un
  flujo de autenticación visual adicional fuera de lo que Swagger UI ofrece por defecto.
- El nombre exacto de la variable de entorno (ej. `ENVIRONMENT`, `ENABLE_DOCS`), sus valores
  posibles, y el comportamiento seguro-por-defecto exacto se definen con precisión durante
  `/plan` (ver FR-011); lo que este spec fija como requisito de negocio es que dicho control
  exista y sea configurable sin cambios de código, no el nombre/formato literal de la variable.
- Este feature no introduce nuevos endpoints de negocio; únicamente garantiza que los endpoints
  ya definidos (o a definir) en `001-reportes-fastapi` sean descubribles y ejecutables desde
  Swagger UI.
- El endpoint de login de administrador introducido por este feature (FR-010) es **estrictamente
  temporal y de alcance de prueba**: no forma parte de la versión final del proyecto. El proyecto
  final NO contempla login/registro en este módulo de reportes; existe una sección separada del
  sistema (fuera de este repo/módulo) donde los usuarios finales inician sesión y donde el
  administrador podrá registrarse. Este login de prueba se retira o se reemplaza cuando ese flujo
  definitivo esté disponible, sin que su existencia temporal condicione el diseño final de
  autenticación del proyecto.
