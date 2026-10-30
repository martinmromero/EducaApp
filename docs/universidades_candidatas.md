# Universidades candidatas para precargar en el catálogo académico

Investigación hecha el 2026-10-29. **Solo investigación**: no se cargó nada en ninguna base, no se tocó código y no se commiteó nada. Documento interno (no es texto de la app).

Método: lectura de páginas puntuales (no scraping masivo) con herramientas de lectura web. Antes de leer cada sitio se consultó su `robots.txt` cuando existía. Todo lo que figura abajo salió de lo que devolvió la página en esa fecha; lo que no se pudo verificar está marcado como **[NO VERIFICADO]** o **[INFERIDO]**. Los conteos "propios" son conteos míos sobre el texto leído, no cifras que informe el sitio.

Limitación de método importante: las lecturas devuelven el texto convertido de la página, no el HTML crudo ni ejecutan JavaScript. Por eso "HTML estático" en las tablas significa "el listado vino en el texto de la respuesta sin ejecutar JS"; no se inspeccionó el código fuente.

---

## 1. Tabla priorizada

Criterio: cantidad probable de docentes que podrían usar la app (AMBA e interior, públicas y privadas grandes) × facilidad de extraer un listado confiable (idealmente con la facultad de cada carrera).

La columna "Gestión" y la ciudad principal son conocimiento general; las sedes marcadas con (v) se verificaron en el sitio. "Carreras" es la cifra aproximada de grado/pregrado según lo leído (la mayoría de los sitios no informan un total oficial).

| # | Universidad | Sigla | Sitio oficial | Gestión | Ciudades / sedes | Carreras (aprox.) | Por qué sirve | URL del listado | Extracción |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Universidad de Buenos Aires | UBA | https://www.uba.ar | Pública | CABA (13 facultades) | ~117-118 distintas (125 entradas; el sitio dice "más de 114") | La más grande del país; 13 facultades con una página cada una | https://www.uba.ar/carreras/1 … `/carreras/13` | **Fácil**: HTML renderizado en servidor, una URL por facultad. El índice `/carreras` no trae lista |
| 2 | Universidad Nacional de Córdoba | UNC | https://www.unc.edu.ar | Pública | Córdoba capital (v) | 99 (el sitio: "cerca de 100") | Listado único alfabético **con la facultad de cada carrera** | https://www.unc.edu.ar/académicas/guia-de-carreras-de-grado-0 | **Fácil**: HTML (Drupal), una sola página. `robots.txt` pide `Crawl-delay: 10` |
| 3 | Universidad Nacional de La Plata | UNLP | https://unlp.edu.ar | Pública | La Plata (17 facultades) | 150 tarjetas (el sitio no da total) | Segunda en tamaño del AMBA ampliado; 17 facultades | https://unlp.edu.ar/carreras_de_grado (8 páginas, `&paged=N`) | **Media**: HTML WordPress paginado; **el listado no muestra la facultad** de cada carrera |
| 4 | Universidad de Palermo | UP | https://www.palermo.edu | Privada | CABA | ~79 títulos | Privada grande de CABA, oferta online/presencial, listados por facultad | https://www.palermo.edu/carreras/ y páginas por facultad | **Media**: HTML, pero nombres de facultad inconsistentes y duplicados entre páginas |
| 5 | Universidad Nacional de La Matanza | UNLaM | https://www.unlam.edu.ar | Pública | San Justo, Gran Bs. As. (conocimiento general; sedes [NO VERIFICADO] en el sitio) | 40 grado + 20 pregrado | Pública grande del conurbano, muchos docentes | https://www.unlam.edu.ar/academicas/?level=1 (grado) y `?level=2` (pregrado) | **Media**: listado limpio, pero el departamento (unidad académica) solo está en la ficha de cada carrera |
| 6 | Universidad Siglo 21 | UES21 | https://21.edu.ar | Privada | Córdoba; modalidad distribuida/online en todo el país | 49 grado + 28 pregrado | Muchísimos docentes y alumnos por modalidad a distancia | https://21.edu.ar/carreras-y-programas?tipo_de_formacion=grado&currentpage=1…5 | **Media**: HTML (HubSpot) paginado; **no tiene facultades**, solo "áreas temáticas" no asignadas por carrera |
| 7 | Universidad del Salvador | USAL | https://www.usal.edu.ar | Privada | CABA (Callao), Pilar, Gobernador Virasoro (Corrientes) (v) | ~80 (propio) en 10 unidades | Privada tradicional grande, listado agrupado por facultad | https://www.usal.edu.ar/carreras-de-grado/ | **Fácil**: HTML, con facultad por carrera (solo se leyeron 15; ver §3) |
| 8 | Universidad Tecnológica Nacional | UTN | https://www.utn.edu.ar | Pública | 30 Facultades Regionales + Rectorado, INSPT y CTDR (33 sedes) (v) | El sitio muestra: 16 ingenierías, 2 licenciaturas, 55 tecnicaturas, 21 ciclos | Enorme base de docentes de ingeniería en todo el país | https://www.utn.edu.ar/es/estudiar-utn?tipo_busqueda=carreras&id_tipos_carreras=1 | **Difícil**: el listado devolvió vacío (probable JS/filtro); además la unidad es la Facultad Regional, no una facultad. No hay nombres de carreras verificados |
| 9 | Pontificia Universidad Católica Argentina | UCA | https://uca.edu.ar | Privada | CABA (Puerto Madero), Rosario, Paraná, Mendoza (según búsquedas, [NO VERIFICADO] en el sitio) | [NO VERIFICADO] | Privada grande; hay una página de carreras por facultad en el sitemap | https://uca.edu.ar/es/todas-las-carreras-de-la-uca | **Difícil**: todas las páginas devolvieron solo el título (renderizado por JS). Requiere navegador |
| 10 | Universidad Católica de Salta | UCASAL | https://www.ucasal.edu.ar | Privada | Salta; Jujuy, Orán, San Luis y "más de 120 sedes" (a distancia) | 93 tarjetas (65 presencial + 28 distancia, con repeticiones; 22 son ciclos) | Mucho alcance del interior y online | https://www.ucasal.edu.ar/menu-oferta-educativa-por-nivel/grado | **Media**: HTML estático, pero sin facultad por carrera (hay una página aparte "por unidad académica"). `robots.txt` bloquea `/carreras/` (las fichas están en `/carrera/`, singular) |
| 11 | Universidad Nacional de Cuyo | UNCuyo | https://www.uncuyo.edu.ar | Pública | Mendoza (Centro Universitario) | [NO VERIFICADO] (12 facultades + 3 institutos) | Pública grande de Cuyo | https://www.uncuyo.edu.ar/estudios/grado | **Media**: tarjetas con facultad en el texto, pero la lectura devolvió solo inicio/fin de la página |
| 12 | Universidad Nacional de Quilmes | UNQ | https://www.unq.edu.ar | Pública | Bernal (Quilmes) y sedes del sur del GBA (v) | 51 (propio) | Pública del conurbano, muchas carreras técnicas y de informática | https://www.unq.edu.ar/carreras/ | **Fácil**: HTML con 4 departamentos (Ciencia y Tecnología, Ciencias Sociales, Economía y Administración, Artes) |
| 13 | Universidad Nacional de Tres de Febrero | UNTREF | https://untref.edu.ar | Pública | Sáenz Peña (Caseros) y CABA (v) | 36 (propio) | Pública del AMBA | https://untref.edu.ar/carreras | **Media**: HTML, pero sin unidad académica por carrera |
| 14 | Universidad Nacional de Lomas de Zamora | UNLZ | https://www.unlz.edu.ar | Pública | Lomas de Zamora (v) | ~49 viñetas (con repeticiones) | Pública del sur del GBA, 5 facultades | https://www.unlz.edu.ar/?page_id=2363 | **Media**: HTML con facultad por carrera, pero cada viñeta mezcla licenciatura + profesorado + tecnicatura |
| 15 | Universidad Austral | Austral | https://www.austral.edu.ar | Privada | Pilar, CABA, Rosario, Nordelta | 24 tarjetas en Pilar + 8 en Rosario (propio) | Privada de perfil alto, facultades claras | https://www.austral.edu.ar/admisiones/ | **Media**: HTML; facultad solo inferible por la ruta de cada URL |
| 16 | Universidad de Belgrano | UB | https://www.ub.edu.ar | Privada | CABA (Torre Universitaria, Villanueva) (v) | 25 (propio) | Privada de CABA | https://ub.edu.ar/distribucion-carreras-de-grado | **Media**: HTML con áreas, que no coinciden siempre con las facultades de la URL |
| 17 | Instituto Tecnológico de Buenos Aires | ITBA | https://www.itba.edu.ar | Privada | CABA (grado: sede [NO VERIFICADO]) | 13 | Ingenierías, pocos pero fáciles de cargar | https://www.itba.edu.ar/grado/ | **Fácil**: HTML; sin facultad/escuela por carrera (una sola unidad "ITBA" alcanzaría) |
| 18 | Universidad Católica de Córdoba | UCC | https://www.ucc.edu.ar | Privada | Córdoba y Río Cuarto (v) | [NO VERIFICADO] | Privada grande del interior | https://ucc.edu.ar/propuesta-academica/grado-y-pregrado | **Difícil**: catálogo vacío para el lector (JS). Solo hay una lista parcial en `/ingreso/directo` |
| 19 | Universidad Blas Pascal | UBP | https://www.ubp.edu.ar | Privada | Córdoba ([NO VERIFICADO]) | [NO VERIFICADO] | Privada de Córdoba | https://www.ubp.edu.ar/a-z/ (índice A-Z) | **Difícil**: el listado real de grado dio HTTP 500; solo se leyó un índice alfabético que mezcla cursos |
| 20 | Universidad Nacional de Rosario | UNR | https://www.unr.edu.ar | Pública | Rosario | [NO VERIFICADO] | Pública grande del interior | [NO VERIFICADO] | **No se pudo leer**: error SSL (handshake) en todas las URL desde la herramienta. Habría que probar desde un navegador |

No se pudieron leer (por error o restricción) y quedan pendientes: **UNR** (error SSL) y **UNSAM** (la portada devolvió HTTP 402 y `robots.txt` 404).

No investigadas en esta pasada (siguiente tanda posible): UNT (Tucumán), UNS (Bahía Blanca), UNMdP, UNNOBA, UNLPam, UNaM, UNNE, UNSL, UNRC, UCEMA, UdeSA, Universidad Kennedy, UMSA, Maimónides, Favaloro, UADE/UAI (ya cargadas por el usuario).

