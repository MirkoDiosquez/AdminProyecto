<!--
Sync Impact Report
===================
Version change: [TEMPLATE] → 1.0.0 (initial ratification)
Modified principles: N/A (first version)
Added sections:
  - Core Principles (I–VII)
  - Contexto de Negocio y Arquitectura General
  - Seguridad y Privacidad
  - Estructura de Repositorios y Documentación Viva
  - Relación con las Constituciones de Módulo
  - Governance (decisiones cerradas + proceso de enmienda)
Removed sections: N/A
Templates requiring updates:
  - .specify/templates/plan-template.md ⚠ pending manual review (Constitution Check section)
  - .specify/templates/spec-template.md ⚠ pending manual review (declarar área A/B/C/D + offline behavior)
  - .specify/templates/tasks-template.md ⚠ pending manual review
Follow-up TODOs:
  - TODO(RATIFICATION_DATE): el equipo debe fijar la fecha real de ratificación (ver Sección 10 del
    documento original: "a completar por el equipo").
-->

# Constitución General — Proyecto "App Anti-Procrastinación" Constitution

> **Alcance de este documento:** esta es la Constitución **raíz** del proyecto (TP Final de
> Arquitectura de Software, Instituto Politécnico Modelo — equipo de 8 integrantes). Fija el
> contexto de negocio, la arquitectura completa del sistema y las decisiones transversales que
> **ningún módulo puede contradecir**. Este repositorio (`Analitycs`) implementa el **Módulo de
> Reportes / ETL** que alimenta al Panel Admin (Área **C — Notificaciones + Admin**) y, como todo
> módulo, debe redactar su propia Constitución de módulo que hereda y referencia ésta (ver
> Sección "Relación con las Constituciones de Módulo").

## Core Principles

### I. Arquitectura en Capas Independientes (NON-NEGOTIABLE)
El sistema se compone de capas que **no se colapsan ni se saltan**:
`App Android → Firebase (Auth, Firestore, FCM)`; `App Android → Backend propio (REST/JWT)`;
`Backend propio → RabbitMQ → Módulo de Notificaciones → FCM`; `Panel Admin → PostgreSQL` (solo
vía el Módulo de Reportes). El Panel Admin **nunca** lee de Firestore en tiempo real; la
sincronización Firestore → PostgreSQL ocurre **exclusivamente** vía el proceso ETL. La
comunicación Backend → Notificaciones es **siempre asíncrona** vía RabbitMQ, nunca una llamada
directa. Razón: aislar responsabilidades permite que cada equipo evolucione su capa sin romper
contratos de las demás, y evita acoplamientos ocultos entre Firestore (tiempo real) y PostgreSQL
(analítico).

### II. Offline-First para lo Personal
Todo lo **personal** del usuario (tareas, sesiones de foco, motor de bloqueo, configuración,
estadísticas del día) **debe** funcionar 100% offline, sin excepciones. Solo lo **social**
(ranking, grupos, desafíos, push) depende de internet y **debe** degradar mostrando la última
caché local disponible junto con un banner **no bloqueante** con fecha/hora del último sync; el
banner nunca impide usar el resto de la app. Un desafío con modo estricto obligatorio puede forzar
el nivel de bloqueo más alto incluso sin conexión, leyendo la caché local. Razón: la filosofía de
producto exige que el bloqueo funcione siempre; depender de red para lo personal rompería la
promesa central del producto.

### III. Backend como Única Fuente de Verdad (Anti-Trampa)
Cualquier contador o estado que pueda manipularse localmente para hacer trampa (ej. el **pase de
emergencia**) se valida **siempre en el servidor**, nunca solo en el cliente; el cliente solo
muestra el resultado. El pase de emergencia es la única acción que puede bloquear completamente al
usuario si no hay internet, porque su validación en servidor no tiene excepción, y esto **debe**
comunicarse claramente en la UI. Razón: sin esta regla el mecanismo de incentivos del producto
(minutos ganados, rachas, ranking) pierde toda credibilidad.

### IV. Modelado de Datos Consistente y Documentado
Cada componente que persiste datos declara su propio modelo (Room, Firestore, PostgreSQL), pero
todo cambio de modelo se documenta en `/docs` **como parte del mismo cambio**, nunca después. Los
timestamps se manejan como epoch ms (`INTEGER`) en todos los sistemas, salvo campos de fecha pura
(ej. `usage_date`) en formato `TEXT "YYYY-MM-DD"`. Los ajustes/preferencias nuevos se agregan como
filas en una tabla/colección clave-valor (`config`), nunca como columnas/campos nuevos. Los datos
demográficos opcionales no completados se guardan como `NULL`/`null` en toda la cadena; nunca se
inventan valores. Los **ETL son siempre idempotentes** (upsert): correrlos dos veces nunca duplica
datos ni inventa datos ausentes. Razón: consistencia de modelo entre 8 personas y 4 áreas solo es
sostenible si las reglas de datos son mecánicas y verificables, no discrecionales.

