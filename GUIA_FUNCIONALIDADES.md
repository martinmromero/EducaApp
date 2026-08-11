# 🎓 ¿Qué hace EducaApp? - Guía Funcional Completa

> **Guía para usuarios, instituciones educativas y tomadores de decisiones**  
> Versión: Agosto 2026

---

## 📖 Introducción

EducaApp es un **sistema integral de gestión educativa** diseñado para facilitar la creación, organización y evaluación del proceso de enseñanza-aprendizaje. Permite a docentes e instituciones administrar contenido educativo, generar evaluaciones de manera inteligente y realizar un seguimiento completo del proceso evaluativo.

### Navegación

El menú lateral organiza todas las funciones en grupos temáticos: **Contenidos**
(subir material y generar preguntas con IA), **Preguntas** (banco propio),
**Exámenes** (armado, plantillas, rúbricas, orales, formatos de impresión),
**Mi espacio académico** (instituciones, carreras, materias), **Grupos**
(compartir preguntas con colegas de confianza) y, para administradores,
**Administración** (usuarios, monitoreo de IA, configuración de prompts).
Las tablas principales (preguntas, exámenes, contenidos, instituciones) se
adaptan automáticamente a tarjetas apiladas en pantallas chicas, en vez de
tablas angostas difíciles de leer en el celular.

Para cuentas nuevas, `/comenzar/` ofrece un **asistente de configuración
guiado** de varios pasos (institución → materia → contenido → generación con
IA) que arma un primer examen de punta a punta sin necesitar que el usuario
sepa de antemano por dónde empezar — ver la sección "¿Cómo Empezar?" al final
de este documento.

---

## 🎯 ¿Para quién es EducaApp?

### 👨‍🏫 Docentes y Profesores
Facilita la creación de exámenes, gestión de preguntas, organización de contenidos y evaluación de estudiantes.

### 🏛️ Instituciones Educativas
Permite estandarizar evaluaciones, mantener bancos de preguntas organizados y gestionar la estructura académica.

### 📚 Coordinadores Académicos
Ayuda a supervisar materias, resultados de aprendizaje y contenidos evaluativos por área.

---

## ✨ Funcionalidades Principales

### 1. 🏫 Gestión de la Estructura Institucional

EducaApp permite organizar toda la estructura de una institución educativa de manera jerárquica, desde **Instituciones** (`/instituciones-v2/`):

#### **Instituciones**
- Crear y administrar una o varias instituciones educativas
- Subir el logo institucional para personalización
- Marcar instituciones como "favoritas" para acceso rápido
- Consultar historial completo de cambios realizados (`/instituciones-v2/logs/<id>/`)

#### **Campus/Sedes y Facultades/Departamentos**
- Se gestionan **dentro de la pantalla de edición de la institución** (formulario
  con secciones embebidas para agregar/editar sedes y facultades), no como
  pantallas separadas — simplifica el flujo: toda la estructura de una
  institución se edita en un solo lugar.
- Cada sede admite dirección y datos propios; cada facultad, nombre y código.

#### **Carreras**
- Crear carreras académicas (`/careers/`)
- Asociar carreras con facultades y campus específicos
- Definir qué materias pertenecen a cada carrera

---

### 2. 📚 Gestión de Contenido Académico

#### **Materias/Asignaturas**
El sistema permite crear y administrar todas las materias que se dictan:

- Crear materias con nombre y descripción
- Asociar materias a una o varias carreras
- Definir semestre en que se cursa
- Indicar si es materia obligatoria u optativa
- Especificar carga horaria

#### **Resultados de Aprendizaje**
Para cada materia, puede definirse qué debe lograr el estudiante:

- Crear listados de resultados de aprendizaje esperados
- Editar y actualizar resultados según necesidad
- Eliminar resultados obsoletos
- Visualizar todos los resultados por materia

#### **Temas y Subtemas**
Organización jerárquica del contenido:

- **Temas principales**: Los grandes tópicos de la materia
- **Subtemas**: Divisiones específicas dentro de cada tema
- **Nivel de importancia**: Asignar prioridad a cada tema (escala 1-5)

Esta estructura permite luego filtrar y seleccionar preguntas de manera organizada.

---

### 3. 📄 Gestión de Materiales Educativos

#### **Subida de Documentos**
El sistema acepta diferentes tipos de archivos:

- **PDFs**: Libros, capítulos, artículos
- **Word (.docx)**: Documentos de texto
- **PowerPoint (.pptx)**: Presentaciones

#### **Política de Almacenamiento de Archivos**

Cada documento subido tiene un **ciclo de vida claro**:

- 🟡 **Mientras la sesión está activa**: El archivo físico está disponible para procesamiento y generación de preguntas.
- 🟠 **Al cerrar sesión (logout)**: El archivo físico se elimina automáticamente del servidor.
- 🟢 **Los metadatos se conservan siempre**: Título, ISBN, edición, editorial, año, páginas y todas las preguntas generadas permanecen en la base de datos indefinidamente.

> Esto significa que aunque no puedas volver a descargar el archivo, la información del libro y sus preguntas están siempre disponibles.

#### **Prevención de Archivos Duplicados**

El sistema detecta automáticamente si ya subiste el mismo archivo:

- Si el archivo **está activo**: El sistema bloquea la re-subida y te avisa que ya existe.
- Si el archivo **fue eliminado** (la sesión anterior cerró): El sistema lo restaura en lugar de crear un duplicado.

#### **Extracción Automática de Información**
Cuando sube un PDF, EducaApp **automáticamente extrae**:

- ISBN del libro
- Edición
- Número de páginas
- Editorial
- Año de publicación
- Capítulo (si aplica)

Esto ahorra tiempo al usuario, que solo debe verificar y confirmar los datos.

#### **Análisis Avanzado de Documentos**
Como parte del mismo flujo de subida (no como herramientas sueltas), el sistema:

- **Cuenta tokens** del documento y de cada capítulo/página, para orientar cuánto contenido conviene seleccionar por tanda de generación
- **Divide automáticamente** documentos largos en fragmentos manejables al mandarlos a la IA, respetando el límite de contexto del modelo
- **Limpia texto repetitivo** (headers/footers/números de página) antes de generar preguntas, para no ensuciar el contenido real

---

### 4. 🤖 Generación Inteligente de Preguntas con IA

Esta es una de las funcionalidades **más potentes** de EducaApp:

#### **Cómo Funciona**

1. **Subida del Material**: El docente sube un documento (PDF, Word, PowerPoint)

2. **Análisis Inteligente**: El sistema utiliza **Inteligencia Artificial** para:
   - Interpretar el contenido del texto
   - Analizar la estructura del documento
   - Identificar conceptos clave
   - Comprender el contexto educativo

3. **Selección de Contenido**: El usuario puede elegir:
   - Todo el documento
   - Capítulos específicos
   - Secciones particulares
   - Segmentos personalizados

4. **Generación Automática**: La IA crea automáticamente:
   - Preguntas relevantes basadas en el contenido
   - Respuestas correctas y detalladas
   - Diferentes tipos de preguntas (opción múltiple, verdadero/falso, completar el espacio, desarrollo)

5. **Curaduría del Docente**: El sistema presenta **todas las preguntas generadas** y el docente:
   - Revisa cada pregunta y respuesta
   - Marca las que son útiles y apropiadas
   - Descarta las que no cumplen los objetivos
   - **Guarda TODAS** (útiles y no útiles) para referencia futura   - Cada pregunta guardada **registra automáticamente el documento de origen** (título, ISBN, edición) para trazabilidad completa
6. **Clasificación Inteligente**: Para cada pregunta, el docente puede:
   - **Asignación Manual**: Seleccionar materia, tema y subtema
   - **Asignación Automática**: El sistema sugiere la clasificación más apropiada
   - Combinar ambos métodos según preferencia