### Orden sugerido para cargar

1. **UNC** (listado más limpio: carrera + facultad en una sola página).
2. **UBA** (13 páginas homogéneas).
3. **UNLP** (grande, pero hay que resolver la facultad de cada carrera; ver §2.3).
4. **UP**, **UNLaM**, **Siglo 21** (útiles, con un trabajo de normalización).
5. **USAL**, **UNQ**, **ITBA**, **UNLZ** (fáciles; completar lectura).
6. **UTN**, **UCA**, **UCC**: dejar para una pasada con navegador (JS).

---

## 2. Listados en bruto de las 6 mejores

Convenciones: `[T]` = tecnicatura / pregrado; `[CCC]` = ciclo de complementación curricular; el resto son licenciaturas, profesorados, ingenierías, etc. Los nombres están **tal como aparecen en el sitio** (incluidas mayúsculas irregulares y erratas). Los nombres de facultad son los encabezados que muestra cada página; en muchos casos no se pudo confirmar el nombre legal completo (por ejemplo, falta el prefijo "Facultad de").

### 2.1 Universidad Nacional de Córdoba (UNC)

- Fuente: https://www.unc.edu.ar/académicas/guia-de-carreras-de-grado-0 (título "Guia de Carreras de Grado"). HTTP 200, HTML. Facultades: https://www.unc.edu.ar/académicas/facultades-de-la-unc
- `robots.txt` (https://www.unc.edu.ar/robots.txt): `Crawl-delay: 10`; ningún Disallow sobre `/académicas/`.
- El sitio dice "cerca de 100 carreras de Grado"; conteo propio: 99 entradas. La guía enlaza a un PDF (`Guía de estudios 2025 FINAL_v2_1.pdf`) que **no se abrió**.
- 15 facultades (página de facultades): Arquitectura, Urbanismo y Diseño; Artes; Ciencias Agropecuarias; Ciencias de la Comunicación; Ciencias Económicas; Ciencias Exactas, Físicas y Naturales; Ciencias Médicas; Ciencias Químicas; Ciencias Sociales; Derecho; Filosofía y Humanidades; Lenguas; Matemática, Astronomía, Física y Computación; Odontología; Psicología.
- Observaciones del sitio: "Licenciatura en Lengua y Literatura Italianas" enlaza a una URL de inglesas (probable error de enlace); "Licenciatura en Matemática" y "Licenciatura Universitaria en Matemática Aplicada" enlazan a la misma página. Las 3 tecnicaturas y el ciclo figuran dentro del listado de grado del propio sitio.

**Facultad de Derecho**
- Abogacía
- Notariado
- Profesorado en Ciencias Jurídicas

**Facultad de Arquitectura, Urbanismo y Diseño**
- Arquitectura
- Diseño Industrial
- Licenciatura en Diseño del Paisaje

**Facultad de Ciencias Químicas**
- Bioquímica
- Farmacia
- Licenciatura en Biotecnología
- Licenciatura en Química

**Facultad de Filosofía y Humanidades**
- Ciclo de Licenciatura en Ciencias de la Educación `[CCC]`
- Licenciatura en Antropología
- Licenciatura en Archivología
- Licenciatura en Ciencias de la Educación
- Licenciatura en Filosofía
- Licenciatura en Geografía
- Licenciatura en Historia
- Licenciatura en Letras Clásicas
- Licenciatura en Letras Modernas
- Profesorado en Ciencias de la Educación
- Profesorado en Filosofía
- Profesorado en Geografía
- Profesorado en Historia
- Profesorado en Letras Clásicas
- Profesorado en Letras Modernas

**Facultad de Ciencias Exactas, Físicas y Naturales**
- Ciencias Biológicas
- Ciencias Geológicas
- Constructor
- Ingeniería Aeroespacial
- Ingeniería Ambiental
- Ingeniería Biomédica
- Ingeniería Civil
- Ingeniería Electromecánica
- Ingeniería Electrónica
- Ingeniería en Agrimensura
- Ingeniería en Computación
- Ingeniería Industrial
- Ingeniería Mecánica
- Ingeniería Química
- Profesorado en Ciencias Biológicas

**Facultad de Ciencias Económicas**
- Contador/a Público/a
- Licenciatura en Administración
- Licenciatura en Economía
- Licenciatura en Gestión Universitaria
- Profesorado en Ciencias Económicas

**Facultad de Ciencias Agropecuarias**
- Ingeniería Agronómica
- Ingeniería Zootecnista
- Licenciatura Universitaria en Agroalimentos
- Licenciatura Universitaria en Diseño del Paisaje

**Facultad de Artes**
- Licenciatura en Artes Visuales
- Licenciatura en Cine y Artes Audiovisuales
- Licenciatura en Composición Musical
- Licenciatura en Dirección Coral
- Licenciatura en Educación Musical
- Licenciatura en Interpretación Instrumental
- Licenciatura en Teatro
- Profesorado en Educación Musical
- Profesorado en Educación Plástica y Visual
- Profesorado en Teatro

**Facultad de Ciencias Sociales**
- Licenciatura en Ciencia Política
- Licenciatura en Sociología
- Licenciatura en Trabajo Social

**Facultad de Matemática, Astronomía, Física y Computación**
- Licenciatura en Ciencias de la Computación
- Licenciatura en Física
- Licenciatura en Hidrometeorología
- Licenciatura en Matemática
- Licenciatura Universitaria en Astronomía
- Licenciatura Universitaria en Matemática Aplicada
- Profesorado en Física
- Profesorado en Matemática

**Facultad de Ciencias de la Comunicación**
- Licenciatura en Comunicación Social
- Profesorado en Comunicación Social

**Facultad de Ciencias Médicas**
- Licenciatura en Enfermería
- Licenciatura en Fonoaudiología
- Licenciatura en Kinesiología y Fisioterapia
- Licenciatura en Nutrición
- Licenciatura en Producción de Bioimágenes
- Medicina
- Tecnicatura en Instrumentación Quirúrgica `[T]`
- Tecnicatura en Laboratorio y Hemoterapia `[T]`
- Tecnicatura en Radiología `[T]`

**Facultad de Lenguas**
- Licenciatura en Español Lengua Materna y Lengua Extranjera
- Licenciatura en Lengua y Literatura Alemanas
- Licenciatura en Lengua y Literatura Francesas
- Licenciatura en Lengua y Literatura Inglesas
- Licenciatura en Lengua y Literatura Italianas
- Profesorado de Lengua Alemana
- Profesorado de Lengua Francesa
- Profesorado de Lengua Inglesa
- Profesorado de Lengua Italiana
- Profesorado de Portugués
- Profesorado en Español Lengua Materna y Lengua Extranjera
- Traductorado Público Nacional de Alemán
- Traductorado Público Nacional de Francés
- Traductorado Público Nacional de Inglés
- Traductorado Público Nacional de Italiano

**Facultad de Psicología**
- Licenciatura en Psicología
- Profesorado en Psicología

**Facultad de Odontología**
- Odontología

(Total: 99; el agrupamiento es el literal "Carrera | Facultad" que devolvió la página, reordenado por facultad.)

### 2.2 Universidad de Buenos Aires (UBA)

- Fuente: una página por facultad, `https://www.uba.ar/carreras/N` con N = 1 a 13 (todas HTTP 200). El índice `https://www.uba.ar/carreras` solo trae menú y pie. Cifra del sitio (https://www.uba.ar/servicios): "trece facultades con más de 114 carreras de grado".
- `robots.txt` (https://www.uba.ar/robots.txt): `User-agent: *` / `Disallow:` vacío.
- Conteo propio: 125 entradas sumando las 13 listas; 117-118 nombres distintos porque varias figuran en más de una facultad. No coincide con el "más de 114" del sitio; no se sabe si el sitio excluye algún tipo de programa.
- Los encabezados que muestra cada página **no llevan el prefijo "Facultad de"**: el nombre legal completo no se confirmó. Los nombres de carreras tienen una errata de origen: "Ciencias Geologógicas".
- No hay fecha visible en el contenido; no se sabe qué tan actual es.
- Los textos entre paréntesis son literales del sitio.

**1) Agronomía** — https://www.uba.ar/carreras/1
- Agronomía
- Licenciatura en Ciencias Ambientales
- Licenciatura en Economía y Administración Agrarias
- Licenciatura en Gestión de Agroalimentos (compartida con FVET)
- Licenciatura en Planificación y Diseño del Paisaje (compartida con FADU)
- Licenciatura en Biotecnología (compartida con FFyB, FCEN y FVET)
- Tecnicatura Universitaria en Producción Florihortícola `[T]`
- Tecnicatura Universitaria en Jardinería `[T]`
- Tecnicatura Universitaria en Producción Vegetal Orgánica `[T]`
- Tecnicatura Universitaria en Turismo Rural `[T]`
- Profesorado de Enseñanza Secundaria y Superior en Ciencias Ambientales

**2) Arquitectura, Diseño y Urbanismo** — https://www.uba.ar/carreras/2
- Arquitectura
- Diseño de Indumentaria
- Diseño de Imagen y Sonido
- Diseño Gráfico
- Diseño Industrial
- Diseño Textil
- Licenciatura en Planificación y Diseño del Paisaje (compartido con FAUBA)

**3) Ciencias Económicas** — https://www.uba.ar/carreras/3
- Contador Público
- Actuario
- Licenciatura en Administración
- Licenciatura en Economía
- Licenciatura en Sistemas de Información de las Organizaciones
- Tecnicatura Universitaria en Gestión y Análisis de Datos en Organizaciones `[T]`

