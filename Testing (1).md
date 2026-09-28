# Testing de Software

> **Fuente:** Testing.pdf — contenido transcripto mediante OCR.


---

## Página 1

Fundamentos de Ingeniería de Software

Testing de Software: De la
cascada a los tests basados
en especificaciones



---

## Página 2

¿Qué es el Testing de Software?

Testing (Definición ISTQB) Depuración (Debugging)

Un proceso formal que incluye planificación,
diseño, ejecución y evaluación del software.
No es solo correr el código. XN

Objetivos:
1. Prevenir fallos antes de que ocurran. Un proceso técnico posterior a la
2. Identificar defectos estructurales y lógicos. detección del fallo.

3. Generar confianza empírica en el sistema.

Enfoque: Prevención y Detección. Encontrar Enfoque: Corrección. Identificar la causa
lo que debería.



---

## Página 3

La Evolución: De la Cascada al Vibe

Coding

Fase 1: Tradicional
(Cascada)

Probar al final del ciclo de
desarrollo. Altamente
costoso, reactivo e
ineficiente.

ad,

Peligro: Vibe Coding
Fase 2: Auge Agil LS
(TDD) Programar de manera

informal en el chat de lA sin
una fuente de verdad objetiva.

El Nuevo Estándar: SDD

Probar antes de codificar.
El test guía el diseño
interno del código fuente.

Pe
Spec-Driven Development. La

especificación es el contrato
inquebrantable que audita a la lA.



---

## Página 4

Caja Negra vs Caja Blanca

Output

Input ——>

Testing de Caja Negra

Pruebas basadas exclusivamente en requisitos y
especificaciones externas.

Foco: ¿Hace el sistema lo que el usuario y el contrato
piden? Cero acceso a la estructura de código interno.

Testing de Caja Blanca

Análisis profundo del código fuente y cobertura
estructural.

Foco: Analiza de manera transparente rutas lógicas,
sentencias, ciclos y decisiones algorítmicas internas.


---

## Página 5

Pruebas Unitarias y el Estándar F.I.R.S.T.

Testing de Unidad: Probar la unidad mínima de código en aislamiento absoluto (sin
interacción con bases de datos, redes o archivos). Utiliza Dobles de Prueba (Stubs,
Mocks) para simular el mundo exterior.

[F] Fast
(Rápidas)

Deben ejecutarse en
milisegundos.

[I] Independent
(Independientes)