7. **Nivel de Dificultad según Bloom**: El sistema permite asignar el **nivel de dificultad** de cada pregunta basado en la **Taxonomía de Bloom**:
   - Recordar (nivel más básico)
   - Comprender
   - Aplicar
   - Analizar
   - Evaluar
   - Crear (nivel más complejo)
   
   Esto ayuda a crear exámenes balanceados que evalúen diferentes niveles cognitivos.

#### **Motor de Inteligencia Artificial**

EducaApp elige el proveedor de IA por usuario (`material/ai_router.py`,
`get_backend_for_user`). Hay tres modos, configurables en "Proveedor de IA":

- 🌐 **Fallback compartido de demo (default)**: **Groq** para texto (rápido y
  gratuito dentro de su cupo diario) con **Gemini** como respaldo para
  imágenes/diagramas (Groq no tiene modelos con visión) y cuando Groq agota
  su cupo del día. No requiere que el docente configure nada — funciona "de
  fábrica" para cuentas nuevas. El cupo restante puede monitorearse en
  `/herramientas/groq-monitor/` (solo administradores).
- 🔑 **BYOK (clave propia)**: el docente o la institución cargan su propia API
  key de OpenAI, Anthropic, Groq, Gemini u otro proveedor compatible, sin
  depender del cupo compartido.
- 💻 **Ollama local**: un servidor Ollama en red interna, pensado como **plan
  de respaldo para escenarios sin internet** (por ejemplo, generar preguntas
  en un lugar sin conectividad confiable), no como el motor principal —
  requiere VPN/red local y no está disponible desde Render (producción).

Si un fragmento del documento incluye imágenes relevantes (diagramas, fotos),
el sistema puede mandarlas junto con el texto a un modelo con visión para que
la pregunta generada haga referencia a lo que se ve en ellas. Cada pregunta
generada también cita la **página real de origen** dentro del documento
(incluyendo, cuando es detectable, el número de página *impreso* del libro,
no solo el índice físico del PDF subido).

> Para la configuración técnica del servidor Ollama de respaldo, ver
> `LOCAL_AI_SETUP_SUMMARY.md` (no es el backend principal).

#### **Beneficios**
- ⏱️ **Ahorro de tiempo**: Reduce horas de trabajo creando preguntas
- 📊 **Cobertura completa**: Asegura que se cubran todos los temas importantes
- 🎯 **Calidad**: Genera preguntas bien estructuradas y alineadas al contenido
- 📚 **Banco creciente**: Acumula preguntas para reutilizar en futuros exámenes

---

### 5. 📝 Banco de Preguntas

EducaApp mantiene un **repositorio organizado** de todas las preguntas:

#### **Tipos de Preguntas**
- **Opción múltiple**: Con varias alternativas (4 opciones, una correcta)
- **Verdadero/Falso**: Afirmaciones para validar
- **Completar el espacio**: Frase con un espacio en blanco a completar
- **Desarrollo**: Preguntas abiertas con respuesta extensa (con respuesta de referencia)

#### **Información de cada Pregunta**
- Texto de la pregunta
- Respuesta correcta
- **Imagen de la pregunta** (opcional) — se almacena de forma permanente en la base de datos como Base64, sin depender del filesystem
- **Imagen de la respuesta** (opcional) — mismo almacenamiento persistente que la imagen de pregunta
- Las imágenes se muestran automáticamente en la vista previa e impresión del examen
- Materia asociada
- Tema y subtema
- Nivel de dificultad (1 a 5)
- Nivel según Taxonomía de Bloom
- Página de referencia en el material fuente
- Documento de origen (Contenido) para trazabilidad completa
- Fecha de creación

#### **Carga Masiva**
Además de la generación por IA, el sistema permite:

- **Importar desde CSV**: Archivo Excel con formato específico
- **Importar desde TXT**: Archivo de texto estructurado
- **Plantillas descargables**: El sistema proporciona plantillas de ejemplo