**4) Ciencias Exactas y Naturales** — https://www.uba.ar/carreras/4
- Licenciatura en Ciencias Biológicas
- Licenciatura en Ciencias de Datos
- Licenciatura en Ciencias de la Atmósfera
- Licenciatura en Ciencias de la Computación
- Licenciatura en Ciencias Físicas
- Licenciatura en Ciencias Geológicas
- Licenciatura en Ciencias Matemáticas
- Licenciatura en Ciencias Químicas
- Licenciatura en Ciencias Oceanográficas
- Licenciatura en Paleontología
- Licenciatura en Ciencia y Tecnología de Alimentos (compartida con FFYB)
- Licenciatura en Biotecnología (compartida con FFyB, Agronomía y FVET)
- Profesorado de Enseñanza Media y Superior en Ciencias de la Atmósfera
- Profesorado de Enseñanza Media y Superior en Ciencias Geologógicas (errata de origen)
- Profesorado Universitario en Biología
- Profesorado Universitario en Computación
- Profesorado Universitario en Física
- Profesorado Universitario en Matemática
- Profesorado Universitario en Química
- Profesorado Universitario para la Educación Secundaria en Biología y Química
- Profesorado Universitario para la Educación Secundaria en Computación y Física
- Profesorado Universitario para la Educación Secundaria en Física y Matemática
- Profesorado Universitario para la Educación Secundaria en Matemática y Computación
- Profesorado Universitario para la Educación Secundaria en Química y Física

**5) Ciencias Sociales** — https://www.uba.ar/carreras/5
- Licenciatura en Ciencias de la Comunicación
- Licenciatura en Ciencia Política
- Licenciatura en Relaciones del Trabajo
- Licenciatura en Trabajo Social
- Sociología
- Profesorado de Enseñanza Media y Superior en Ciencias de la Comunicación
- Profesorado de Enseñanza Media y Superior en Ciencia Política
- Profesorado de Enseñanza Media y Superior en Relaciones del Trabajo
- Profesorado de Enseñanza Media y Superior en Trabajo Social
- Profesor/a de Enseñanza Secundaria, Normal y Especial en Sociología

**6) Ciencias Veterinarias** — https://www.uba.ar/carreras/6
- Veterinaria
- Licenciatura en Gestión de Agroalimentos (Compartida con FAUBA)
- Licenciatura en Biotecnología (compartida con FCEN, Agronomía y FFyB)
- Tecnicatura Universitaria en Gestión Integral de Bioterios (Compartida con FFYB) `[T]`

**7) Derecho** — https://www.uba.ar/carreras/7
- Abogacía
- Traductorado Público
- Profesorado para la Enseñanza Media y Superior en Ciencias Jurídicas
- Calígrafo Público

**8) Farmacia y Bioquímica** — https://www.uba.ar/carreras/8
- Bioquímica
- Farmacia
- Licenciatura en Ciencia y Tecnología de Alimentos (Compartida con FCEN)
- Licenciatura en Biotecnología (compartida con FCEN, Agronomía y FVET)
- Tecnicatura Universitaria en Óptica y Contactología `[T]`
- Tecnicatura Universitaria en Medicina Nuclear `[T]`
- Tecnicatura Universitaria en Gestión Integral de Bioterios (Compartida con FVET) `[T]`

**9) Filosofía y Letras** — https://www.uba.ar/carreras/9
- Licenciatura en Artes
- Licenciatura en Ciencias Antropológicas
- Licenciatura en Ciencias de la Educación
- Licenciatura en Ciencia de la Información (Ciclo de Complementación Curricular) `[CCC]`
- Licenciatura en Filosofía
- Licenciatura en Geografía
- Licenciatura en Historia
- Licenciatura en Letras
- Edición (así figura, sin "Licenciatura en")
- Profesorado en Enseñanza Secundaria y Superior en Artes
- Profesorado de Enseñanza Secundaria y Superior en Ciencias Antropológicas
- Profesorado en Enseñanza Secundaria y Superior en Ciencias de la Educación
- Profesorado de Enseñanza Secundaria y Superior en Geografía
- Profesorado en Filosofía
- Profesorado en Historia
- Tecnicatura Universitaria en Acompañamiento de Trayectorias Educativas `[T]`
- Tecnicatura Universitaria en Producción y Gestión de las Artes `[T]`
- Tecnicatura Universitaria en Archivística `[T]`
- Tecnicatura Universitaria en Bibliotecología `[T]`

**10) Ingeniería** — https://www.uba.ar/carreras/10
- Ingeniería Civil
- Ingeniería en Alimentos
- Ingeniería en Energía Eléctrica
- Ingeniería Electrónica
- Ingeniería en Agrimensura
- Ingeniería en Informática
- Ingeniería en Petróleo
- Ingeniería Industrial
- Ingeniería Mecánica
- Ingeniería Naval
- Ingeniería Química
- Licenciatura en Análisis de Sistemas
- Bioingeniería

**11) Ciencias Médicas** — https://www.uba.ar/carreras/11
- Medicina
- Licenciatura en Enfermería
- Licenciatura en Fonoaudiología
- Licenciatura en Kinesiología y Fisiatría
- Licenciatura en Nutrición
- Licenciatura en Obstetricia
- Licenciatura en Podología
- Licenciatura en Producción de Bioimágenes
- Licenciatura en Enfermería (Ciclo de Complementación Curricular) `[CCC]`
- Tecnicatura Universitaria en Podología `[T]`
- Tecnicatura Universitaria en Hemoterapia e Inmunohematología `[T]`
- Tecnicatura Universitaria en Instrumentación Quirúrgica `[T]`
- Tecnicatura Universitaria en Cosmetología Facial y Corporal `[T]`
- Tecnicatura Universitaria en Anestesia `[T]`
- Tecnicatura Universitaria en Prácticas Cardiológicas `[T]`

**12) Odontología** — https://www.uba.ar/carreras/12
- Odontología

**13) Psicología** — https://www.uba.ar/carreras/13
- Licenciatura en Psicología
- Licenciatura en Musicoterapia
- Terapia Ocupacional
- Profesorado de Enseñanza Media y Superior en Psicología

### 2.3 Universidad Nacional de La Plata (UNLP)