(ay
0

El resultado no debe
depender del estado
dejado por otra
prueba.

[R] Repeatable
(Repetibles)

Mismo resultado en

cualquier entorno de
ejecución, siempre.

[S] Self-validating
(Autovalidables)

Y

Devuelven un "Pasa"
o "Falla" binario;
binario; sin
inspección humana.

[T] Timely
(Oportunas)

Escritas en el
momento justo,
antes del código de
producción.



---

## Página 6

El Ritmo de Desarrollo: TDD (Test-Driven

Development)

RED

Escribir prueba que

falla. Define intención.

REFACTOR

Mejorar diseño sin alterar
comportamiento.

GREEN

Código mínimo para
pasar la prueba.

Ejemplo: Validador de contraseña
(8 a 30 caracteres)

Fase RED Fase GREEN Fase REFACTOR
@Test class Validador { class Validador {
void longitudMenorA8F void validar (String private static final
Validador v = new \ throws Exception : void validar(String c
assertThrows(Except if (contrasenia. le if (isMuyCorta(cont
() -> // 7 cé throw new Except throw new Excepti
v.validar("12345€ } }
»; ) }
} } private boolean isMuy
return contrasenia.
}
}

La aserción falla porque Escribir el código mínimo Mejorar el diseño sin alterar
el validador aún no para que la prueba pase comportamiento. Se

existe o no implementa La implementación es extrae constante y método
la lógica simple y directa para mayor claridad



---

## Página 7

El Ritmo de Desarrollo: TDD (Test-Driven
Development)

Ejemplo: Validador de contraseña

RED (8 a 30 caracteres)
Escribir prueba que
falla. Define intención.
Test Fase RED:

La aserción

void longitudMenorA8Falla() { falla porque

Validador v = new Validador();_ st niga
aun no existe.

assertThrows(Exception.class, () -> {
v.validar("1234567"); // 7 caracteres

});
REFACTOR GREEN }
Mejorar diseño sin alterar Código mínimo para
comportamiento. pasar la prueba.

is


---

## Página 8

El Ritmo de Desarrollo: TDD (Test-Driven
Development)

Ejemplo: Validador de contraseña

RED (8 a 30 caracteres)
Escribir prueba que
falla. Define intención. Fase GREEN

class Validador {
void validar(String contrasenia)
throws Exception {
if (contrasenia.length() < 8) {
throw new Exception("Contrasenia muy corta”);

)
REFACTOR GREEN a
Mejorar diseño sin alterar Código minimo para AAA
comportamiento. pasar la prueba.

Escribir el código mínimo para que la prueba pase.
La implementación es simple y directa.



---

## Página 9

El Ritmo de Desarrollo: TDD (Test-Driven
Development)

Ejemplo Refactorizado: Validador de contraseña
(8 a 30 caracteres)

RED
class Validador (

Escribir prueba que private static final int LONGITUD_MINIMA
falla. Define intención. private static final int LONGITUD_MAXIMA

8;
30;

void validar(String contrasenia) throws Exception (
if (esInvalida(contrasenia)) {
throw new Exception("La contraseña debe tener entre " +L

)
}

private boolean esInvalida(String contrasenia) {
return contrasenia == null || contrasenia.length() <

REFACTOR GREEN LONGITUD_MINIMA || contrasenia.length() > LONGITUD_MAXIMA;

Mejorar diseño sin alterar Código minimo para )
comportamiento. pasar la prueba.

Mejorar el diseño sin alterar comportamiento. Se extraen constantes para

los límites y un método privado para la lógica de validación, aumentando la
claridad y mantenibilidad.



---

## Página 10

Specification-Based Testing (SBT): La Fuente de la

Verdad

El Cambio de Pregunta

Antiguo enfoque: ¿Qué
pruebas puedo escribir
mirando el código que
acabo de

programar?

Nuevo enfoque SBT:
Según la especificación,
¿qué comportamientos
observables debe
demostrar el sistema?

Spec.md

(La Especificación)

$). 3

Casos de Prueba Derivados

El "De Dónde"

SBT es una técnica de
Caja Negra que
responde de dónde
provienen las pruebas.

La especificación es la
única fuente de

fuente de verdad
autorizada para auditar,
no el código.



---

## Página 11

Técnicas SBT I: Particiones y Valores Limite

Pruebas de l

& yl Límite: 7, 8

NS

Pruebas de l

e >! Límite: 30, 31

Y

|
Inválido (< 8) Válido (8 a 30) Inválido (> 30)

Partición de Equivalencia

Divide las entradas en grupos con
comportamiento equivalente. Se prueba un solo
representante por grupo para evitar redundancia.

Análisis de Valores Límite

Los errores algorítmicos (ej: usar > en lugar de
>=) ocurren exactamente en las transiciones
matemáticas. Se auditan los bordes.



---

## Página 12

Técnicas SBT Il: Tablas de Decisión y Transiciones

Tablas de Decisión Transiciones de Estados
(Causas Multiples) (Sistemas Dinámicos)
: Resultado:
Autenticado Es Creador Puede Bomar ve A Con B
A Válida ~ Productos? válida
No - No
Si Si Si
C
Si No No NH Pagado
Transición Inválida

Cada fila estructurada se traduce Prueba las rutas cronológicas de estados
matemáticamente en un caso de prueba permitidos y prohibidos.

automatizado.


---

## Página 13

Técnicas SBT Ill:
Given-When-Then

GIVEN (Dado)

La Precondición. Establece
el contexto o estado inicial
exacto del sistema antes de
someterlo a prueba.

THEN (Entonces)

// GIVEN: Usuario válido creado
Usuario u = new Usuario();

// WHEN: Intenta registrar password de 7 chars |

Exception e = assertThrows(Exception.class, () -> u.setPassword("1234567")); |

// THEN: El sistema rechaza la operación
assertEquals("Invalido", e.getMessage());

El Resultado. Las aserciones
donde se verifica que el
comportamiento observable
coincida con el contrato.

WHEN (Cuando)

La Acción. El evento,
función o entrada específica
que se somete al escrutinio
del auditor.


---

## Página 14

Paso 1: La especificación como el contrato

absoluto del software.

EAS

### RF-@3 - Registro de Usuario

El sistema debe permitir registrar un usuario.

- La contraseña debe tener entre 8 y 30 caracteres. «__

- Todos los campos son obligatorios.

Regla de negocio: unicidad

- El email debe ser único y tener un formato válido TN

ll

Valores límite: 8 y 30



---

## Página 15

Paso 2: El plan de pruebas traduce reglas a casos estructurados

El programador analiza spec.md y redacta los casos en test-plan.md usando
técnicas SBT y el formato Given-When-Then (GWT).

test-plan.md

ID: TC-001 (Límites)

GIVEN (Precondición): Un sistema de registro activo.

WHEN (Acción): Se ingresa un usuario con contraseña de 7 caracteres.

THEN (Resultado): El sistema rechaza la petición por longitud inválida.



---

## Página 16

Paso 3: La automatización formaliza el contrato
en código ejecutable (Fase RED).

Valores Límite Inválidos

ID: TC-001
GIVEN: Un sistema activo.

WHEN: Contraseña de 7 caracteres (y 31
caracteres).

THEN: El sistema rechaza la petición.

Java JUnit 5

1 @ParameterizedTest

2 @ValueSource(ints = {7, 31})

3 void longitudesInvalidasDebenSerRechazadas(int longitud) {
4 String password = "a".repeat (longitud);

5 assertThrows(PasswordInvalidaException.class, () ->

6 servicio.registrar("Juan", "juan@mail.com", password)
7 );
8 )

Nota Importante

Uso de @ParameterizedTest para probar ambos límites (7 y 31) en una sola estructura sin duplicar código.



---

## Página 17

Paso 4: La lA cumple el contrato sin
alterar las reglas (Fase GREEN).

spec.md Agent/Copilot JUnit Tests
(Input to Al) (Writes Implementation) (Validation Gate)

La lA lee la especificación y corre los tests en Java implementando la

lógica para ponerlos en Verde. Regla de oro: La lA jamás debe modificar las
aserciones de los tests de aceptación simplemente para hacerlos pasar.



---

## Página 18

Flujo SDD Moderno:
Arquitectura y Auditoría con lA

Zona de Responsabilidad Humana Zona de Responsabilidad IA
(El Auditor) (El Obrero)
l J
f 1 f 1
3. Código de 4.
1. Spec.md 2. Test-Plan AP 5. Refactor
-——> t——> — » de
(Humano) (SBT/Humano) lesa O 1 (I¡A+Humano)
Arquitecto define Diseño con límites Ml JUnit / Fase RED. Ml Agente IA escribe Optimización
reglas sin y particiones. Parametrizados. código Java estructural del
ambigiiedades. productivo. código verificado.
Fase GREEN.

LA REGLA DE ORO: La Inteligencia Artificial NUNCA debe generar tests basándose en su

propio código productivo, ni modificar un test para autovalidar suposiciones sesgadas.