### V. Seguridad, Privacidad y Manejo de Errores
El equipo nunca maneja, ve, ni almacena contraseñas: es responsabilidad exclusiva de Firebase
Authentication. El JWT emitido por Firebase Auth se valida en un **único punto centralizado** del
backend, nunca repetido por endpoint. El backend responde siempre con JSON consistente y códigos
HTTP semánticos (401/403/404/422/500), y **nunca** expone un stack trace al cliente. El consumidor
de RabbitMQ hace ACK solo tras procesamiento exitoso; un mensaje nunca se pierde silenciosamente si
falla. Los datos de uso de apps son locales por defecto y solo se envían agregados al backend con
consentimiento explícito obtenido en el onboarding (incluyendo pantalla de política de privacidad).
Cualquier permiso sensible del sistema operativo se verifica explícitamente antes de usarlo; nunca
se asume concedido. Razón: estas son las superficies de riesgo reales del producto (credenciales,
datos personales, pérdida silenciosa de mensajes) y deben tratarse como no negociables.

### VI. Testing Riguroso en Puntos de Integración
No se introducen frameworks de testing nuevos sin necesidad real documentada en la spec
correspondiente, validada por el área de propiedad responsable (no por una persona individual).
Son **obligatorios**: tests de integración en todo punto de contacto entre módulos (ej. endpoint
del backend con JWT inválido → 401) y tests de idempotencia en todo proceso de sincronización o
ETL. Todo comportamiento específico de un dispositivo/entorno real (hardware, SO, capas de
personalización) se prueba en ese entorno real cuando exista evidencia de que el emulador no lo
reproduce fielmente. Razón: los puntos de integración y los ETL son donde más frecuentemente
aparecen bugs silenciosos de duplicación o contratos rotos entre áreas.

### VII. Flujo Spec-Kit Obligatorio y Decisiones Cerradas
No se implementa lógica de negocio nueva sin spec y plan previos. Flujo obligatorio para features
no triviales: `/constitution → /specify → /clarify → /plan (Constitution Check) → /tasks →
/implement`. Esta Constitución (y la del módulo correspondiente) tiene prioridad sobre cualquier
pedido puntual que la contradiga; si hay conflicto, el agente debe señalarlo **antes de proceder**
y esperar confirmación explícita del equipo. Las siguientes decisiones están **cerradas** y no se
pueden reabrir sin pedido explícito y por escrito de al menos 2 integrantes del equipo:
  - Solo Android en v1, sin iOS.
  - Distribución por APK directo, sin Google Play Store.
  - RabbitMQ como broker de mensajería (evaluado y descartado: Redis Pub/Sub por falta de
    persistencia, Kafka por complejidad innecesaria para el volumen del proyecto).
  - Firebase como proveedor de Auth/Firestore/FCM (no se programa un reemplazo propio).
  - El pase de emergencia se valida siempre en servidor, sin lógica local de conteo.
  - El Panel Admin lee siempre de PostgreSQL vía el Módulo de Reportes, nunca de Firestore en
    tiempo real.
Toda spec debe declarar: (a) su área de propiedad (A — App, B — API, C — Notificaciones + Admin,
D — Firebase/Integración/QA), (b) su comportamiento offline explícito (funciona sin internet /
requiere internet / degrada a caché), y (c) si toca un modelo de datos, actualizar la
documentación de modelo correspondiente como parte del mismo cambio. Si una spec asume un
contrato con otra área (formato de datos, endpoint, evento), ese contrato debe estar confirmado
por escrito por ambas áreas antes de implementarse; en caso contrario la spec queda bloqueada.

## Contexto de Negocio y Arquitectura General

La aplicación es un Launcher Android nativo que resuelve tres problemas de procrastinación
digital: (1) bloqueo progresivo de redes sociales en tres niveles escalables (Blando, Insistente,
Estricto) más un pase de emergencia validado 100% en servidor; (2) tareas y sesiones de foco
cronometradas que otorgan minutos extra de uso según un ratio configurable; (3) competencia social
grupal con ranking en tiempo real sobre un catálogo fijo de desafíos predefinido por la plataforma.
El **administrador de plataforma** es un segundo tipo de usuario que solo accede al Panel Admin
interno (web) con estadísticas globales; nunca es usuario de la app final. Filosofía del producto:
usar el teléfono debe ser incómodo mientras hay tareas pendientes, no imposible; la fricción escala
pero nunca sorprende (todo se explica en el onboarding); los mensajes ante rachas rotas son de
acompañamiento, nunca punitivos. Alcance v1: solo Android, distribución por APK directo.

**Componentes y responsabilidad:**