#### **Búsqueda y Filtrado**
Encuentra rápidamente preguntas usando:

- Filtro por materia
- Filtro por tema (actualiza automáticamente los subtemas disponibles)
- Filtro por subtema
- Filtro por dificultad
- Búsqueda por texto

---

### 6. 📋 Plantillas de Examen

Las plantillas permiten **reutilizar configuraciones** de exámenes:

#### **Configuración de la Plantilla**
- **Datos Institucionales**:
  - Institución, facultad, sede
  - Carrera y materia
  - Profesor responsable

- **Configuración del Examen**:
  - Año académico
  - Tipo: 1er Parcial, 2do Parcial, 3er Parcial, Final, Recuperatorio, Práctico
  - Modalidad: Presencial, Virtual, Domiciliario, Híbrido
  - Turno: Mañana, Tarde, Noche
  - Duración (ej: "90 minutos", "2 horas")

- **Contenido Evaluativo**:
  - Resultados de aprendizaje a evaluar
  - Temas incluidos en el examen
  - Notas y recomendaciones para el docente

- **Personalización Visual**:
  - Logo institucional
  - Estilos personalizados (colores, fuentes)

#### **Beneficios**
- ⚡ **Rapidez**: Crea nuevos exámenes en segundos
- 📏 **Estandarización**: Mantiene formato consistente
- 🔄 **Reutilización**: Usa la misma plantilla para diferentes períodos

---

### 7. 📝 Creación de Exámenes Escritos

#### **Proceso de Creación**

1. **Seleccionar Plantilla** (opcional):
   - Usar plantilla existente
   - O crear desde cero

2. **Configurar el Examen**:
   - Título del examen
   - Instrucciones generales
   - Duración estimada

3. **Seleccionar Preguntas**:
   - Buscar por materia/tema/subtema
   - Ver lista completa de preguntas disponibles
   - Filtrar por dificultad
   - Seleccionar las preguntas deseadas

4. **Organizar el Examen**:
   - Ver preguntas organizadas por tema
   - Calcular puntuación total
   - Verificar distribución de dificultad

5. **Vista Previa**:
   - Ver exactamente cómo se verá impreso
   - Formato profesional con logo institucional
   - Incluye espacio para respuestas

6. **Generar e Imprimir**:
   - Exportar a formato imprimible
   - Guardar para futuras referencias

#### **Editor de Preguntas**

El editor de preguntas cuenta con un diseño en dos columnas:

- **Columna principal** (izquierda): tipo de pregunta, texto, opciones de opción múltiple y texto de respuesta
- **Columna lateral** (derecha): clasificación (materia, tema, subtema, Bloom, dificultad) y fuente documental
- **Imagen de pregunta / respuesta**: si ya hay una imagen guardada se muestra un preview al abrir el editor, con botones para eliminarla o cambiarla. Al seleccionar un archivo nuevo aparece un preview instantáneo antes de guardar.
- Las imágenes se guardan **directamente en la base de datos** (no en el servidor), por lo que sobreviven reinicios del servidor y son compatibles con alojamiento en la nube.

---

### 8. 🎤 Exámenes Orales

Esta funcionalidad permite evaluar a grupos de estudiantes mediante exámenes orales con **distribución automática e inteligente** de preguntas.

#### **Configuración del Examen Oral**

1. **Datos Básicos**:
   - Nombre del cuestionario
   - Materia a evaluar
   - Temas que se incluirán

2. **Organización de Estudiantes**:
   - Número total de estudiantes
   - Cantidad de grupos
   - Estudiantes por grupo (se calcula automáticamente)
   - Preguntas por estudiante (típicamente 3)

#### **Algoritmo Inteligente de Distribución**

El sistema **automáticamente**:

- Distribuye preguntas de forma **equitativa** entre todos los estudiantes
- **Evita repeticiones** dentro del mismo grupo
- Asegura que cada estudiante reciba preguntas de **dificultad balanceada**
- Permite **intercambio de preguntas** entre estudiantes si es necesario
- Garantiza que todos los temas sean evaluados proporcionalmente

#### **Durante el Examen**

El docente puede:

1. **Asignar Nombres**: Poner el nombre real de cada estudiante
2. **Ver Preguntas**: Visualizar las preguntas de cada estudiante
3. **Intercambiar Preguntas**: Si una pregunta ya fue respondida, cambiarla por otra disponible
4. **Evaluar en Tiempo Real**: Calificar cada respuesta mientras el estudiante responde

#### **Sistema de Evaluación**

Para cada pregunta, el docente marca:

- ✅ **Bien** (100% - 1.0 punto): Respuesta correcta y completa
- ⚠️ **Regular** (50% - 0.5 puntos): Respuesta parcialmente correcta
- ❌ **Mal** (0% - 0.0 puntos): Respuesta incorrecta
- ⏸️ **Pendiente**: Aún no se evaluó

#### **Seguimiento Automático**

El sistema **calcula automáticamente**:

- **Porcentaje de Progreso**: Cuántas preguntas ya fueron evaluadas
- **Puntuación Total**: Suma de todos los puntos obtenidos
- **Porcentaje Final**: Nota del estudiante en porcentaje
- **Estadísticas por Estudiante**: Cantidad de respuestas Bien/Regular/Mal

#### **Ventajas del Sistema Oral**
- 📊 **Evaluación justa**: Distribución equitativa de preguntas
- ⏱️ **Tiempo real**: Calificación instantánea
- 📈 **Seguimiento visual**: Barra de progreso por estudiante
- 🔄 **Flexibilidad**: Intercambio de preguntas si es necesario
- 💾 **Registro completo**: Historial de todas las evaluaciones

---

### 9. 🤝 Grupos de Confianza (Compartir Preguntas)

Permite a docentes compartir su banco de preguntas por materia con colegas
de confianza, sin necesidad de pertenecer a la misma institución formal en
el sistema — el alcance es **por grupo de invitación**, no institucional.

#### **Cómo Funciona**

1. **Crear un grupo**: cualquier docente puede crear un grupo de confianza
   (`/grupos/nuevo/`) y queda como su primer miembro.
2. **Invitar colegas**: los miembros aceptados de un grupo pueden invitar a
   otros usuarios por nombre de usuario. La invitación queda **pendiente**
   hasta que la persona invitada la acepta o la rechaza
   (`/grupos/invitaciones/`).
3. **Compartir una materia**: un miembro del grupo elige qué materia
   compartir con el resto — a partir de ahí, los demás miembros pueden ver
   y usar las preguntas de esa materia al armar sus propios exámenes.
4. **Indicador en el menú**: si tenés invitaciones pendientes, el ítem
   "Grupos" del menú lateral muestra un contador en rojo.

#### **Por qué "de confianza" y no institucional**

El diseño original contemplaba compartir preguntas a nivel institución, pero
se optó por grupos explícitos basados en invitación: un docente decide con
quién comparte su banco de preguntas, en vez de que la pertenencia a una
institución en el sistema habilite acceso automático.

---

### 10. 👥 Gestión de Usuarios

EducaApp incluye un sistema completo de administración de usuarios:

#### **Roles de Usuario**

- **Administrador**:
  - Acceso total al sistema
  - Puede crear/editar/eliminar usuarios
  - Gestiona instituciones y configuraciones
  
- **Usuario (Docente)**:
  - Acceso a sus materias y contenidos
  - Crea y gestiona evaluaciones
  - Administra sus preguntas y exámenes

#### **Funciones de Gestión**

- Crear nuevos usuarios
- Asignar roles y permisos
- Editar información de usuarios
- Activar/desactivar usuarios
- Ver listado completo de usuarios

#### **Perfil Personal**

