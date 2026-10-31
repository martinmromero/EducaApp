# Asistentes en el celular: análisis y propuesta (31/10/2026)

Pedido (V16): el indicador de pasos (chevrones) siempre arriba como parte superior, los botones Atrás / Siguiente /
Saltear siempre abajo, y que lo único que cambie sea la parte del medio. Análisis de cada asistente y cómo aprovechar
mejor la pantalla.

Medición hecha en un celular emulado de **369 × 716 px** (el área visible de tu celular, entre la barra de estado y la de
navegación), tema UAI, con el indicador a 64 px del borde (como queda hoy después de cada paso).

## 1. Cómo se reparte hoy la pantalla (716 px)

| Franja | Alto | Comentario |
|---|---|---|
| Margen superior reservado (botón ☰ flotante) | 64 px | Hoy el indicador queda a 64 px del borde para no chocar con el botón ☰. |
| Indicador de pasos (chevrones) | 43 px | |
| Aire entre indicador y tarjeta | ~26 px | |
| **Parte del medio (tarjeta del paso)** | **~472 px (66 %)** | Lo único que cambia entre pasos. |
| Botonera inferior (2 filas: Atrás / Siguiente + «Empezar de nuevo») | 87 px | 127 px en el último paso del oral (el botón final es más largo). |
| Barra superior (título, «Avanzado») | 119 px | Queda fuera de la vista al empezar cada paso; solo se ve al subir. |

Es decir: **un tercio de la pantalla (244 px) son marcos**, y la tarjeta tiene 472 px útiles.

## 2. Cuánto contenido necesita cada paso

(«Entra» = cabe en los 472 px sin desplazarse dentro del paso.)

**Asistente de examen (8 pasos)**: plantilla 362 ✓ · materia 262 ✓ · tópicos 648 ✗ · uno o varios temas 667 ✗ ·
docente y fecha 631 ✗ · institución, sede y curso **982** ✗ · tipo y modalidad 867 ✗ · rúbricas 613 ✗.
→ 2 de 8 entran.

**Cuestionario oral (3 pasos)**: materia 317 ✓ · alumnos, grupos y preguntas 658 ✗ · nombre y resumen 512 ✗.

**Plantilla (4 pasos)**: institución 613 ✗ · materia 518 ✗ · resultados y rúbricas 696 ✗ · nombre 733 ✗. → ninguno entra.

**Grupo de confianza (4 pasos)**: nombre 598 ✗ · materias 418 ✓ · rúbricas/plantillas/formatos **836** ✗ · revisar 513 ✗.

**Institución (4 pasos)**: nombre 422 ✓ · sedes 323 ✓ · facultades 319 ✓ · revisar 431 ✓. → los 4 entran (es el más compacto).

**Asistente paso a paso completo (7 pasos)**: los pasos 1 a 5 (institución, carrera, materia, resultados, preguntas) son
listas cortas; el **paso 7 (examen)** mete el asistente de examen en un marco (iframe) dentro de la pantalla del host:
arriba quedan el indicador del host + la barra «Armar: Examen escrito / Cuestionario oral» + «Paso X de N» (≈ 285 px)
y el marco recibe solo ~423 px, con su propia botonera adentro. Es el caso más apretado.

**Subir preguntas (3-4 pasos)**: indicador propio y botonera propia; mismo tratamiento que los demás.

## 3. Qué se puede ganar

La idea que proponés (indicador fijo arriba, botonera fija abajo, solo cambia el medio) es la correcta: es un
«cascarón» de aplicación. Hoy ya lo hacemos a medias (botonera fija abajo; indicador que sube a 64 px tras cada paso,
pero **se va de la vista si la tarjeta se desplaza**). Para completarlo:

1. **Indicador fijo (sticky) arriba**, siempre visible mientras se desplaza el medio. Se sube a 8 px del borde
   (hoy 64) y el botón ☰ pasa a ir dentro de la misma fila (a la izquierda del indicador, 40 px) en vez de flotar
   encima. Ganancia: **+56 px**.
2. **Botonera inferior de una sola fila (56 px)**: «Atrás» a la izquierda, botón principal a la derecha, y
   «Empezar de nuevo» / «Salir» se mueven a un menú «⋯» chico dentro de la misma fila (o al indicador). Ganancia:
   **+31 px** (87 → 56).
3. **Quitar el aire sobrante** entre indicador y tarjeta (26 → 8 px) y el padding interno de la tarjeta en celular
   (hoy ~24 px por lado): **+18 px** de alto y **+16 px de ancho** (los textos largos pasan de 5 a 4 renglones).

Resultado: la parte del medio pasa de **472 a ~600 px (+27 %)**. Con eso entran 5 de los 8 pasos del examen y 3 de 4
de plantilla y grupo; los más largos (institución/sede/curso 982, tipo y modalidad 867) seguirían desplazándose, pero
**solo en el medio**, con indicador y botones siempre a la vista.

4. **Asistente paso a paso, paso 7 (examen embebido)**: compactar el host en esa pantalla: «Armar:» y los dos botones en
   una sola fila (hoy dos), y «Paso X de N: …» en la misma fila a la derecha o dentro del marco. Se recuperan
   ≈ 110 px para el marco (de 423 a ~530 px). Es el cambio de más impacto en esa pantalla.
5. **Pasos largos**: partir en dos los tres más largos del examen (institución, sede y curso → «Institución» y
   «Sede y curso»; tipo y modalidad → dos pantallas) mejora más que cualquier ajuste de márgenes, pero agrega pasos:
   decisión de producto, no la tomo yo.

## 4. Cómo se implementa (un solo lugar)

Todo vive en `wizard_common.css` y `wizard_engine.js` (los usan examen, oral, plantilla, grupo, institución y el
asistente completo) y en el CSS propio de Subir preguntas:
- `.wiz-stepper { position: sticky; top: 0; z-index: 25; background: var(--bs-body-bg); }` solo en ≤ 767 px y dentro
  del contenedor del asistente.
- El botón ☰ flotante se muestra en línea dentro de esa fila cuando la pantalla es un asistente (un `padding-left` de
  48 px en el indicador y el botón anclado a la izquierda).
- Botonera: una fila (`flex-wrap: nowrap`), «Empezar de nuevo / Salir» en un menú desplegable «⋯».
- El desplazamiento al cambiar de paso ya existe (`scrollToStepper`); con el indicador fijo pasa a ser «volver al inicio
  del medio» (scrollTop de la tarjeta).
- Riesgos: el indicador fijo + el botón ☰ + la barra del navegador compiten por la parte de arriba (hay que probarlo en
  tu celular); y el asistente embebido necesita que el host fije su indicador y que el marco ocupe exactamente el alto
  restante (ya existe `fitExamFrame`, se le cambia la cuenta).

## 5. Recomendación y orden

1. Indicador fijo + botonera de una fila (puntos 1 y 2) en **todos** los asistentes a la vez: es lo que cambia la
   sensación y toca un solo archivo de estilos.
2. Compactar el paso 7 del asistente completo (punto 4).
3. Menos aire y padding (punto 3).
4. Recién después, evaluar partir pasos largos (punto 5) mirando cuántos siguen desplazándose.

Cada uno se prueba en el celular emulado con la misma medición de este documento y, al final, una vez en tu celular
real (V16 del artefacto).