| Componente | Responsabilidad | Depende de |
|---|---|---|
| App Android | UI, motor de bloqueo local, tareas/foco offline | Firebase SDKs, API REST del backend |
| Firebase (Google) | Auth, Firestore (ranking/desafíos en tiempo real), FCM | — |
| Backend propio | Valida JWT de Firebase, lógica de negocio server-side, expone API REST | Firebase Admin SDK, RabbitMQ |
| Módulo de Notificaciones | Consume RabbitMQ, envía push vía FCM | RabbitMQ, Firebase Admin SDK |
| Panel Admin (ETL + Reportes + Web) | Estadísticas globales para el administrador de plataforma | PostgreSQL (nunca Firestore directo) |

**Áreas de propiedad del equipo** (toda spec debe declarar la suya):
- **A — App** (3 personas): módulo Android.
- **B — API** (2 personas): backend propio.
- **C — Notificaciones + Admin** (2 personas): módulo de notificaciones y Panel Admin (ETL,
  Reportes, Web) — este repositorio (`Analitycs`) pertenece a esta área.
- **D — Firebase / Integración / QA** (1 persona): configuración de Firebase, integración entre
  áreas, testing transversal.

**Resolución de conflictos entre áreas**: si una spec de un área asume un contrato que otra área no
confirmó explícitamente, la spec queda bloqueada hasta que ambas áreas lo acuerden por escrito en
el propio archivo de spec. Ninguna área puede asumir unilateralmente el comportamiento de otra.

## Estructura de Repositorios y Documentación Viva

Cada módulo (App, Backend, Notificaciones, Admin) vive en su propio repositorio o carpeta
independiente, con su propia Constitución de módulo. Cada módulo mantiene: `/specs`
(especificaciones de Spec Kit, organizadas por feature, declarando su área A/B/C/D); `/docs`
(documentación viva de arquitectura y modelo de datos, actualizada junto con el código, nunca
después); `README.md` (instrucciones de build, permisos/variables de entorno requeridas, notas de
setup). Ningún módulo copia código de un prototipo/demo directamente a su rama principal sin
revisión; los prototipos son solo referencia de estructura.

## Relación con las Constituciones de Módulo

Este documento es la **raíz**. Cada módulo (App, Backend, Notificaciones, Panel Admin, etc.)
redacta su propia `constitution.md` de módulo, que: (1) declara qué versión de esta Constitución
general usa como base (ej. "Basada en Constitución General v1.0.0"); (2) no puede contradecir
ninguna decisión cerrada del Principio VII — si un módulo necesita hacerlo, primero se enmienda
esta Constitución general, no la del módulo; (3) agrega únicamente lo específico de su stack:
lenguaje, convenciones de nomenclatura, estructura de paquetes/carpetas interna, tablas o
colecciones de su propio modelo de datos, permisos específicos de su plataforma, y las
herramientas de testing concretas que usa; (4) hereda sin necesidad de repetir el contexto de
negocio, la arquitectura general, y los principios offline y de seguridad de este documento —
puede citarlos brevemente para dar contexto, pero no debe copiar el texto completo.

## Governance

Esta Constitución tiene prioridad sobre cualquier práctica, spec o pedido puntual que la
contradiga. Todo PR/plan de implementación debe verificar cumplimiento vía el "Constitution Check"
de `/speckit-plan`; cualquier complejidad no justificada por un Principio debe explicarse o
eliminarse.

**Versionado semántico**:
- **MAJOR**: cambio de una decisión cerrada (Principio VII), o cualquier cambio que rompa lo que
  un módulo ya asume como base.
- **MINOR**: nueva sección, nueva regla que agrega restricción sin contradecir las existentes,
  nuevo componente en la arquitectura.
- **PATCH**: corrección de redacción o aclaración sin cambio de intención.

**Proceso de enmienda**:
1. Un integrante propone la enmienda por escrito (documento en `/specs` o issue en el
   repositorio), explicando la razón del cambio.
2. Al menos 2 integrantes deben aprobar explícitamente.
3. Se actualiza esta Constitución y se incrementa la versión.
4. Si el cambio afecta una decisión cerrada, todos los módulos deben revisar su propia
   Constitución para verificar que sigue siendo compatible.
5. El cambio se registra en el historial de commits con el mensaje:
   `constitution(vX.Y.Z): [descripción del cambio]`.

**Historial de versiones**:
- 1.0.0 — Versión inicial: extraída y generalizada a partir de la Constitución del módulo Android
  v2.0.0, incorporando la arquitectura completa del sistema (backend, RabbitMQ, Panel Admin) y las
  áreas de propiedad del equipo.

**Version**: 1.0.0 | **Ratified**: TODO(RATIFICATION_DATE): a completar por el equipo | **Last Amended**: 2026-09-07