Cada usuario puede:
- Ver y editar sus datos personales
- Cambiar contraseña
- Configurar preferencias
- Ver sus instituciones asignadas

---

### 11. 📊 Consulta y Reportes

#### **Mis Exámenes**
- Ver todos los exámenes creados
- Filtrar por fecha, materia, tipo
- Acceder a exámenes anteriores
- Reutilizar configuraciones

#### **Mis Preguntas**
- Listado completo de preguntas propias
- Editar preguntas existentes
- Eliminar preguntas no deseadas
- Estadísticas de uso

#### **Mis Contenidos**
- Todos los documentos subidos con su estado actual
- **Estado del archivo**: Muestra si el archivo está disponible (🟡 se eliminará al cerrar sesión) o ya fue eliminado (🔘 fecha de eliminación)
- Ver preguntas generadas por documento
- Los metadatos (ISBN, edición, editorial) se conservan aunque el archivo haya sido eliminado

#### **Historial de Instituciones**
- Auditoría completa de cambios
- Quién realizó cada modificación
- Fecha y hora de cambios
- Detalles de actualizaciones

---

## 🔄 Flujos de Trabajo Típicos

### Flujo 1: Crear un Examen Escrito desde Material Nuevo

1. ✅ Subir documento PDF del libro/capítulo
2. ✅ El sistema detecta si ya subiste ese mismo archivo y lo restaura o bloquea el duplicado
3. ✅ El sistema extrae automáticamente ISBN, editorial, año, etc.
4. ✅ La IA analiza el contenido y genera preguntas
5. ✅ Revisar y aprobar las preguntas útiles
6. ✅ Cada pregunta queda vinculada al documento de origen (trazabilidad completa)
7. ✅ Asignar tema/subtema y nivel de Bloom a cada pregunta
8. ✅ Crear plantilla de examen con configuración institucional
9. ✅ Seleccionar preguntas del banco
10. ✅ Vista previa y generación del examen
11. ✅ Imprimir o exportar

> **Nota de almacenamiento**: El archivo físico se elimina al cerrar sesión. El banco de preguntas y los metadatos del libro quedan disponibles permanentemente.

### Flujo 2: Evaluar Estudiantes con Examen Oral

1. ✅ Crear cuestionario oral
2. ✅ Configurar materia, temas, grupos y cantidad de estudiantes
3. ✅ El sistema distribuye preguntas automáticamente
4. ✅ Asignar nombres a los estudiantes
5. ✅ Durante el examen: evaluar cada respuesta (Bien/Regular/Mal)
6. ✅ El sistema calcula automáticamente las notas
7. ✅ Ver estadísticas y progreso en tiempo real
8. ✅ Intercambiar preguntas si es necesario

### Flujo 3: Organizar la Estructura Institucional

1. ✅ Crear institución con logo
2. ✅ Agregar campus/sedes y facultades (embebido en la misma pantalla de edición de la institución)
3. ✅ Definir carreras
4. ✅ Agregar materias
5. ✅ Asociar materias con carreras
6. ✅ Definir resultados de aprendizaje por materia
7. ✅ Crear temas y subtemas
8. ✅ El sistema queda listo para uso

> **Atajo para cuentas nuevas**: en vez de hacer estos pasos a mano, el
> asistente de `/comenzar/` guía la creación de institución, materia y primer
> contenido en un solo flujo (ver "¿Cómo Empezar?" más abajo).

### Flujo 4: Compartir un Banco de Preguntas con Colegas

1. ✅ Crear un grupo de confianza (o aceptar una invitación a uno existente)
2. ✅ Invitar a colegas por nombre de usuario
3. ✅ Elegir qué materia compartir con el grupo
4. ✅ Los demás miembros ya pueden usar esas preguntas al armar sus exámenes

---

## 🎯 Beneficios Clave de EducaApp