- Fuente: https://unlp.edu.ar/carreras_de_grado (página 1) y las páginas 2-8 con la misma base: `https://unlp.edu.ar/?areadisciplinarbuscadorcgyp=all&duracionbuscadorcgyp=all&facultadbuscadorcgyp=all&post_type=carrera&s&tipobuscadorcgyp=all&paged=N` (N = 2 a 8; HTTP 200 todas).
- `robots.txt` (https://unlp.edu.ar/robots.txt): `Disallow: /wp-admin/` (con `Allow: /wp-admin/admin-ajax.php`); no bloquea el listado.
- Conteo propio: **150 tarjetas** (páginas 1-7 con 20 y la 8 con 10). El sitio no informa un total. Hay una tarjeta por cada orientación (ver abajo), por eso el número sube respecto de "carreras" en sentido estricto.
- **El listado no muestra la facultad de cada carrera.** Abajo se agrupa por el dominio del enlace de cada tarjeta, lo cual es **[INFERIDO]**, no lo dice el sitio, y falla en al menos un caso (ver nota de Fonoaudiología). Los valores de URL del filtro "Facultad" no se pudieron ver.
- Nombres de las 17 facultades (https://unlp.edu.ar/institucional/unlp/facultades_y_colegios-83-5083/, página con fecha de publicación 2008, puede estar desactualizada): Facultad de Arquitectura y Urbanismo; Facultad de Artes; Facultad de Ciencias Agrarias y Forestales; Facultad de Ciencias Astronómicas y Geofísicas; Facultad de Ciencias Económicas; Facultad de Ciencias Exactas; Facultad de Ciencias Jurídicas y Sociales; Facultad de Ciencias Médicas; Facultad de Ciencias Naturales y Museo; Facultad de Ciencias Veterinarias; Facultad de Humanidades y Ciencias de la Educación; Facultad de Informática; Facultad de Ingeniería; Facultad de Odontología; Facultad de Periodismo y Comunicación Social; Facultad de Psicología; Facultad de Trabajo Social. (Coinciden con las del filtro del listado, que usa nombres abreviados.)
- Las "or." son orientaciones: cada orientación es **una tarjeta separada** en el sitio (aquí se escriben en una línea entre llaves para no repetir).
- URL de cada carrera: el enlace de cada tarjeta (apunta al sitio de la facultad). En las tarjetas con varias orientaciones el enlace es el mismo.

**Facultad de Arquitectura y Urbanismo** (fau.unlp.edu.ar)
- Arquitectura — https://www.fau.unlp.edu.ar/grado/plan-vi/

**Facultad de Artes** (fba / www2.fba.unlp.edu.ar)
- Diseño Industrial — https://fba.unlp.edu.ar/diseno-industrial/
- Licenciatura en Artes Audiovisuales or. {Dirección de Fotografía; Guión; Realización; Teoría y Crítica} — https://fba.unlp.edu.ar/licenciatura-en-artes-audiovisuales/
- Licenciatura en Artes Plásticas or. {Cerámica; Dibujo; Escenografía; Escultura; Grabado; Muralismo; Pintura} — https://fba.unlp.edu.ar/licenciatura-en-artes-visualea/ (así figura la URL)
- Licenciatura en Diseño en Comunicación Visual — https://fba.unlp.edu.ar/diseno-en-comunicacion-visual/
- Licenciatura en Diseño Multimedial — https://fba.unlp.edu.ar/licenciatura-en-diseno-multimedial/
- Licenciatura en Historia de las Artes, Orientación Artes Visuales — https://fba.unlp.edu.ar/licenciatura-en-historia-del-arte/
- Licenciatura en Música or. {Composición; Dirección Coral; Dirección Orquestal; Educación Musical; Guitarra; Música Popular; Piano} — https://fba.unlp.edu.ar/composicion/ (y una URL propia por orientación)
- Profesorado en Artes Audiovisuales — https://fba.unlp.edu.ar/profesorado-en-artes-audiovisuales/
- Profesorado en Artes Plásticas or. {Cerámica; Dibujo; Escenografía; Escultura; Grabado; Muralismo; Pintura} — https://fba.unlp.edu.ar/profesorado-en-artes-visuales/
- Profesorado en Diseño en Comunicación Visual — https://fba.unlp.edu.ar/profesorado-en-diseno-en-comunicacion-visual/
- Profesorado en Diseño Industrial — https://fba.unlp.edu.ar/profesorado-en-diseno-industrial-2/
- Profesorado en Diseño Multimedial — https://fba.unlp.edu.ar/profesorado-en-diseno-multimedial/
- Profesorado en Historia de las Artes con orientación en Artes Visuales — https://fba.unlp.edu.ar/profesorado-en-en-historia-del-arte/
- Profesorado en Música or. {Composición; Dirección Coral; Dirección Orquestal; Educación Musical; Guitarra; Música Popular; Piano} — mismas URL que la licenciatura
- Tecnicatura en Música Popular `[T]` — https://www2.fba.unlp.edu.ar/musica/tecnicatura/
- Tecnicatura Universitaria en Fotografía `[T]` — https://www2.fba.unlp.edu.ar/artesvisuales/fotografia/
- Tecnicatura Universitaria en Sonido y Grabación `[T]` — https://fba.unlp.edu.ar/tecnicatura-en-sonido-y-grabacion/

**Facultad de Ciencias Agrarias y Forestales** (agro.unlp.edu.ar)
- Ingeniería Agronómica — https://www.agro.unlp.edu.ar/ensenanza/carreras/ingenieria-agronomica/
- Ingeniería Forestal — https://www.agro.unlp.edu.ar/ensenanza/carreras/ingenieria-forestal/
- Tecnicatura Universitaria en Agroecología `[T]` — https://www.agro.unlp.edu.ar/ensenanza/carreras/tecnicatura-universitaria-en-agroecologia/
- Tecnicatura Universitaria en Cultivos Protegidos y Ambientes Controlados `[T]` — https://www.agro.unlp.edu.ar/ensenanza/carreras/tecnicatura-universitaria-en-cultivos-protegidos-y-ambientes-controlados/

**Facultad de Ciencias Astronómicas y Geofísicas** (fcaglp.unlp.edu.ar)
- Geofísica — https://www.fcaglp.unlp.edu.ar/index.php/carreras-grado/geofisica/
- Licenciatura en Astronomía — https://www.fcaglp.unlp.edu.ar/index.php/carreras-grado/astronomia/
- Licenciatura en Meteorología y Ciencias de la Atmósfera — https://www.fcaglp.unlp.edu.ar/index.php/carreras-grado/meteorologia/

**Facultad de Ciencias Económicas** (econo.unlp.edu.ar)
- Ciencia de Datos en Organizaciones — https://www.econo.unlp.edu.ar/cdo
- Contador Público — https://www.econo.unlp.edu.ar/contador_publico
- Licenciatura en Administración — https://www.econo.unlp.edu.ar/licenciatura_en_administracion
- Licenciatura en Economía — https://www.econo.unlp.edu.ar/licenciatura_en_economia
- Licenciatura en Turismo — https://www.econo.unlp.edu.ar/licenciatura_en_turismo
- Tecnicatura en Cooperativismo `[T]` — https://www.econo.unlp.edu.ar/tecnicatura_en_cooperativismo

**Facultad de Ciencias Exactas** (exactas.unlp.edu.ar)
- Farmacia — https://www.exactas.unlp.edu.ar/farmacia
- Licenciatura en Bioquímica — https://www.exactas.unlp.edu.ar/licenciatura_en_bioquimica
- Licenciatura en Biotecnología y Biología Molecular — https://www.exactas.unlp.edu.ar/licenciatura_en_biotecnologia_y_biologia_molecular
- Licenciatura en Ciencia y Tecnología de Alimentos — https://www.exactas.unlp.edu.ar/alimentos
- Licenciatura en Física — https://www.exactas.unlp.edu.ar/licenciatura_en_fisica
- Licenciatura en Física Médica — https://www.exactas.unlp.edu.ar/licenciatura_en_fisica_medica
- Licenciatura en Matemática — https://www.exactas.unlp.edu.ar/licenciatura_en_matematicas
- Licenciatura en Óptica Ocular y Optometría — https://www.exactas.unlp.edu.ar/licenciatura_en_optica_ocular_y_optometria
- Licenciatura en Química — https://www.exactas.unlp.edu.ar/licenciatura_en_quimica
- Licenciatura en Química y Tecnología Ambiental — https://www.exactas.unlp.edu.ar/licenciatura_en_quimica_y_tecnologia_ambiental
- Tecnicatura Universitaria en Alimentos `[T]` — https://www.exactas.unlp.edu.ar/tecnicatura_universitaria_en_alimentos
- Tecnicatura Universitaria en Química `[T]` — https://www.exactas.unlp.edu.ar/tecnicatura_universitaria_en_quimica

**Facultad de Ciencias Jurídicas y Sociales** (jursoc.unlp.edu.ar)
- Abogacía — https://jursoc.unlp.edu.ar/index.php/estudiantes/informacion/carreras.html
- Escribanía — misma URL
- Licenciatura en Gestión de Recursos para Instituciones Universitarias (sólo para trabajadores no docentes) — https://jursoc.unlp.edu.ar/index.php/carreras-ingreso.html
- Técnico Superior Universitario de Martillero público y Corredor `[T]` — https://jursoc.unlp.edu.ar/index.php/estudiantes/informacion/carreras.html

**Facultad de Ciencias Médicas** (med.unlp.edu.ar)
- Enfermería Universitaria — https://www.med.unlp.edu.ar/index.php/carreras/enfermeria-universitaria/plan-de-estudio
- Licenciatura en Nutrición — https://www.med.unlp.edu.ar/index.php/carreras/lic-en-nutricion/plan-de-estudio
- Licenciatura en Obstetricia — https://www.med.unlp.edu.ar/index.php/carreras/lic-en-obstetricia/plan-de-estudio
- Medicina — https://www.med.unlp.edu.ar/index.php/carreras/medicina/plan-de-estudio
- Tecnicatura en Prácticas Cardiológicas `[T]` — https://www.med.unlp.edu.ar/index.php/carreras/tec-en-practicas-cardiologicas/plan-de-estudio

**Facultad de Ciencias Naturales y Museo** (fcnym.unlp.edu.ar)
- Licenciatura en Antropología — https://www.fcnym.unlp.edu.ar/grado/carreras/licenciatura-en-antropologia/
- Licenciatura en Biología or. {Botánica; Ecología; Paleontología; Zoología} — https://www.fcnym.unlp.edu.ar/grado/carreras/licenciatura-en-biologia-orientacion-<orientación>/
- Licenciatura en Geología — https://www.fcnym.unlp.edu.ar/grado/carreras/licenciatura-en-geologia/
- Licenciatura en Geoquímica — https://www.fcnym.unlp.edu.ar/grado/carreras/licenciatura-en-geoquimica/

**Facultad de Ciencias Veterinarias** (fcv.unlp.edu.ar)
- Medicina Veterinaria — https://www.fcv.unlp.edu.ar/index.php/carrera-de-medicina-veterinaria/
- Microbiología — https://www.fcv.unlp.edu.ar/index.php/carrera-de-microbiologia/

**Facultad de Humanidades y Ciencias de la Educación** (fahce.unlp.edu.ar; URL base `https://www.fahce.unlp.edu.ar/facultad/secretarias-y-prosecretarias/academica/deptos/<depto>/carreras/<carrera>`)
- Licenciatura en Bibliotecología y Ciencia de la Información
- Licenciatura en Cs. de la Educación
- Licenciatura en Educación Física
- Licenciatura en Filosofía
- Licenciatura en Francés Orientación Lingüística
- Licenciatura en Francés Orientación Literaria
- Licenciatura en Geografía
- Licenciatura en Historia
- Licenciatura en Inglés Orientación Lingüística
- Licenciatura en Inglés Orientación Literaria
- Licenciatura en Letras
- Licenciatura en Sociología
- Profesorado de Bibliotecología y Ciencia de la Información
- Profesorado de Ciencias Biológicas
- Profesorado de Física
- Profesorado de Matemática
- Profesorado de Química
- Profesorado en Ciencias de la Educación
- Profesorado en Educación Física
- Profesorado en Filosofía
- Profesorado en Geografía
- Profesorado en Historia
- Profesorado en Lengua y Literatura Francesas
- Profesorado en Lengua y Literatura inglesas
- Profesorado en Letras
- Profesorado en Portugués
- Profesorado en Sociología
- Traductorado Público Nacional en Lengua Francesa
- Traductorado Público Nacional en Lengua Inglesa

**Facultad de Informática** (info.unlp.edu.ar, ic.info.unlp.edu.ar)
- Analista en Tecnologías de la Información y la Comunicación `[T]` — https://www.info.unlp.edu.ar/analista-en-tic/
- Analista Programador Universitario `[T]` — https://www.info.unlp.edu.ar/analista-programador-universitario/
- Ingeniería en Computación — https://ic.info.unlp.edu.ar/alcances-del-titulo-y-competencias-profesionales-de-ingenieria-en-computacion/
- Licenciatura en Informática — https://www.info.unlp.edu.ar/carreras-de-grado-lic-en-informatica/
- Licenciatura en Sistemas — https://www.info.unlp.edu.ar/licenciatura-en-sistemas/

(Clasificar "Analista…" como pregrado/`[T]` es mío, por el nombre; la página no lo dice.)

**Facultad de Ingeniería** (ing.unlp.edu.ar; URL base `https://ing.unlp.edu.ar/grado/carreras/<slug>/`)
- Ingeniería Aeroespacial
- Ingeniería Civil
- Ingeniería Electromecánica
- Ingeniería Electrónica
- Ingeniería en Agrimensura
- Ingeniería en Energía Eléctrica
- Ingeniería en Materiales
- Ingeniería en Telecomunicaciones
- Ingeniería Hidráulica
- Ingeniería Industrial
- Ingeniería Mecánica
- Ingeniería Química

**Facultad de Odontología** (folp.unlp.edu.ar)
- Odontología — https://www.folp.unlp.edu.ar/plandeestudios
- Tecnicatura Universitaria en Asistencia Odontológica `[T]` — https://www.folp.unlp.edu.ar/asistenciaodontologica
- Tecnicatura Universitaria en Prótesis de Laboratorio Odontológico `[T]` — https://www.folp.unlp.edu.ar/protesisdelaboratorio

**Facultad de Periodismo y Comunicación Social** (perio.unlp.edu.ar)
- Licenciatura en Comunicación Social con Orientación Periodismo, Producción de contenidos y Gestión de Medios — https://perio.unlp.edu.ar/academica/carreras/licenciatura/
- Licenciatura en Comunicación Social con Orientación Planificación y Gestión de la Comunicación en Organizaciones — misma URL
- Profesorado en Comunicación Social — https://perio.unlp.edu.ar/academica/carreras/profesorado/
- Tecnicatura Superior Universitaria en Comunicación Digital `[T]` — https://perio.unlp.edu.ar/academica/carreras/comunicacion-digital/
- Tecnicatura Superior Universitaria en Comunicación Pública y Política `[T]` — https://perio.unlp.edu.ar/academica/carreras/comunicacion-publica-y-politica/
- Tecnicatura Superior Universitaria en Periodismo Deportivo `[T]` — https://perio.unlp.edu.ar/academica/carreras/periodismo-deportivo/
- Tecnicatura Universitaria en Comunicación Popular `[T]` — https://perio.unlp.edu.ar/academica/carreras/comunicacion-popular/

**Facultad de Psicología** (psico.unlp.edu.ar)
- Licenciatura en Psicología — https://www.psico.unlp.edu.ar/carreras
- Profesorado en Psicología — https://www.psico.unlp.edu.ar/carreras

**Facultad de Trabajo Social** (trabajosocial.unlp.edu.ar) — todas apuntan a https://trabajosocial.unlp.edu.ar/carreras-2/
- Licenciatura en Trabajo Social
- Profesorado en Trabajo Social
- Tecnicatura en Gestión Comunitaria del Riesgo `[T]`
- Licenciatura en Fonoaudiología — **[DUDOSO]**: el enlace de la tarjeta va a la web de Trabajo Social, pero la facultad real no se verificó (el dominio no es confiable en este caso).

### 2.4 Universidad de Palermo (UP)

- Fuentes: https://www.palermo.edu/carreras/ (lista general por facultad, online y presencial), https://www.palermo.edu/carreras/negocios/index.html, https://www.palermo.edu/cienciassociales/carreras.html?tipo=grado, https://www.palermo.edu/ingenieria/, https://www.palermo.edu/derecho/, https://www.palermo.edu/dyc/, https://www.palermo.edu/arquitectura/ (todas HTTP 200).
- `robots.txt` (https://www.palermo.edu/robots.txt): `Disallow` para `/RSU/201*`, `/propuesta/`, `/webemails/`, `/demo/` y varias rutas bajo `/dyc/` y `/economicas/`. **No se leyó** `https://www.palermo.edu/propuesta/cienciassociales/carreras.html?tipo=grado` (bloqueada). Ninguna ruta leída está bloqueada.
- Conteo propio: **79 títulos distintos** (67 de grado, 10 ciclos de complementación, 2 de carrera corta/pregrado); 77 si dos "Management" resultan ser el mismo programa que otros dos listados con otro nombre.
- Los nombres de facultad son los encabezados de las páginas (no hay nombre legal verificado). Arquitectura no es una facultad separada en lo leído: se presenta dentro de Diseño y Comunicación. Psicología aparece como "Departamento de Psicología" dentro de Ciencias Sociales. "Ciencias Económicas" no aparece: se usa "Negocios".

**Facultad de Negocios** (fuente: /carreras/negocios/index.html; URL por ítem, de /carreras/ cuando coincide el título)
- Licenciatura en Administración — https://www.palermo.edu/negocios/licenciatura-administracion/
- Licenciatura en Administración de Sistemas y Empresas — https://www.palermo.edu/negocios/licenciatura-administracion-sistemas-y-empresas/
- Licenciatura en Comercio Internacional — https://www.palermo.edu/negocios/licenciatura-comercio-internacional/
- Licenciatura en Marketing — https://www.palermo.edu/negocios/licenciatura-marketing/
- Licenciatura en Recursos Humanos — https://www.palermo.edu/negocios/licenciatura-recursos-humanos/
- Licenciatura en Management: orientación Economía y Finanzas (en /carreras/: "Licenciatura en Management: Economía y Finanzas") — https://www.palermo.edu/negocios/management-economia-y-finanzas/
- Licenciatura en Management: orientación en Negocios Digitales (en /carreras/: "Licenciatura en Negocios Digitales") — https://www.palermo.edu/negocios/licenciatura-negocios-digitales/ — **[DUDOSO]** si es el mismo programa
- Licenciatura en Gastronomía — https://www.palermo.edu/negocios/licenciatura-gastronomia/
- Contador Público — https://www.palermo.edu/negocios/contador-publico/
- Licenciatura en Comercialización: Marketing y Publicidad — https://www.palermo.edu/negocios/licenciatura-comercializacion/
- Programa Conjunto en Hotelería y Turismo — sin URL en lo leído
- Licenciatura en Comercialización y Dirección de Empresas — sin URL en lo leído
- Licenciatura en Administración de Sistemas y Empresas - Ciclo de Complementación Curricular `[CCC]` — https://www.palermo.edu/negocios/ciclo-administracion-sistemas-y-empresas/
- Licenciatura en Turismo - Ciclo de Complementación Curricular `[CCC]` — sin URL
- Licenciatura en Gastronomía - Ciclo de Complementación Curricular `[CCC]` — sin URL
- Licenciatura en Hotelería - Ciclo de Complementación Curricular `[CCC]` — sin URL
- Solo en /carreras/: Licenciatura en Management: Inteligencia Artificial (https://www.palermo.edu/negocios/management-inteligencia-artificial/); Licenciatura en Management de la Innovación y Startups (…/management-innovacion-y-startups/); Licenciatura en Management: Gestión Deportiva (…/management-gestion-deportiva/); Licenciatura en Management en Turismo y Hospitalidad (…/management-turismo-hospitalidad/, solo online); Carrera corta: Comercialización y Dirección de Empresas `[T]` (…/carrera-corta-comercializacion-direccion-de-empresas/) — **[DUDOSO]** si es distinta de la licenciatura de igual nombre.

**Facultad de Diseño y Comunicación** (incluye Arquitectura; fuente: /carreras/; ruta base `https://www.palermo.edu/dyc/<slug>/`)
- Asesoramiento y Gestión de Imagen (Programa conjunto con la Lic. en Relaciones Públicas y Comunicación de Moda)
- Comunicación de Moda
- Dirección de Comunicación (Programa conjunto con la Lic. en Publicidad y la Lic. en Relaciones Públicas)
- Diseño de Ilustración
- Diseño de Interiores
- Diseño de Moda (Diseño Textil e Indumentaria)
- Diseño Digital (Diseño de Imagen y Sonido)
- Diseño Gráfico
- Diseño Industrial
- Diseño y Estéticas de la Moda (Programa conjunto con Diseño de Moda y Producción de Modas)
- Diseño y Negocios de la Moda (Programa conjunto con Diseño de Moda y Marketing de la Moda)
- Licenciatura en Comunicación Digital
- Licenciatura en Creación Sonora
- Licenciatura en Publicidad
- Licenciatura en Relaciones Públicas
- Marketing de la Moda
- Producción de Modas
- Producción Musical
- Community Management para Emprendedores - Licenciatura en Comunicación Digital - Ciclo de Complementación Curricular `[CCC]`
- Licenciatura en Diseño - Ciclo de Complementación Curricular `[CCC]`
- Licenciatura en Negocios de Diseño y Comunicación - Ciclo de Complementación Curricular `[CCC]`
- Licenciatura en Gestión de Proyectos de Diseño y Comunicación - Ciclo de Complementación Curricular `[CCC]`
- Arquitectura (solo presencial o combinada; la página leída es https://www.palermo.edu/arquitectura/)
- Actuación Profesional (Actor Profesional)
- Dirección Creativa Publicitaria (Programa conjunto con la Lic. en Publicidad y la Lic. en Dirección de Arte)
- Diseño de Música y Sonido (Programa conjunto con Lic. en Creación Sonora y Producción Musical)
- Licenciatura en Comunicación Audiovisual
- Licenciatura en Dirección Cinematográfica
- Licenciatura en Diseño (Diseño + Negocios + Tecnología)
- Licenciatura en Fotografía
- Organización de Eventos
- Proyecto y Construcción de Obras

**Facultad de Derecho** (https://www.palermo.edu/derecho/ y /carreras/)
- Abogacía — https://www.palermo.edu/derecho/abogacia/
- Escribanía (en /carreras/: "Escribanía (Notariado)", solo online) — https://www.palermo.edu/derecho/escribania/

**Facultad de Ciencias Sociales** (incluye Psicología; fuente: …/cienciassociales/carreras.html?tipo=grado; la página no marca por ítem si es grado o pregrado)
- Licenciatura en Psicología — https://www.palermo.edu/cienciassociales/psicologia/licenciatura-psicologia.html
- Licenciatura en Ciencias del Comportamiento — https://www.palermo.edu/cienciassociales/ciencias-del-comportamiento/ (en /carreras/ aparece bajo "Facultad de Negocios")
- Licenciatura en Periodismo — https://www.palermo.edu/cienciassociales/periodismo/
- Periodismo Deportivo — https://www.palermo.edu/cienciassociales/periodismo/deportivo/
- Licenciatura en Relaciones Internacionales — https://www.palermo.edu/cienciassociales/relaciones-internacionales/
- Licenciatura en Relaciones Internacionales y Ciencia Política — https://www.palermo.edu/cienciassociales/relaciones-internacionales-ciencia-politica/
- Crítico Universitario en Arte — https://www.palermo.edu/cienciassociales/critico-arte/ (sin nivel indicado; se cuenta como grado por defecto)
- Licenciatura en Arte — https://www.palermo.edu/cienciassociales/arte/
- Licenciatura en Humanidades y Ciencias Sociales — https://www.palermo.edu/cienciassociales/humanidades-ciencias-sociales/

**Facultad de Ingeniería** (https://www.palermo.edu/ingenieria/)
- Ingeniería en Inteligencia Artificial
- Ingeniería en Informática
- Ingeniería en Ciencia de Datos
- Ingeniería Industrial
- Ingeniería en Telecomunicaciones
- Ingeniería Electrónica
- Licenciatura en Ciberseguridad
- Licenciatura en Inteligencia Artificial
- Licenciatura en Informática
- Licenciatura en Redes y Comunicación de Datos
- Licenciatura en Administración de Sistemas y Empresas (también listada en Negocios; tiene tres URL distintas: `/negocios/…`, `/negocios/…-modalidad-online/` y `/economicas/…`)
- Licenciatura en Organización de la Producción
- Licenciatura en Tecnología de la Información
- Licenciatura en Tecnología de la Información para egresados de terciarios `[CCC]`
- Licenciatura en Redes y Comunicación de Datos para egresados de terciarios `[CCC]`
- Licenciatura en Administración de Sistemas y Empresas para egresados de terciarios `[CCC]` (también en Negocios)
- Analista Universitario en Sistemas `[T]` (carrera corta)

### 2.5 Universidad Nacional de La Matanza (UNLaM)

- Fuentes: grado https://www.unlam.edu.ar/academicas/?level=1 ("Encontramos 40 propuestas académicas para vos"); pregrado https://www.unlam.edu.ar/academicas/?level=2 ("20 propuestas"). Filtro "Unidad Académica": https://www.unlam.edu.ar/oferta-academica/. `https://www.unlam.edu.ar/index.php?seccion=3` no sirve (devuelve la portada).
- `robots.txt` (https://www.unlam.edu.ar/robots.txt): `Disallow:` vacío; declara `sitemap_index.xml` (que enlaza a `courses-sitemap.xml`, no abierto).
- Departamentos (unidad académica) según el filtro del sitio: Ciencias Económicas; Humanidades y Ciencias Sociales; Ingeniería e Investigaciones Tecnológicas; Derecho y Ciencia Política; Arquitectura y Urbanismo; Ciencias de la Salud; Odontología. También figuran en el filtro, y **no** son departamentos: Escuela de Formación Continua; Escuela de Artes, Medios e Innovación; Escuela de Posgrado; Secretaría de Extensión Universitaria; Secretaría de Desarrollo Universitario.
- **El listado no asigna departamento a cada carrera.** Cada ficha tiene una línea "Unidad académica: …", pero solo se verificó en 2 de 60: Ingeniería en Energías Renovables → Departamento de Ingeniería e Investigaciones Tecnológicas (nota: la ficha dice "Resolución Ministerial: En trámite") y Licenciatura en Nutrición → Departamento de Ciencias de la Salud. El resto **[NO VERIFICADO]**; completarlo requiere abrir 58 fichas más (una por carrera), o inferirlo.
- Formato: `Título · modalidad · duración · URL`. Todas las URL cuelgan de `https://www.unlam.edu.ar/academicas/<slug>/`.

**Grado (40 tarjetas; 16 de ellas son ciclos de complementación)**

| # | Título | Modalidad | Duración | Slug |
|---|---|---|---|---|
| 1 | Ingeniería en Informática | Presencial | 5 años | ingenieria-en-informatica |
| 2 | Licenciatura en Nutrición | Presencial | 5 | nutricion |
| 3 | Ingeniería Mecánica | Presencial | 5 | ingenieria-mecanica |
| 4 | Ingeniería Civil | Presencial | 5 | ingenieria-civil |
| 5 | Ingeniería Electrónica | Presencial | 5 | ingenieria-electronica |
| 6 | Ingeniería Industrial | Presencial | 5 | ingenieria-industrial |
| 7 | Odontología | Presencial | 5 | odontologia |
| 8 | Licenciatura en Kinesiología y Fisiatría | Presencial | 5 | licenciatura-en-kinesiologia-y-fisiatria |
| 9 | Medicina | Presencial | 6 | medicina |
| 10 | Licenciatura en Enfermería | Presencial | 5 | licenciatura-en-enfermeria |
| 11 | Licenciatura en Relaciones Laborales | Presencial | 4 | licenciatura-en-relaciones-laborales |
| 12 | Licenciatura en Comunicación Social | Presencial | 4 | licenciatura-en-comunicacion-social |
| 13 | Licenciatura en Relaciones Públicas | Presencial | 4 | licenciatura-en-relaciones-publicas |
| 14 | Licenciatura en Trabajo Social | Presencial | 5 | licenciatura-en-trabajo-social |
| 15 | Profesorado de Educación Física | Presencial | 4 | profesorado-de-educacion-fisica |
| 16 | Licenciatura en Educación Física | Presencial | 5 | licenciatura-en-educacion-fisica |
| 17 | Licenciatura en Arte y Gestión Cultural (Ciclo de Complementación Curricular) | A distancia | 2 | licenciatura-en-arte-y-gestion-cultural |
| 18 | Licenciatura en Animación Digital (Ciclo de Complementación Curricular) | A distancia | 2 | licenciatura-en-animacion-digital |
| 19 | Licenciatura en Administración | Presencial | 5 | licenciatura-en-administracion |
| 20 | Contador Público | Presencial | 5 | contador-publico |
| 21 | Licenciatura en Comercio Internacional | Presencial | 5 | licenciatura-en-comercio-internacional |
| 22 | Licenciatura en Economía | Presencial | 5 | licenciatura-en-economia |
| 23 | Licenciatura en Comercio Internacional (Ciclo de Complementación Curricular) | Presencial | 2 | licenciatura-en-comercio-internacional-2 |
| 24 | Licenciatura en Gestión de Seguros (Ciclo…) | A distancia | 2 | licenciatura-en-gestion-de-seguros |
| 25 | Licenciatura en Marketing (Ciclo…) | Presencial | 2 años y medio | licenciatura-en-marketing |
| 26 | Licenciatura en Gestión de Tecnología (Ciclo…) | Presencial | 2 | licenciatura-en-gestion-de-tecnologia |
| 27 | Licenciatura en Psicopedagogía (Ciclo…) | Presencial | 1 año y medio | licenciatura-en-psicopedagogia |
| 28 | Licenciatura en Lengua y Literatura (Ciclo…) | Presencial | 2 | licenciatura-en-lengua-y-literatura |
| 29 | Licenciatura en Gestión Tributaria (Ciclo…) | Semipresencial | 2 | licenciatura-en-gestion-tributaria |
| 30 | Licenciatura en Gestión Educativa (Ciclo…) | Presencial | 2 años y medio | licenciatura-en-gestion-educativa |
| 31 | Licenciatura en Educación Física (Ciclo…) | Presencial | 2 | licenciatura-en-educacion-fisica-2 |
| 32 | Licenciatura en Matemática Aplicada (Ciclo…) | Presencial | 2 | licenciatura-en-matematica-aplicada |
| 33 | Licenciatura en Historia (Ciclo…) | Presencial | 1 año y medio | licenciatura-en-historia |
| 34 | Licenciatura en Enfermería (Ciclo…) | Presencial | 2 | licenciatura-en-enfermeria-2 |
| 35 | Licenciatura en Lengua Inglesa (Ciclo…) | Presencial | 2 | licenciatura-en-lengua-inglesa |
| 36 | Licenciatura en Gestión Ambiental (Ciclo…) | Presencial | 2 | licenciatura-en-gestion-ambiental |
| 37 | Abogacía | Presencial | 5 | abogacia |
| 38 | Licenciatura en Ciencia Política | Presencial | 4 | licenciatura-en-ciencia-politica |
| 39 | Arquitectura | Presencial | 6 | arquitectura |
| 40 | Ingeniería en Energías Renovables | Presencial | 5 | ingenieria-en-energias-renovables |

Ojo: tres nombres se repiten con y sin ciclo (Comercio Internacional, Enfermería, Educación Física): son entradas distintas en el sitio.

**Pregrado / tecnicaturas (20 tarjetas, todas `[T]`)**

| # | Título | Modalidad | Duración | Slug |
|---|---|---|---|---|
| 1 | Tecnicatura en Anatomía Patológica | Presencial | 3 años | tecnicatura-en-anatomia-patologica |
| 2 | Tecnicatura Universitaria en Ceremonial y Protocolo | Presencial | 3 | tecnicatura-universitaria-en-ceremonial-y-protocolo |
| 3 | Tecnicatura en Guion Audiovisual | Presencial | 2 y medio | tecnicatura-en-guion-audiovisual |
| 4 | Tecnicatura en Animación y Arte Digital | Presencial | 2 y medio | tecnicatura-en-animacion-y-arte-digital |
| 5 | Tecnicatura en Artes Audiovisuales | Presencial | 2 y medio | tecnicatura-en-artes-audiovisuales |
| 6 | Tecnicatura en Artes Escénicas | Presencial | 2 y medio | tecnicatura-en-artes-escenicas |
| 7 | Locutor Nacional | Presencial | 3 | locutor-nacional |
| 8 | Tecnicatura en Periodismo Deportivo Integral | Presencial | 2 y medio | tecnicatura-en-periodismo-deportivo-integral |
| 9 | Tecnicatura en Diseño Gráfico y Digital | Presencial | 2 y medio | tecnicatura-en-diseno-grafico-y-digital |
| 10 | Tecnicatura Universitaria en Psicopedagogía | Presencial | 2 y medio | tecnicatura-universitaria-en-psicopedagogia |
| 11 | Martillero, Corredor Público y Tasador | Semipresencial | 2 y medio | martillero-corredor-publico-y-tasador |
| 12 | Tecnicatura Universitaria en Seguros | A distancia | 2 | tecnicatura-universitaria-en-seguros |
| 13 | Agente de Propaganda Médica | Presencial | 2 | agente-de-propaganda-medica |
| 14 | Tecnicatura Universitaria en Desarrollo de Videojuegos | A distancia | 2 y medio | tecnicatura-universitaria-en-desarrollo-de-videojuegos |
| 15 | Tecnicatura Universitaria en Producción de Contenidos para la Comunicación | Presencial | 2 y medio | tecnicatura-universitaria-en-produccion-de-contenidos-para-la-comunicacion |
| 16 | Tecnicatura Universitaria en Producción Musical | Presencial | 2 y medio | new-course-8 |
| 17 | Tecnicatura Universitaria en Publicidad y Comunicación Estratégica | Presencial | 2 y medio | new-course-9 |
| 18 | Tecnicatura Universitaria en Comercio Electrónico | A distancia | 2 y medio | new-course-12 |
| 19 | Tecnicatura en Diseño de Espacios Virtuales y Realidad Aumentada | Presencial | 2 y medio | tecnicatura-en-diseno-de-espacios-virtuales-y-realidad-aumentada |
| 20 | Tecnicatura en Políticas Públicas y Gestión Ciudadana | A distancia | 2 y medio | tecnicatura-en-politicas-publicas-y-gestion-ciudadana |

Los nº 7, 11 y 13 no llevan "Tecnicatura" en el nombre; se clasifican como pregrado porque así los etiqueta el sitio. Ojo con los slugs `new-course-N` (provisorios en el sitio).

### 2.6 Universidad Siglo 21

- Fuentes: https://21.edu.ar/carreras-y-programas?tipo_de_formacion=grado&currentpage=1 a 5 (grado: "49 de 262 carreras") y `…=pregrado&currentpage=1 a 3` (pregrado: "28 de 262"). `https://21.edu.ar/carreras` y `/carreras/grado` dan 404.
- `robots.txt` (https://21.edu.ar/robots.txt): Disallow solo de `/_hcms/preview/`, `/hs/manage-preferences/`, `/hs/preferences-center/` y parámetros `hs_preview`/`hsCacheBuster`; no bloquea `/carreras-y-programas`. Sitio sobre HubSpot; footer "Copyright 2025".
- **No tiene facultades** en lo leído (no aparece la palabra "facultad"). Solo hay un filtro por "Área temática" (Salud, Administración, Tecnología, Ingenierías, Marketing y Comunicación, Derecho, Educación, Política, Diseño, Criminología, "Ver más"), pero cada ítem **no muestra su área**: asignarla requeriría recorrer cada filtro (no se hizo).
- No se consultó el filtro "Ciclo de Complementación" (no se conoce su parámetro de URL): ningún ítem de estas dos listas viene marcado como ciclo, pero pueden existir ciclos no cubiertos.
- El "262" no tiene etiqueta en la página (probable total sin filtrar; [INFERIDO]).
- Prefijo de URL de cada ítem: `https://21.edu.ar/carreras-y-programas/<slug>`. Nombres con las mayúsculas irregulares del sitio.

**Grado (49 entradas; 48 URL distintas porque #21 y #42 son la misma)** — duración en años

1. Licenciatura en Psicología (4) · 2. Abogacía (4) · 3. Contador Público (4) · 4. Licenciatura en Administración (4) · 5. Licenciatura En Comercio Internacional (4) · 6. Licenciatura en Diseño y Animación Digital (4) · 7. Licenciatura en Administración Agraria (4) · 8. Ingeniería En Software (5) · 9. Licenciatura En Criminología Y Seguridad (4) · 10. Licenciatura en Relaciones Públicas e Institucionales (4) · 11. Licenciatura En Inteligencia Artificial Y Robótica (4) · 12. Actuario (4) · 13. Ingeniería en Innovación y Desarrollo (5) · 14. Licenciatura en Bioinformática (4) · 15. Licenciatura en Ciencia De Datos (4) · 16. Licenciatura en Ciencia Política y Gobierno (4) · 17. Licenciatura en Comercialización (4; slug `licenciatura-en-comercializacion-marketing`) · 18. Licenciatura en Diseño de Indumentaria y Textil (4) · 19. Licenciatura en Diseño Gráfico (4) · 20. Licenciatura en Diseño Industrial (4) · 21. Licenciatura En Educación Y Nuevas Tecnología (4) · 22. Licenciatura en Finanzas (4) · 23. Licenciatura en Gestión Ambiental (4) · 24. Licenciatura En Gestión De Recursos Humanos (4) · 25. Licenciatura en Gestión Turística (4) · 26. Licenciatura en Higiene, Seguridad y Medio Ambiente del Trabajo (4) · 27. Licenciatura En Informática (4) · 28. Licenciatura en Instrumentación Quirúrgica (4) · 29. Licenciatura en Inteligencia de Negocios Digitales (4) · 30. Licenciatura en Kinesiología y Fisioterapia (4) · 31. Licenciatura en Logística Global (4) · 32. Licenciatura en Matemática (4) · 33. Licenciatura en Nutrición (4) · 34. Licenciatura en Periodismo (4) · 35. Licenciatura en Producción de Bioimágenes (4) · 36. Licenciatura en Psicopedagogía (4) · 37. Licenciatura en Publicidad (4) · 38. Licenciatura en Relaciones Internacionales (4) · 39. Licenciatura en Seguridad Informática (4) · 40. Licenciatura en Terapia Ocupacional y Desarrollo Humano (4) · 41. Medicina (6) · 42. Licenciatura en Educación y Nuevas Tecnologías (4) (**duplicado de #21**, misma URL `…/licenciatura-en-educacion-y-nuevas-tecnologias`) · 43. Licenciatura En Ambiente Y Energías Renovables (4) · 44. Licenciatura en Gestión Deportiva (4) · 45. Licenciatura En Administración Hotelera (4) · 46. Licenciatura en Administración de Infraestructura Tecnológica (4) · 47. Licenciatura En Administración Pública (4) · 48. Licenciatura En Antropologia Organizacional (4) · 49. Licenciatura En Fonoaudiología (4)

**Pregrado (28 entradas, 26 son tecnicaturas)** — duración "2 años y medio" salvo indicación

1. Martillero, Corredor Público Y Corredor Inmobiliario (no es tecnicatura) · 2. Procurador (hasta 3 años; no es tecnicatura) · 3. Tecnicatura en Administración y Gestión Tributaria · 4. Tecnicatura en Dirección de Equipos de Ventas · 5. Tecnicatura en Dirección de Protocolo, Organización de Eventos y Relaciones Públicas · 6. Tecnicatura en Gestión Contable e Impositiva · 7. Tecnicatura en Gestión de Empresas Familiares · 8. Tecnicatura En Higiene Y Seguridad Laboral (URL en otro subdominio: `inscribite.21.edu.ar`) · 9. Tecnicatura En Investigación De La Escena Del Crimen · 10. Tecnicatura en Relaciones Laborales · 11. Tecnicatura Universitaria en Administración y Gestión de Políticas Públicas · 12. Tecnicatura Universitaria en Atención Prehospitalaria de Emergencias · 13. Tecnicatura Universitaria en Diseño y Animación Digital · 14. Tecnicatura Universitaria en Diseño y Desarrollo de Videojuegos · 15. Tecnicatura Universitaria En Enfermería · 16. Tecnicatura Universitaria en Gestión Administrativa de Servicios de Salud · 17. Tecnicatura Universitaria en Gestión de Moda · 18. Tecnicatura Universitaria en Gestión de Recursos Turísticos (href con `http://`) · 19. Tecnicatura Universitaria En Gestión Y Auditorías Ambientales · 20. Tecnicatura Universitaria en Hidrocarburos y Geociencia · 21. Tecnicatura Universitaria En Marketing Y Publicidad Digital · 22. Tecnicatura Universitaria en Promoción Comunitaria en Niñez y Adolescencia · 23. Tecnicatura Universitaria en Redes Informáticas y Telecomunicaciones · 24. Tecnicatura Universitaria en Gestión de Clima Laboral en la Organización · 25. Tecnicatura Universitaria en Simulación Clínica (URL sin el prefijo `/carreras-y-programas/`) · 26. Tecnicatura En Negocios Agroecológicos · 27. Tecnicatura En Responsabilidad Y Gestión Social · 28. Tecnicatura Universitaria En Estadística Aplicada Y Análisis Avanzado

---

## 3. Lo dudoso y lo que quedó sin verificar

**Universidades que no se pudieron leer**
- **UCA**: robots.txt sin restricciones y sitemap con URLs de carreras por facultad (Ciencias Médicas, Ciencias Económicas, Humanidades, Psicología y Psicopedagogía, Teología, Ciencias Sociales, Derecho Canónico, Ingeniería y Ciencias Agrarias, Rosario…), pero **todas las páginas de carreras devuelven solo el título** (probable renderizado por JavaScript). No se obtuvo ni una carrera. No se encontró en el sitemap ninguna URL específica de Mendoza ni de Derecho (grado). Pendiente: navegador con JS o mirar las peticiones de red de `/es/todas-las-carreras-de-la-uca`.
- **UTN**: se obtuvieron las 30 Facultades Regionales (Avellaneda, Bahía Blanca, Buenos Aires, Chubut, Concepción del Uruguay, Concordia, Córdoba, Delta, General Pacheco, Haedo, La Plata, La Rioja, Mar del Plata, Mendoza, Neuquén, Paraná, Rafaela, Reconquista, Resistencia, Rosario, San Francisco, San Nicolás, San Rafael, Santa Cruz, Santa Fe, Tierra del Fuego, Trenque Lauquen, Tucumán, Venado Tuerto, Villa María) y los conteos de portada (16 ingenierías, 2 licenciaturas, 55 tecnicaturas, 21 ciclos), pero **ningún nombre de carrera**: el listado dio vacío. Además no se verificó si todas las regionales dictan las mismas carreras. Para el catálogo habría que decidir si "facultad" = Facultad Regional.
- **UNR**: error SSL en todas las URL (incluido robots.txt).
- **UNSAM**: portada HTTP 402, robots.txt 404.
- **UCC**: catálogo "No se encontraron carreras…" (JS); solo una lista parcial en `/ingreso/directo` (~15 carreras sin facultad). robots.txt 404. Facultades sin verificar.
- **UBP**: el listado de grado devolvió HTTP 500; solo se leyó un índice A-Z que mezcla cursos y diplomaturas. Sin facultades.
- **UNCuyo**: se leyó solo inicio y fin de `/estudios/grado`; las 15 primeras tarjetas son todas de Artes y Diseño y no representan el listado. Las 12 facultades + 3 institutos sí están verificados (https://www.uncuyo.edu.ar/uacademicas).

**Lecturas incompletas de universidades listadas como fáciles**
- **USAL**: solo se vieron las 15 primeras de ~80 y las 10 unidades (Facultad de Arte y Arquitectura; Ciencias Agrarias y Veterinarias; Ciencias Económicas y Empresariales; Ciencias Jurídicas; Filosofía, Historia, Letras y Estudios Orientales; Ingeniería; Escuela de Lenguas Modernas; Medicina; Psicología y Psicopedagogía; Ciencias Sociales, Educación y Comunicación). Hay carreras marcadas "A Distancia" y "Programa Internacional" (p. ej., "Licenciatura en Comercio Internacional (Francia)") que no son carreras distintas del catálogo.
- **UNQ, UNTREF, UNLZ, UCASAL, Austral, ITBA, UB**: se confirmó URL, estructura y robots.txt, pero **no se transcribió el listado completo** (solo primeras ~15 o resumen). Datos clave: UNQ 51 entradas en 4 departamentos (con ciclos "(CCC)" y dos entradas repetidas "Licenciatura en Educación (CCC)"); UNTREF 36 entradas sin unidad por carrera (6 categorías de filtro, no son departamentos); UNLZ 5 facultades (Ciencias Agrarias; Ciencias Económicas; Ciencias Sociales; Derecho; Ingeniería), el buscador `carreras.unlz.edu.ar` no devuelve lista (JS) y robots.txt da 404; Austral solo expone la facultad en la ruta de la URL; UB: el encabezado del listado no siempre coincide con la facultad de la URL (p. ej. "Ciencias de la Comunicación" cuelga de `facultad-de-derecho-y-ciencias-sociales`); ITBA: 13 carreras, sin unidad.

**Datos que cada sitio no informa o hay que tomar con cuidado**
- La mayoría de los sitios **no informan un total** de carreras de grado; los números de §1 son conteos míos, salvo UBA ("más de 114"), UNC ("cerca de 100") y los de UNLaM/Siglo 21 ("N propuestas"/"N de 262").
- **Austral** dice "+100" pero junta grado, pregrado, posgrado y especializaciones; **UB** muestra un contador "0" sin sentido; **UCASAL** dice "140 carreras" sin aclarar el nivel.
- **UBA**: conteo propio (117-118 distintas) ≠ "más de 114"; sin fecha de actualización.
- **UNLP**: la página de facultades es de 2008; no hay facultad por carrera (agrupación por dominio = inferencia); una carrera (Fonoaudiología) apunta a la web de otra facultad.
- **UNLaM**: departamento por carrera verificado en 2 de 60 (ver §2.5); `new-course-N` son slugs provisorios.
- **UP**: tres páginas (negocios/index.html, /carreras/, facultad) no coinciden entre sí; nombres de facultad sin confirmar; no se abrieron las fichas.
- **Siglo 21**: ciclos de complementación y área temática por carrera no consultados; hay un duplicado y 3 URL con patrón distinto.
- **Gestión pública/privada y ciudad principal** de §1: conocimiento general; solo las sedes marcadas (v) se leyeron en el sitio. No se revisaron los términos de uso de ningún sitio, solo `robots.txt`.
- Los textos se leyeron como markdown convertido; pueden faltar tildes o signos en algunos casos. **Cualquier carga real debería re-verificar contra la página** o, mejor, hacerse con un navegador y revisión humana de la vista previa (la vista previa de la carga masiva sirve para esto).
- Ninguna ficha individual de carrera se abrió (planes de estudio, títulos, vigencia). Una carrera "en trámite" (UNLaM Ingeniería en Energías Renovables, "Resolución Ministerial: En trámite") es un ejemplo de que el listado puede incluir carreras sin reconocimiento oficial definitivo.

**Páginas que `robots.txt` o la política del sitio piden no leer (respetadas)**
- UP: `/propuesta/…` (la página de Ciencias Sociales enlaza a una versión bloqueada).
- UCASAL: `Disallow: /carreras/` (las fichas están bajo `/carrera/`, no afectadas, pero conviene no depender de ello).
- UNC: `Crawl-delay: 10` — respetar al automatizar (≥10 s entre pedidos).
- UBP: `Disallow: /*.pdf$` y `/wp-content/`.

---

## 4. Propuesta de mapeo al formato de carga masiva existente

Fuente: `material/templates/material/bulk_catalog_upload.html` y la vista `admin_bulk_catalog_upload` (`material/views.py`, con `_importar_fila_catalogo` y `_procesar_carga_catalogo`), formulario `BulkCatalogUploadForm` (`material/forms.py`). Ruta: `herramientas/carga-catalogo/`.

### 4.1 Qué espera la carga actual

- **Un CSV por institución.** La institución **no viene en el archivo**: se elige en un desplegable (`InstitutionV2` con `es_catalogo_institucional=True`). Por lo tanto **la institución tiene que existir antes** (nombre ≤255, sigla opcional ≤20, la sigla permite buscar "UBA" y encontrar "Universidad de Buenos Aires"). Cargar la institución no está cubierto por el CSV.
- **Columnas** (encabezado, sin distinguir mayúsculas ni acentos): `facultad, carrera, numero de materia, materia, año de cursada, cuatrimestre de cursada`.
- **Una fila por materia.** `facultad`, `carrera` y `materia` son **obligatorias** en cada fila (`ValueError: faltan facultad, carrera o materia`); `materia` ≤ 100 caracteres. `numero de materia` se recorta a 20 caracteres, `cuatrimestre de cursada` a 20, `año de cursada` se parsea como el primer número del texto (puede quedar vacío).
- **Codificación**: se prueba `utf-8-sig`, `latin1`, `cp1252`, `iso-8859-1` y `utf-16`; hay reparación de mojibake. Conviene entregar **UTF-8 con BOM** y verificar acentos/ñ en la vista previa.
- **Facultad**: se busca por nombre (sin distinguir mayúsculas) dentro de la institución y solo entre las del catálogo institucional; si no existe, se crea (`FacultyV2`, único por nombre y por institución).
- **Carrera**: se busca por nombre entre las ya vinculadas a **esa** facultad (`Career.faculties`); si no existe, se crea y se vincula. Una misma carrera repetida bajo dos facultades distintas se crea dos veces (una por facultad).
- **Materia**: se busca **global** por nombre entre las del catálogo (`Subject`): "Inglés I" se reutiliza entre carreras e instituciones. Se vincula con `CareerSubject` (`unique_together` carrera+materia).
- Flujo: vista previa (dry run, nada se guarda) → confirmar. Todo entra directo al catálogo institucional, sin bandeja de aprobación.
- Longitudes de modelo: `InstitutionV2.name`, `FacultyV2.name`, `Career.name` = 255.

### 4.2 Problema central: lo investigado son carreras, no materias

Todo lo recolectado es **facultad → carrera**; no hay planes de estudio. La carga actual **exige una materia en cada fila**, así que no se puede cargar "solo carreras" sin cambiar algo. Opciones:

1. **Agregar un modo "solo carreras" a la vista/función** (recomendada): si `materia` viene vacía y el modo está activado, crear facultad + carrera y saltear materia/`CareerSubject`. Cambio chico en `_importar_fila_catalogo` (hoy lanza error). Mantiene intacto el comportamiento actual por defecto y no ensucia el catálogo de materias.
2. **Fila ficticia con una materia comodín** (p. ej. "Materia a definir"): funciona hoy sin tocar código, pero `Subject` se busca **globalmente por nombre**, así que el comodín sería **una única materia compartida por todas las carreras de todas las instituciones**; además aparecería en los selectores de materia de los docentes. No recomendado.
3. **Cargar solo carreras por otra vía** (script/comando de gestión que reutilice `_importar_fila_catalogo` sin materia). Mismo efecto que la opción 1 pero fuera de la interfaz.

(No se verificó cómo se cargaron UAI y UADE; si ya existe una forma de cargar solo carreras, usar esa.)

### 4.3 Mapeo de campos propuesto (una fila por carrera)

| Campo CSV | Qué poner | Notas |
|---|---|---|
| `facultad` | Nombre de la facultad / departamento / escuela tal como figura en la fuente (§2) | Ver reglas de normalización abajo. Para universidades sin facultades (Siglo 21) usar un nombre único, p. ej. "Universidad Siglo 21" o el área temática si se llega a asignar |
| `carrera` | Nombre de la carrera, sin sufijos de ficha | Quitar `[T]`/`[CCC]`; decidir si los sufijos "(Ciclo de Complementación Curricular)" van en el nombre (recomendado conservarlos: distinguen carreras homónimas) |
| `numero de materia` | vacío | |
| `materia` | vacío (modo "solo carreras") o comodín (opción 2) | |
| `año de cursada` | vacío | |
| `cuatrimestre de cursada` | vacío | |

Archivos: **un CSV por universidad** (el desplegable pide una institución). Nombre sugerido `docs/carga_catalogo/<sigla>.csv` o fuera del repo. Antes: crear la `InstitutionV2` con `name` oficial y `sigla` (UBA, UNC, UNLP, UP, UNLaM, UES21, USAL…).

### 4.4 Reglas de normalización a decidir antes de generar archivos

- **Carreras compartidas entre facultades** (UBA Biotecnología en 4 facultades; Gestión de Agroalimentos y Paisaje en 2; UP Administración de Sistemas y Empresas en Negocios e Ingeniería; Tecnicatura Bioterios en 2): la carga crea una `Career` por facultad. Decidir si se repite la fila bajo cada facultad (más fiel al sitio, genera duplicados por nombre) o se carga una sola vez en la facultad "principal".
- **Orientaciones UNLP** (Artes Plásticas × 7, Música × 7, Artes Audiovisuales × 4, Biología × 4, Inglés/Francés × 2): una carrera por orientación (como el sitio) o una sola carrera con la orientación en el nombre. Recomiendo una por orientación, como el sitio, porque cada una tiene su plan.
- **Licenciatura vs. profesorado vs. tecnicatura vs. ciclo**: el catálogo no tiene campo de tipo; el tipo está solo en el nombre. Si se quieren excluir tecnicaturas y/o ciclos, decidirlo **por universidad** (UTN tiene 55 tecnicaturas y 21 ciclos que dominarían el catálogo).
- **Nombre de facultad**: usar el nombre de la fuente tal cual cuando es oficial (UNC, UNLP); para UBA agregar el prefijo "Facultad de" solo si se confirma el nombre legal (hoy [NO VERIFICADO]); unificar variantes dentro de una misma universidad (UP: Negocios vs. Ciencias Económicas, DyC con Arquitectura adentro).
- **Duplicados internos**: Siglo 21 #21/#42; UNLaM nombres repetidos con y sin ciclo; UBA "Licenciatura en Enfermería" aparece como grado y como ciclo en Ciencias Médicas (mismo nombre, dos niveles).
- **Mayúsculas irregulares** de Siglo 21 ("Licenciatura En Comercio Internacional"): normalizar a mayúscula inicial/minúsculas de artículos; la búsqueda por facultad/carrera es insensible a mayúsculas, así que no genera duplicados al recargar, pero se vería prolijo.
- **Datos con errata de origen** (UBA "Ciencias Geologógicas"): decidir si se corrige; si se corrige, anotar la corrección.
- **Carreras sin vigencia clara** (UNLaM Energías Renovables, "en trámite"): decidir si entra.
- **Acentos y ñ**: generar en UTF-8 con BOM y revisar la vista previa de la carga.

### 4.5 Siguientes pasos sugeridos (no hechos)

1. Decidir la opción de §4.2 (modo "solo carreras") y las reglas de §4.4.
2. Crear las instituciones (nombre oficial + sigla) en el catálogo.
3. Generar un CSV por universidad a partir de §2, empezando por UNC (la fuente más limpia) y UBA, y probar la vista previa de `herramientas/carga-catalogo/`.
4. Completar las lecturas pendientes de §3 (USAL, UNQ, UNTREF, UNLZ, UCASAL, Austral, ITBA, UB) y las de navegador (UTN, UCA, UCC, UBP, UNR, UNSAM).
5. Revisar cada CSV a ojo contra la página antes de confirmar la carga en producción (la base de producción se va a borrar y recargar: dejar los CSV versionados como parte del proceso de recarga).