### Para Docentes
- ⏱️ **Ahorro de Tiempo**: La IA genera preguntas en minutos en lugar de horas
- 📊 **Mejor Calidad**: Preguntas alineadas a los contenidos y taxonomía de Bloom
- 🎯 **Organización**: Todo centralizado en un solo lugar
- 🔄 **Reutilización**: Banco de preguntas creciente para futuros exámenes
- 📈 **Evaluación Justa**: Distribución equitativa en exámenes orales

### Para Instituciones
- 📏 **Estandarización**: Formatos consistentes en todas las evaluaciones
- 👥 **Gestión Centralizada**: Control de usuarios, roles y permisos
- 🤝 **Bancos Compartidos por Grupo**: Repositorio de preguntas compartido entre colegas de confianza, por materia (grupos de invitación, no institucional — ver sección 9)
- 🔍 **Auditoría**: Historial completo de cambios y modificaciones
- 💾 **Preservación**: Contenidos y evaluaciones guardadas permanentemente

### Para Estudiantes (Indirecto)
- ✅ **Evaluaciones Justas**: Preguntas balanceadas y bien diseñadas
- 📖 **Cobertura Completa**: Evaluación de todos los temas importantes
- 🎓 **Diferentes Niveles**: Preguntas que evalúan desde conocimiento básico hasta pensamiento crítico

---

## 🚀 ¿Cómo Empezar?

**Camino recomendado para una cuenta nueva:**

1. **Registrarse** y entrar a la app — el sistema te lleva directo al
   **asistente de configuración** (`/comenzar/`), un flujo guiado de varios
   pasos que arma institución, materia y primer contenido/examen sin
   necesitar que sepas de antemano por dónde empezar. Se puede salir en
   cualquier momento ("Saltar asistente") y retomar la configuración manual.
2. **Subir Contenidos**: cargar materiales educativos (PDF, Word, PowerPoint)
3. **Generar Preguntas**: usar la IA para crear el banco de preguntas
4. **Crear Evaluaciones**: diseñar exámenes escritos y orales
5. **Evaluar Estudiantes**: utilizar las herramientas de calificación
6. **(Opcional) Compartir**: crear o unirse a un grupo de confianza para
   compartir el banco de preguntas de una materia con colegas

**Configuración manual** (sin pasar por el asistente): crear institución →
sedes/facultades → carreras → materias → resultados de aprendizaje → temas y
subtemas, como se detalla en el Flujo 3 más arriba.

---

## 📞 Soporte

Para más información técnica, consultar:
- **README.md**: Documentación técnica completa
- **DOCUMENT_PROCESSOR_GUIDE.md**: Guía del procesador de documentos (incluye el mecanismo de cita de página real)
- **METADATA_EXTRACTION_FEATURE.md**: Detalles de extracción de metadata
- **LOCAL_AI_SETUP_SUMMARY.md**: Configuración del servidor Ollama de respaldo offline (NO es el backend principal — el default es el fallback compartido Groq/Gemini, ver sección 4)
- **SOLUCION_ERROR_IA.md**: Solución de problemas de conectividad, específico para quienes usan Ollama local
- **EDUCAAPP_INTEGRATION.md**: Referencia técnica de integración de módulos (para desarrolladores)

---

## 📌 Resumen Final

EducaApp es un **ecosistema completo** que:

✅ Organiza la estructura académica institucional  
✅ Gestiona materiales educativos digitales  
✅ Genera preguntas automáticamente usando Inteligencia Artificial  
✅ Permite curaduría y clasificación de preguntas según Taxonomía de Bloom  
✅ Crea exámenes escritos con plantillas reutilizables  
✅ Administra exámenes orales con distribución inteligente  
✅ Evalúa en tiempo real con cálculo automático de notas  
✅ Centraliza todo en un banco de preguntas organizado  
✅ Ofrece reportes y estadísticas completas  

**Todo en un solo sistema, fácil de usar y potenciado por Inteligencia Artificial.**

---

*Documento actualizado: Agosto 2026*  
*Versión del Sistema: 2026.08*
