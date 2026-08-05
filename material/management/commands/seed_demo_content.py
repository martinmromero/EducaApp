"""
Crea contenido de ejemplo (instituciones, materias, temas, resultados de
aprendizaje y preguntas) que viene con el sistema desde el primer booteo.

Es idempotente: se puede correr en cada deploy sin duplicar datos ni pisar
ediciones. Todo el contenido queda en propiedad del usuario técnico
`settings.SEED_CONTENT_USERNAME` (ver material/migrations/0042_seed_content_user.py),
lo que lo protege de borrado/edición por parte de usuarios normales: las
vistas de edición/borrado de Question ya filtran por `user=request.user`,
así que un usuario distinto del dueño nunca puede tocarlas.
"""
import base64

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import CommandError
from django.core.management.base import BaseCommand
from django.db import transaction

from material.models import (
    CampusV2,
    Career,
    FacultyV2,
    InstitutionSubject,
    InstitutionV2,
    LearningOutcome,
    Question,
    Subject,
    Topic,
)


def _fake_crest_svg(initials, primary, secondary):
    """
    Escudo ficticio simple (SVG generado, sin depender de ningún archivo de
    imagen externo) para que las instituciones demo tengan membrete en vez
    de quedar sin logo en el examen de ejemplo. Se guarda como data URI en
    InstitutionV2.logo_b64 (mismo campo que usa un logo real subido por un
    usuario — ver InstitutionV2.logo_src).
    """
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 116" width="100" height="116">'
        f'<path d="M50 4 L92 18 L92 54 C92 82 74 100 50 112 C26 100 8 82 8 54 L8 18 Z" '
        f'fill="{primary}" stroke="#1a1a1a" stroke-width="2"/>'
        f'<path d="M50 4 L92 18 L92 54 C92 82 74 100 50 112 Z" fill="{secondary}" opacity="0.35"/>'
        '<circle cx="50" cy="46" r="22" fill="none" stroke="#ffffff" stroke-width="1.5" opacity="0.6"/>'
        f'<text x="50" y="56" font-family="Georgia, \'Times New Roman\', serif" font-size="26" '
        f'font-weight="700" text-anchor="middle" fill="#ffffff">{initials}</text>'
        '</svg>'
    )
    encoded = base64.b64encode(svg.encode('utf-8')).decode('ascii')
    return f'data:image/svg+xml;base64,{encoded}'


PROGRAMACION_TOPICS = [
    ('Variables y tipos de datos', 5),
    ('Estructuras de control', 5),
    ('Funciones y modularización', 4),
    ('Estructuras de datos básicas', 3),
]

PROGRAMACION_OUTCOMES = [
    'Diseñar algoritmos simples usando variables, condicionales y bucles.',
    'Escribir funciones reutilizables para descomponer un problema en partes más pequeñas.',
    'Elegir la estructura de datos adecuada (lista, pila, cola) según el problema a resolver.',
]

PROGRAMACION_QUESTIONS = [
    dict(
        topic='Variables y tipos de datos', difficulty=1, bloom_level=1,
        question_type='verdadero_falso',
        question_text='En la mayoría de los lenguajes de programación, una variable declarada como entero puede almacenar directamente un valor decimal sin conversión.',
        answer_text='Falso. Un entero (int) no puede almacenar decimales sin perder precisión o sin una conversión explícita a un tipo de punto flotante (float/double).',
    ),
    dict(
        topic='Variables y tipos de datos', difficulty=1, bloom_level=1,
        question_type='opcion_multiple',
        question_text='¿Cuál de los siguientes es un tipo de dato primitivo típico en la mayoría de los lenguajes de programación?',
        answer_text='Booleano',
        options=['Booleano', 'Lista enlazada', 'Árbol binario', 'Hash map'],
    ),
    dict(
        topic='Variables y tipos de datos', difficulty=2, bloom_level=2,
        question_type='desarrollo',
        question_text='Explicá la diferencia entre una variable de tipo estático y una de tipo dinámico, dando un ejemplo de lenguaje para cada caso.',
        answer_text='En tipado estático (ej. Java, C), el tipo de la variable se fija en tiempo de compilación y no puede cambiar. En tipado dinámico (ej. Python, JavaScript), el tipo se determina en tiempo de ejecución y una misma variable puede referenciar valores de distinto tipo a lo largo del programa.',
    ),
    dict(
        topic='Estructuras de control', difficulty=1, bloom_level=1,
        question_type='completar_blank',
        question_text='La instrucción ______ permite repetir un bloque de código mientras se cumpla una condición, sin conocer de antemano cuántas iteraciones se ejecutarán.',
        answer_text='while',
    ),
    dict(
        topic='Estructuras de control', difficulty=2, bloom_level=3,
        question_type='opcion_multiple',
        question_text='¿Qué estructura de control es más adecuada para recorrer un arreglo de tamaño conocido, elemento por elemento?',
        answer_text='for',
        options=['for', 'while', 'do-while', 'goto'],
    ),
    dict(
        topic='Estructuras de control', difficulty=3, bloom_level=4,
        question_type='desarrollo',
        question_text='Dado un arreglo de números, describí un algoritmo que use estructuras de control para encontrar el valor máximo, indicando qué rol cumple cada estructura utilizada.',
        answer_text='Se inicializa una variable "máximo" con el primer elemento del arreglo. Luego se recorre el resto del arreglo con un bucle for; en cada iteración, un condicional (if) compara el elemento actual contra "máximo" y lo reemplaza si es mayor. Al terminar el recorrido, "máximo" contiene el valor buscado.',
    ),
    dict(
        topic='Funciones y modularización', difficulty=2, bloom_level=2,
        question_type='verdadero_falso',
        question_text='Una función que no recibe parámetros no puede devolver ningún valor.',
        answer_text='Falso. Los parámetros de entrada y el valor de retorno son independientes: una función sin parámetros puede devolver un valor perfectamente (por ejemplo, una función que retorna la fecha actual).',
    ),
    dict(
        topic='Funciones y modularización', difficulty=2, bloom_level=3,
        question_type='opcion_multiple',
        question_text='¿Cuál es la principal ventaja de dividir un programa en funciones pequeñas y reutilizables?',
        answer_text='Facilita el mantenimiento y evita duplicar código',
        options=[
            'Facilita el mantenimiento y evita duplicar código',
            'Hace que el programa ocupe menos espacio en disco siempre',
            'Elimina la necesidad de probar el programa',
            'Aumenta automáticamente la velocidad de ejecución',
        ],
    ),
    dict(
        topic='Funciones y modularización', difficulty=3, bloom_level=4,
        question_type='desarrollo',
        question_text='Analizá qué problemas puede traer una función que modifica variables globales en lugar de recibir y devolver valores mediante parámetros y retorno.',
        answer_text='Dificulta predecir el comportamiento del programa (efectos secundarios ocultos), complica las pruebas unitarias porque el resultado depende de un estado externo, y aumenta el riesgo de errores cuando varias funciones modifican la misma variable global en distinto orden.',
    ),
    dict(
        topic='Estructuras de datos básicas', difficulty=2, bloom_level=2,
        question_type='opcion_multiple',
        question_text='¿Qué estructura de datos sigue la política "el último en entrar es el primero en salir" (LIFO)?',
        answer_text='Pila (stack)',
        options=['Pila (stack)', 'Cola (queue)', 'Árbol', 'Grafo'],
    ),
    dict(
        topic='Estructuras de datos básicas', difficulty=1, bloom_level=1,
        question_type='verdadero_falso',
        question_text='En una cola (queue), los elementos se procesan en el mismo orden en que fueron agregados (FIFO).',
        answer_text='Verdadero.',
    ),
    dict(
        topic='Estructuras de datos básicas', difficulty=3, bloom_level=3,
        question_type='desarrollo',
        question_text='Proponé un caso de uso real donde convenga usar una cola en lugar de una pila, y justificá por qué.',
        answer_text='Un sistema de impresión de documentos: los trabajos de impresión deben procesarse en el orden en que llegaron (el primero que se envió es el primero en imprimirse), lo cual corresponde al comportamiento FIFO de una cola. Una pila haría que el último trabajo enviado se imprima primero, lo cual no es intuitivo para el usuario.',
    ),
    dict(
        topic='Variables y tipos de datos', difficulty=1, bloom_level=1,
        question_type='verdadero_falso',
        question_text='El operador de asignación (=) y el operador de comparación de igualdad (==) cumplen la misma función en la mayoría de los lenguajes de programación.',
        answer_text='Falso. El operador = asigna un valor a una variable, mientras que == compara si dos valores son iguales y devuelve un booleano.',
    ),
    dict(
        topic='Variables y tipos de datos', difficulty=2, bloom_level=2,
        question_type='opcion_multiple',
        question_text='¿Cuál de las siguientes opciones es un ejemplo de conversión de tipo explícita (casting)?',
        answer_text='int("25")',
        options=['int("25")', 'x = 25', 'x == 25', 'print(25)'],
    ),
    dict(
        topic='Variables y tipos de datos', difficulty=2, bloom_level=1,
        question_type='completar_blank',
        question_text='Una variable declarada pero nunca inicializada puede contener un valor ______ (no determinado) hasta que se le asigne uno explícitamente, según el lenguaje.',
        answer_text='basura',
    ),
    dict(
        topic='Variables y tipos de datos', difficulty=1, bloom_level=1,
        question_type='opcion_multiple',
        question_text='¿Qué tipo de dato usarías para representar un valor de verdadero o falso?',
        answer_text='Booleano',
        options=['Booleano', 'Entero', 'Cadena de texto', 'Flotante'],
    ),
    dict(
        topic='Variables y tipos de datos', difficulty=3, bloom_level=2,
        question_type='desarrollo',
        question_text='Explicá qué es el "scope" (ámbito) de una variable y por qué es importante entenderlo al escribir funciones.',
        answer_text='El scope es la región del programa donde una variable existe y puede ser accedida. Una variable local solo existe dentro de la función donde se declaró; una global existe en todo el programa. Entender el scope es importante para evitar que una función modifique por error una variable de otra parte del programa, y para saber cuándo una variable deja de estar disponible.',
    ),
    dict(
        topic='Estructuras de control', difficulty=1, bloom_level=1,
        question_type='verdadero_falso',
        question_text='Un bucle do-while ejecuta el bloque de código al menos una vez, incluso si la condición es falsa desde el inicio.',
        answer_text='Verdadero. A diferencia del while, el do-while evalúa la condición después de ejecutar el bloque, garantizando al menos una ejecución.',
    ),
    dict(
        topic='Estructuras de control', difficulty=1, bloom_level=1,
        question_type='opcion_multiple',
        question_text='¿Qué instrucción se usa para salir anticipadamente de un bucle antes de que termine su condición natural?',
        answer_text='break',
        options=['break', 'continue', 'return', 'pass'],
    ),
    dict(
        topic='Estructuras de control', difficulty=2, bloom_level=2,
        question_type='completar_blank',
        question_text='La estructura condicional ______ permite evaluar múltiples casos posibles de una misma variable de forma más legible que una cadena larga de if-else.',
        answer_text='switch',
    ),
    dict(
        topic='Estructuras de control', difficulty=2, bloom_level=2,
        question_type='opcion_multiple',
        question_text='¿Cuál es el riesgo principal de un bucle mal condicionado?',
        answer_text='Que se convierta en un bucle infinito',
        options=['Que se convierta en un bucle infinito', 'Que el programa no compile', 'Que ocupe menos memoria', 'Que se ejecute más rápido'],
    ),
    dict(
        topic='Estructuras de control', difficulty=2, bloom_level=4,
        question_type='desarrollo',
        question_text='Comparar if-else con switch: ¿en qué situación conviene usar cada uno?',
        answer_text='if-else conviene cuando las condiciones son rangos o expresiones booleanas complejas. switch (o match, según el lenguaje) conviene cuando se comparan muchos valores discretos posibles de una misma variable, porque resulta más legible y ordenado que una larga cadena de if-else if.',
    ),
    dict(
        topic='Funciones y modularización', difficulty=2, bloom_level=2,
        question_type='verdadero_falso',
        question_text='Una función puede llamarse a sí misma; a esto se lo llama recursividad.',
        answer_text='Verdadero. La recursividad es una técnica válida siempre que exista un caso base que detenga las llamadas.',
    ),
    dict(
        topic='Funciones y modularización', difficulty=3, bloom_level=2,
        question_type='opcion_multiple',
        question_text='¿Qué término describe a una función que siempre devuelve el mismo resultado para los mismos argumentos y no produce efectos secundarios?',
        answer_text='Función pura',
        options=['Función pura', 'Función recursiva', 'Función anónima', 'Función global'],
    ),
    dict(
        topic='Funciones y modularización', difficulty=1, bloom_level=1,
        question_type='completar_blank',
        question_text='Los valores que una función recibe entre paréntesis en su definición se llaman parámetros ______.',
        answer_text='formales',
    ),
    dict(
        topic='Funciones y modularización', difficulty=2, bloom_level=3,
        question_type='opcion_multiple',
        question_text='¿Qué ventaja tiene pasar un parámetro por referencia en lugar de por valor?',
        answer_text='La función puede modificar el valor original de la variable',
        options=[
            'La función puede modificar el valor original de la variable',
            'El programa ocupa menos líneas de código',
            'Se evita tener que declarar la función',
            'El tipo de dato deja de importar',
        ],
    ),
    dict(
        topic='Funciones y modularización', difficulty=3, bloom_level=4,
        question_type='desarrollo',
        question_text='Explicá qué es la recursividad y qué condición es imprescindible para que una función recursiva no termine en un bucle infinito.',
        answer_text='La recursividad es cuando una función se llama a sí misma para resolver un problema dividiéndolo en subproblemas más pequeños del mismo tipo. Es imprescindible definir un "caso base": una condición simple que no requiere más llamadas recursivas y detiene la cadena de llamadas, evitando que la función se llame indefinidamente.',
    ),
    dict(
        topic='Estructuras de datos básicas', difficulty=1, bloom_level=1,
        question_type='verdadero_falso',
        question_text='Un arreglo (array) tiene tamaño fijo una vez declarado en los lenguajes de bajo nivel como C.',
        answer_text='Verdadero. En C, el tamaño del arreglo se define en la declaración y no puede cambiar dinámicamente (a diferencia de listas dinámicas en otros lenguajes).',
    ),
    dict(
        topic='Estructuras de datos básicas', difficulty=2, bloom_level=2,
        question_type='opcion_multiple',
        question_text='¿Qué estructura de datos es ideal para representar relaciones jerárquicas, como el sistema de archivos de una computadora?',
        answer_text='Árbol',
        options=['Árbol', 'Pila (stack)', 'Cola (queue)', 'Arreglo'],
    ),
    dict(
        topic='Estructuras de datos básicas', difficulty=2, bloom_level=1,
        question_type='completar_blank',
        question_text='En una lista enlazada, cada elemento (nodo) contiene un dato y un puntero al ______ nodo de la lista.',
        answer_text='siguiente',
    ),
    dict(
        topic='Estructuras de datos básicas', difficulty=2, bloom_level=3,
        question_type='desarrollo',
        question_text='Dado un problema donde se necesita insertar y eliminar elementos frecuentemente en el medio de una colección, ¿convendría más un arreglo o una lista enlazada? Justificá.',
        answer_text='Conviene una lista enlazada: insertar o eliminar un elemento en el medio de un arreglo requiere desplazar todos los elementos posteriores, lo cual es costoso. En una lista enlazada, esa misma operación solo requiere reajustar un par de punteros, sin mover el resto de los elementos.',
    ),
]

BASES_DE_DATOS_TOPICS = [
    ('Modelo relacional', 5),
    ('Consultas SQL', 5),
    ('Normalización', 4),
    ('Transacciones y control de concurrencia', 4),
]

BASES_DE_DATOS_OUTCOMES = [
    'Diseñar un modelo entidad-relación normalizado para un dominio simple.',
    'Escribir consultas SQL con joins, filtros y funciones de agregación.',
]

BASES_DE_DATOS_QUESTIONS = [
    dict(
        topic='Modelo relacional', difficulty=1, bloom_level=1,
        question_type='opcion_multiple',
        question_text='¿Qué elemento de una tabla garantiza que cada fila pueda identificarse de forma única?',
        answer_text='Clave primaria',
        options=['Clave primaria', 'Índice secundario', 'Vista', 'Trigger'],
    ),
    dict(
        topic='Modelo relacional', difficulty=2, bloom_level=2,
        question_type='verdadero_falso',
        question_text='Una clave foránea puede referenciar a una fila que no existe en la tabla referenciada.',
        answer_text='Falso. La integridad referencial exige que toda clave foránea apunte a un valor existente en la tabla referenciada (o sea NULL si el campo lo permite).',
    ),
    dict(
        topic='Modelo relacional', difficulty=3, bloom_level=4,
        question_type='desarrollo',
        question_text='Dado un sistema de biblioteca con "Libros" y "Autores", donde un libro puede tener varios autores y un autor puede escribir varios libros, describí cómo modelarías esa relación.',
        answer_text='Se necesita una tabla intermedia (ej. "Libro_Autor") con claves foráneas hacia "Libros" y hacia "Autores", ya que es una relación muchos-a-muchos que no puede resolverse agregando una sola clave foránea en ninguna de las dos tablas originales.',
    ),
    dict(
        topic='Consultas SQL', difficulty=1, bloom_level=1,
        question_type='completar_blank',
        question_text='La cláusula SQL ______ se usa para filtrar filas antes de agruparlas, mientras que HAVING filtra después de agrupar.',
        answer_text='WHERE',
    ),
    dict(
        topic='Consultas SQL', difficulty=2, bloom_level=3,
        question_type='opcion_multiple',
        question_text='¿Qué tipo de JOIN devuelve todas las filas de la tabla izquierda aunque no tengan coincidencia en la tabla derecha?',
        answer_text='LEFT JOIN',
        options=['LEFT JOIN', 'INNER JOIN', 'CROSS JOIN', 'RIGHT JOIN'],
    ),
    dict(
        topic='Consultas SQL', difficulty=3, bloom_level=4,
        question_type='desarrollo',
        question_text='Explicá la diferencia entre usar COUNT(*) y COUNT(columna) en una consulta con GROUP BY, y en qué caso los resultados podrían diferir.',
        answer_text='COUNT(*) cuenta todas las filas del grupo, incluyendo aquellas donde una columna específica tenga valor NULL. COUNT(columna) solo cuenta las filas donde esa columna no es NULL. Los resultados difieren cuando el grupo contiene filas con valores NULL en la columna contada.',
    ),
    dict(
        topic='Normalización', difficulty=2, bloom_level=2,
        question_type='verdadero_falso',
        question_text='Una tabla en primera forma normal (1FN) puede tener columnas con valores multivaluados, como una lista de teléfonos en una sola celda.',
        answer_text='Falso. La primera forma normal exige que cada celda contenga un único valor atómico, no listas ni conjuntos de valores.',
    ),
    dict(
        topic='Normalización', difficulty=3, bloom_level=3,
        question_type='opcion_multiple',
        question_text='¿Qué problema busca resolver principalmente la segunda forma normal (2FN)?',
        answer_text='Dependencias parciales de la clave primaria',
        options=[
            'Dependencias parciales de la clave primaria',
            'Valores multivaluados en una columna',
            'Dependencias transitivas entre atributos no clave',
            'Falta de índices en las tablas',
        ],
    ),
    dict(
        topic='Normalización', difficulty=3, bloom_level=4,
        question_type='desarrollo',
        question_text='Dada una tabla "Pedidos" con columnas (id_pedido, id_cliente, nombre_cliente, id_producto, nombre_producto, cantidad), identificá qué forma normal viola y cómo la normalizarías.',
        answer_text='Viola la 2FN y la 3FN: nombre_cliente depende solo de id_cliente (no de la clave completa) y nombre_producto depende solo de id_producto. Se normaliza separando en tres tablas: Clientes (id_cliente, nombre_cliente), Productos (id_producto, nombre_producto) y Pedidos (id_pedido, id_cliente, id_producto, cantidad), cada una referenciando a las otras por clave foránea.',
    ),
    dict(
        topic='Modelo relacional', difficulty=1, bloom_level=1,
        question_type='verdadero_falso',
        question_text='Una tabla puede tener más de una clave candidata, pero solo una de ellas se designa como clave primaria.',
        answer_text='Verdadero. Las demás claves candidatas suelen implementarse como restricciones UNIQUE.',
    ),
    dict(
        topic='Modelo relacional', difficulty=2, bloom_level=2,
        question_type='opcion_multiple',
        question_text='¿Qué tipo de relación existe cuando un empleado tiene un único legajo y ese legajo pertenece a un único empleado?',
        answer_text='Uno a uno',
        options=['Uno a uno', 'Uno a muchos', 'Muchos a muchos', 'Ninguna de las anteriores'],
    ),
    dict(
        topic='Modelo relacional', difficulty=1, bloom_level=1,
        question_type='completar_blank',
        question_text='El diagrama ______ se usa para modelar visualmente entidades, atributos y relaciones antes de crear las tablas.',
        answer_text='entidad-relación',
    ),
    dict(
        topic='Modelo relacional', difficulty=2, bloom_level=2,
        question_type='opcion_multiple',
        question_text='¿Cuál de los siguientes NO es un elemento propio del modelo relacional clásico?',
        answer_text='Documento JSON embebido',
        options=['Documento JSON embebido', 'Tabla', 'Fila', 'Columna'],
    ),
    dict(
        topic='Modelo relacional', difficulty=3, bloom_level=3,
        question_type='desarrollo',
        question_text='Explicá la diferencia entre una clave primaria y una clave única (UNIQUE), dando un ejemplo de cuándo usarías cada una.',
        answer_text='La clave primaria identifica de forma única cada fila y no admite valores NULL; solo puede haber una por tabla (aunque puede ser compuesta). Una restricción UNIQUE también exige valores no repetidos, pero puede admitir NULL (según el motor) y puede haber varias por tabla — por ejemplo, el DNI de una persona podría ser UNIQUE aunque la clave primaria sea un id autogenerado.',
    ),
    dict(
        topic='Consultas SQL', difficulty=1, bloom_level=1,
        question_type='verdadero_falso',
        question_text='La cláusula ORDER BY debe ir siempre antes que WHERE en una consulta SQL.',
        answer_text='Falso. El orden correcto es SELECT, FROM, WHERE, GROUP BY, HAVING y por último ORDER BY.',
    ),
    dict(
        topic='Consultas SQL', difficulty=1, bloom_level=1,
        question_type='opcion_multiple',
        question_text='¿Qué función SQL de agregación devuelve el valor promedio de una columna numérica?',
        answer_text='AVG()',
        options=['AVG()', 'SUM()', 'COUNT()', 'MAX()'],
    ),
    dict(
        topic='Consultas SQL', difficulty=2, bloom_level=1,
        question_type='completar_blank',
        question_text='La palabra clave ______ elimina los valores duplicados de los resultados de una consulta SELECT.',
        answer_text='DISTINCT',
    ),
    dict(
        topic='Consultas SQL', difficulty=2, bloom_level=2,
        question_type='opcion_multiple',
        question_text='¿Qué instrucción SQL se usa para modificar filas ya existentes en una tabla?',
        answer_text='UPDATE',
        options=['UPDATE', 'INSERT', 'ALTER', 'CREATE'],
    ),
    dict(
        topic='Consultas SQL', difficulty=3, bloom_level=3,
        question_type='desarrollo',
        question_text='Explicá qué hace una subconsulta (subquery) y dá un ejemplo de una situación donde sea necesaria.',
        answer_text='Una subconsulta es una consulta SELECT anidada dentro de otra consulta, usada para calcular un valor o un conjunto de valores intermedios. Por ejemplo, para encontrar los empleados que ganan más que el promedio salarial, se necesita una subconsulta que calcule ese promedio (SELECT AVG(salario) FROM empleados) y usarla dentro del WHERE de la consulta principal.',
    ),
    dict(
        topic='Normalización', difficulty=1, bloom_level=1,
        question_type='verdadero_falso',
        question_text='La tercera forma normal (3FN) elimina las dependencias transitivas entre atributos no clave.',
        answer_text='Verdadero.',
    ),
    dict(
        topic='Normalización', difficulty=2, bloom_level=2,
        question_type='opcion_multiple',
        question_text='¿Cuál es el objetivo principal de normalizar una base de datos?',
        answer_text='Reducir la redundancia de datos y evitar anomalías de actualización',
        options=[
            'Reducir la redundancia de datos y evitar anomalías de actualización',
            'Aumentar la cantidad de tablas sin motivo funcional',
            'Eliminar la necesidad de claves primarias',
            'Hacer que las consultas SQL sean más cortas',
        ],
    ),
    dict(
        topic='Normalización', difficulty=2, bloom_level=1,
        question_type='completar_blank',
        question_text='Una tabla está en ______ forma normal cuando cumple la 1FN y todos sus atributos no clave dependen completamente de la clave primaria (sin dependencias parciales).',
        answer_text='segunda',
    ),
    dict(
        topic='Normalización', difficulty=2, bloom_level=3,
        question_type='opcion_multiple',
        question_text='¿Qué anomalía puede ocurrir en una tabla no normalizada al borrar la única fila que contenía cierta información?',
        answer_text='Anomalía de borrado',
        options=['Anomalía de borrado', 'Anomalía de inserción', 'Deadlock', 'Overflow de índice'],
    ),
    dict(
        topic='Transacciones y control de concurrencia', difficulty=2, bloom_level=1,
        question_type='opcion_multiple',
        question_text='¿Qué propiedad ACID garantiza que una transacción se ejecute por completo o no se ejecute en absoluto?',
        answer_text='Atomicidad',
        options=['Atomicidad', 'Consistencia', 'Aislamiento', 'Durabilidad'],
    ),
    dict(
        topic='Transacciones y control de concurrencia', difficulty=2, bloom_level=2,
        question_type='verdadero_falso',
        question_text='Dos transacciones que se ejecutan de forma concurrente pueden generar resultados inconsistentes si no se controla el acceso a los datos compartidos.',
        answer_text='Verdadero. Por eso los motores de base de datos usan bloqueos y niveles de aislamiento para evitar estos problemas.',
    ),
    dict(
        topic='Transacciones y control de concurrencia', difficulty=1, bloom_level=1,
        question_type='completar_blank',
        question_text='El comando SQL ______ confirma de forma permanente los cambios realizados durante una transacción.',
        answer_text='COMMIT',
    ),
    dict(
        topic='Transacciones y control de concurrencia', difficulty=3, bloom_level=2,
        question_type='opcion_multiple',
        question_text='¿Qué problema de concurrencia ocurre cuando una transacción lee datos que otra transacción todavía no confirmó?',
        answer_text='Lectura sucia (dirty read)',
        options=['Lectura sucia (dirty read)', 'Lectura fantasma', 'Deadlock', 'Lectura repetible'],
    ),
    dict(
        topic='Transacciones y control de concurrencia', difficulty=2, bloom_level=1,
        question_type='opcion_multiple',
        question_text='¿Qué instrucción SQL deshace los cambios de una transacción que todavía no fue confirmada?',
        answer_text='ROLLBACK',
        options=['ROLLBACK', 'COMMIT', 'UNDO', 'CANCEL'],
    ),
    dict(
        topic='Transacciones y control de concurrencia', difficulty=3, bloom_level=3,
        question_type='desarrollo',
        question_text='Explicá qué es un bloqueo (lock) en una base de datos y por qué es necesario para el control de concurrencia.',
        answer_text='Un bloqueo es un mecanismo que impide que dos transacciones modifiquen (o a veces incluso lean) el mismo dato al mismo tiempo, reservando temporalmente el acceso a una fila o tabla para una transacción hasta que termine. Es necesario porque, sin bloqueos, transacciones concurrentes podrían pisarse cambios entre sí o leer datos en un estado intermedio inconsistente.',
    ),
]

BIOLOGIA_TOPICS = [
    ('La célula y sus organelas', 5),
    ('Membrana celular y transporte', 4),
    ('División celular', 4),
    ('Núcleo y material genético', 4),
]

BIOLOGIA_OUTCOMES = [
    'Describir la estructura y función de las principales organelas celulares.',
    'Explicar los mecanismos de transporte a través de la membrana celular.',
    'Diferenciar los procesos de mitosis y meiosis y su rol biológico.',
]

BIOLOGIA_QUESTIONS = [
    dict(
        topic='La célula y sus organelas', difficulty=1, bloom_level=1,
        question_type='opcion_multiple',
        question_text='¿Cuál es la organela responsable de la producción de energía (ATP) en la célula?',
        answer_text='Mitocondria',
        options=['Mitocondria', 'Aparato de Golgi', 'Ribosoma', 'Lisosoma'],
    ),
    dict(
        topic='La célula y sus organelas', difficulty=1, bloom_level=1,
        question_type='verdadero_falso',
        question_text='Las células procariotas poseen núcleo delimitado por membrana nuclear.',
        answer_text='Falso. Las células procariotas carecen de núcleo verdadero; su material genético se encuentra disperso en el citoplasma, en una región llamada nucleoide.',
    ),
    dict(
        topic='La célula y sus organelas', difficulty=2, bloom_level=2,
        question_type='completar_blank',
        question_text='El ______ es la organela encargada de modificar, empaquetar y distribuir proteínas y lípidos sintetizados en el retículo endoplasmático.',
        answer_text='Aparato de Golgi',
    ),
    dict(
        topic='La célula y sus organelas', difficulty=3, bloom_level=4,
        question_type='desarrollo',
        question_text='Compará la estructura y función del retículo endoplasmático liso y el rugoso.',
        answer_text='El retículo endoplasmático rugoso tiene ribosomas adheridos y se encarga principalmente de la síntesis de proteínas destinadas a secreción o membranas. El retículo endoplasmático liso carece de ribosomas y participa en la síntesis de lípidos, el metabolismo de carbohidratos y la desintoxicación de sustancias.',
    ),
    dict(
        topic='Membrana celular y transporte', difficulty=2, bloom_level=2,
        question_type='opcion_multiple',
        question_text='¿Qué tipo de transporte celular requiere gasto de energía (ATP) para mover sustancias en contra de su gradiente de concentración?',
        answer_text='Transporte activo',
        options=['Transporte activo', 'Difusión simple', 'Ósmosis', 'Difusión facilitada'],
    ),
    dict(
        topic='Membrana celular y transporte', difficulty=2, bloom_level=3,
        question_type='verdadero_falso',
        question_text='En una solución hipertónica, una célula animal tiende a ganar agua y aumentar de volumen.',
        answer_text='Falso. En una solución hipertónica, el agua sale de la célula por ósmosis (hacia donde hay mayor concentración de soluto), por lo que la célula pierde volumen y puede crenarse.',
    ),
    dict(
        topic='Membrana celular y transporte', difficulty=3, bloom_level=4,
        question_type='desarrollo',
        question_text='Explicá por qué la bicapa lipídica de la membrana celular es permeable a moléculas pequeñas y no polares, pero no a iones, y qué mecanismo permite igualmente el paso de estos últimos.',
        answer_text='La bicapa lipídica está formada por colas hidrofóbicas hacia el interior, que dejan pasar libremente moléculas pequeñas no polares (como O2 o CO2) por difusión simple. Los iones, al estar cargados, no pueden atravesar ese ambiente hidrofóbico, por lo que necesitan proteínas de membrana específicas (canales o transportadores) que faciliten su paso mediante difusión facilitada o transporte activo.',
    ),
    dict(
        topic='División celular', difficulty=1, bloom_level=1,
        question_type='opcion_multiple',
        question_text='¿Cuál es el resultado de la mitosis en términos del número de células y su carga genética?',
        answer_text='Dos células hijas genéticamente idénticas a la célula madre',
        options=[
            'Dos células hijas genéticamente idénticas a la célula madre',
            'Cuatro células hijas con la mitad de cromosomas',
            'Una célula hija con el doble de cromosomas',
            'Dos células hijas genéticamente distintas entre sí',
        ],
    ),
    dict(
        topic='División celular', difficulty=2, bloom_level=2,
        question_type='verdadero_falso',
        question_text='La meiosis produce células con la mitad de la carga cromosómica de la célula original, lo que permite mantener constante el número de cromosomas de la especie a través de las generaciones.',
        answer_text='Verdadero.',
    ),
    dict(
        topic='División celular', difficulty=3, bloom_level=4,
        question_type='desarrollo',
        question_text='Explicá por qué el entrecruzamiento (crossing over) que ocurre durante la meiosis es una fuente importante de variabilidad genética.',
        answer_text='Durante la profase I de la meiosis, los cromosomas homólogos se aparean e intercambian segmentos de material genético entre sus cromátidas no hermanas. Esto genera combinaciones nuevas de alelos en los cromosomas resultantes, distintas tanto de las de la madre como del padre, aumentando la diversidad genética de los gametos producidos.',
    ),
    dict(
        topic='La célula y sus organelas', difficulty=1, bloom_level=1,
        question_type='verdadero_falso',
        question_text='Los ribosomas están presentes tanto en células procariotas como en células eucariotas.',
        answer_text='Verdadero. Los ribosomas son la maquinaria de síntesis de proteínas y están presentes en prácticamente todos los tipos celulares.',
    ),
    dict(
        topic='La célula y sus organelas', difficulty=1, bloom_level=1,
        question_type='opcion_multiple',
        question_text='¿Qué organela es responsable de la digestión intracelular mediante enzimas hidrolíticas?',
        answer_text='Lisosoma',
        options=['Lisosoma', 'Mitocondria', 'Aparato de Golgi', 'Ribosoma'],
    ),
    dict(
        topic='La célula y sus organelas', difficulty=2, bloom_level=1,
        question_type='completar_blank',
        question_text='El ______ es la organela encargada de modificar, empaquetar y distribuir proteínas y lípidos sintetizados en el retículo endoplasmático.',
        answer_text='Aparato de Golgi',
    ),
    dict(
        topic='La célula y sus organelas', difficulty=2, bloom_level=2,
        question_type='opcion_multiple',
        question_text='Además del núcleo, ¿qué otra estructura celular contiene su propio ADN?',
        answer_text='La mitocondria',
        options=['La mitocondria', 'El aparato de Golgi', 'El lisosoma', 'El retículo endoplasmático'],
    ),
    dict(
        topic='La célula y sus organelas', difficulty=3, bloom_level=4,
        question_type='desarrollo',
        question_text='Explicá la teoría endosimbiótica sobre el origen de las mitocondrias y qué evidencia la sustenta.',
        answer_text='La teoría endosimbiótica propone que las mitocondrias fueron originalmente bacterias de vida libre que fueron incorporadas por una célula ancestral mayor, estableciendo una relación simbiótica permanente. La evidencia principal es que las mitocondrias tienen su propio ADN circular (similar al bacteriano), se reproducen por división binaria independiente del ciclo celular, y poseen una doble membrana compatible con un origen por fagocitosis.',
    ),
    dict(
        topic='Membrana celular y transporte', difficulty=1, bloom_level=1,
        question_type='verdadero_falso',
        question_text='La ósmosis es un caso particular de difusión que involucra específicamente el movimiento de agua a través de una membrana semipermeable.',
        answer_text='Verdadero.',
    ),
    dict(
        topic='Membrana celular y transporte', difficulty=2, bloom_level=1,
        question_type='opcion_multiple',
        question_text='¿Qué modelo describe la estructura de la membrana plasmática como una bicapa lipídica con proteínas que se desplazan lateralmente?',
        answer_text='Modelo del mosaico fluido',
        options=['Modelo del mosaico fluido', 'Modelo de la doble hélice', 'Teoría celular', 'Modelo de Bohr'],
    ),
    dict(
        topic='Membrana celular y transporte', difficulty=2, bloom_level=1,
        question_type='completar_blank',
        question_text='En la endocitosis, la célula ______ partículas o líquidos del exterior mediante invaginación de la membrana plasmática.',
        answer_text='incorpora',
    ),
    dict(
        topic='Membrana celular y transporte', difficulty=2, bloom_level=2,
        question_type='opcion_multiple',
        question_text='¿Qué tipo de proteína de membrana forma un canal que permite el paso selectivo de iones?',
        answer_text='Proteína canal',
        options=['Proteína canal', 'Proteína estructural', 'Enzima digestiva', 'Proteína motora'],
    ),
    dict(
        topic='Membrana celular y transporte', difficulty=3, bloom_level=4,
        question_type='desarrollo',
        question_text='Comparar difusión simple y difusión facilitada: ¿en qué se parecen y en qué se diferencian?',
        answer_text='Ambas son formas de transporte pasivo, es decir, no requieren gasto de energía y ocurren a favor del gradiente de concentración. Se diferencian en que la difusión simple ocurre directamente a través de la bicapa lipídica (solo para moléculas pequeñas y no polares), mientras que la difusión facilitada requiere una proteína de membrana (canal o transportador) para que moléculas más grandes o cargadas, como la glucosa o los iones, puedan atravesar la membrana.',
    ),
    dict(
        topic='División celular', difficulty=1, bloom_level=1,
        question_type='verdadero_falso',
        question_text='La citocinesis es la división del citoplasma que ocurre después de la división del núcleo.',
        answer_text='Verdadero.',
    ),
    dict(
        topic='División celular', difficulty=2, bloom_level=1,
        question_type='opcion_multiple',
        question_text='¿En qué fase del ciclo celular se duplica el ADN?',
        answer_text='Fase S (síntesis)',
        options=['Fase S (síntesis)', 'Fase G1', 'Fase G2', 'Mitosis'],
    ),
    dict(
        topic='División celular', difficulty=2, bloom_level=1,
        question_type='completar_blank',
        question_text='Durante la ______, los cromosomas duplicados se alinean en el plano ecuatorial de la célula antes de separarse hacia los polos.',
        answer_text='metafase',
    ),
    dict(
        topic='División celular', difficulty=2, bloom_level=2,
        question_type='opcion_multiple',
        question_text='¿Cuántas células resultan al finalizar la meiosis, a partir de una única célula original?',
        answer_text='Cuatro',
        options=['Cuatro', 'Dos', 'Una', 'Ocho'],
    ),
    dict(
        topic='Núcleo y material genético', difficulty=1, bloom_level=1,
        question_type='opcion_multiple',
        question_text='¿Qué estructura nuclear regula el paso de sustancias entre el núcleo y el citoplasma?',
        answer_text='Poro nuclear',
        options=['Poro nuclear', 'Nucléolo', 'Cromátida', 'Centrómero'],
    ),
    dict(
        topic='Núcleo y material genético', difficulty=2, bloom_level=2,
        question_type='verdadero_falso',
        question_text='La cromatina se condensa en cromosomas visibles al microscopio óptico únicamente durante la división celular.',
        answer_text='Verdadero. En el resto del ciclo celular, el ADN permanece disperso como cromatina dentro del núcleo.',
    ),
    dict(
        topic='Núcleo y material genético', difficulty=2, bloom_level=1,
        question_type='completar_blank',
        question_text='El ______ es la región del núcleo donde se sintetiza el ARN ribosómico.',
        answer_text='nucléolo',
    ),
    dict(
        topic='Núcleo y material genético', difficulty=1, bloom_level=1,
        question_type='opcion_multiple',
        question_text='¿Qué molécula constituye la información genética almacenada en el núcleo de una célula eucariota?',
        answer_text='ADN',
        options=['ADN', 'ARN mensajero', 'Proteína', 'ATP'],
    ),
    dict(
        topic='Núcleo y material genético', difficulty=3, bloom_level=4,
        question_type='desarrollo',
        question_text='Explicá la diferencia entre eucromatina y heterocromatina en términos de su actividad transcripcional.',
        answer_text='La eucromatina es cromatina laxa, poco condensada, que resulta accesible para la maquinaria de transcripción — sus genes suelen estar activos. La heterocromatina está muy condensada y compactada, lo que la vuelve inaccesible para esa maquinaria, por lo que sus genes permanecen generalmente inactivos (silenciados).',
    ),
]


class Command(BaseCommand):
    help = (
        'Crea/actualiza el contenido de ejemplo del sistema (instituciones, materias, '
        'temas, resultados de aprendizaje y preguntas), en propiedad del usuario técnico '
        'SEED_CONTENT_USERNAME. Idempotente: se puede correr en cada deploy.'
    )

    def handle(self, *args, **options):
        username = getattr(settings, 'SEED_CONTENT_USERNAME', 'educaapp_demo')
        try:
            seed_user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(
                f'No existe el usuario "{username}". Corré antes las migraciones '
                '(material.0042_seed_content_user crea este usuario).'
            )

        with transaction.atomic():
            institucion1 = self._get_institution(
                'Universidad Nacional Demostración',
                crest_initials='UND',
                crest_colors=('#1c3d5a', '#d4af37'),
            )
            campus1 = self._get_campus(institucion1, 'Sede Central')
            facultad1 = self._get_faculty(institucion1, 'Facultad de Ciencias Exactas e Ingeniería')
            carrera1 = self._get_career(
                'Licenciatura en Sistemas de Información',
                faculties=[facultad1],
                campuses=[campus1],
            )

            institucion2 = self._get_institution(
                'Instituto Superior del Profesorado Demo',
                crest_initials='ISP',
                crest_colors=('#1b5e20', '#f4ede4'),
            )
            campus2 = self._get_campus(institucion2, 'Sede Instituto Central')
            facultad2 = self._get_faculty(institucion2, 'Departamento de Ciencias Biológicas')
            carrera2 = self._get_career(
                'Profesorado en Biología',
                faculties=[facultad2],
                campuses=[campus2],
            )

            self._seed_subject(
                institution=institucion1,
                seed_user=seed_user,
                subject_name='Programación I',
                topics=PROGRAMACION_TOPICS,
                outcomes=PROGRAMACION_OUTCOMES,
                questions=PROGRAMACION_QUESTIONS,
                career=carrera1,
            )
            self._seed_subject(
                institution=institucion1,
                seed_user=seed_user,
                subject_name='Bases de Datos',
                topics=BASES_DE_DATOS_TOPICS,
                outcomes=BASES_DE_DATOS_OUTCOMES,
                questions=BASES_DE_DATOS_QUESTIONS,
                career=carrera1,
            )
            self._seed_subject(
                institution=institucion2,
                seed_user=seed_user,
                subject_name='Biología Celular',
                topics=BIOLOGIA_TOPICS,
                outcomes=BIOLOGIA_OUTCOMES,
                questions=BIOLOGIA_QUESTIONS,
                career=carrera2,
            )

        self.stdout.write(self.style.SUCCESS('Contenido de ejemplo sincronizado correctamente.'))

    def _get_institution(self, name, crest_initials=None, crest_colors=None):
        institucion, _ = InstitutionV2.objects.get_or_create(
            name=name,
            defaults={'is_active': True},
        )
        # Solo genera el escudo ficticio si todavía no tiene ningún logo
        # (ni subido a mano ni de una corrida anterior) — idempotente, no
        # pisa un logo real que alguien haya cargado para esta institución.
        if crest_initials and not institucion.logo_b64 and not institucion.logo:
            primary, secondary = crest_colors or ('#1c3d5a', '#d4af37')
            institucion.logo_b64 = _fake_crest_svg(crest_initials, primary, secondary)
            institucion.save(update_fields=['logo_b64'])
        return institucion

    def _get_campus(self, institution, name):
        campus, _ = CampusV2.objects.get_or_create(
            institution=institution, name=name, defaults={'is_active': True},
        )
        return campus

    def _get_faculty(self, institution, name):
        faculty, _ = FacultyV2.objects.get_or_create(
            institution=institution, name=name, defaults={'is_active': True},
        )
        return faculty

    def _get_career(self, name, *, faculties, campuses):
        career, _ = Career.objects.get_or_create(name=name)
        career.faculties.add(*faculties)
        career.campus.add(*campuses)
        return career

    def _seed_subject(self, *, institution, seed_user, subject_name, topics, outcomes, questions, career=None):
        # Puede haber más de un Subject con este nombre (ej. una materia real
        # de un docente creada aparte por clean_seed_subjects, ver
        # [[project_subject_topic_global_sharing_bug]]) — se identifica la
        # fila semilla específicamente por is_seed_demo=True, nunca por
        # nombre a secas (que ya no es único).
        subject = Subject.objects.filter(name=subject_name, is_seed_demo=True).first()
        if not subject:
            subject = Subject.objects.filter(
                name=subject_name, questions__user__username=seed_user.username
            ).distinct().first()
        if not subject:
            subject = Subject.objects.filter(name=subject_name, is_seed_demo=False).first() \
                or Subject.objects.create(name=subject_name)
        if not subject.is_seed_demo:
            subject.is_seed_demo = True
            subject.save(update_fields=['is_seed_demo'])

        InstitutionSubject.objects.get_or_create(
            institution=institution,
            subject=subject,
            defaults={'is_core': True, 'is_active': True},
        )

        if career is not None:
            career.subjects.add(subject)
            subject.careers.add(career)

        for description in outcomes:
            LearningOutcome.objects.get_or_create(
                subject=subject,
                description=description,
            )

        topic_objs = {}
        for name, importance in topics:
            topic, _ = Topic.objects.get_or_create(
                subject=subject,
                name=name,
                defaults={'importance': importance},
            )
            topic_objs[name] = topic

        for q in questions:
            topic = topic_objs[q['topic']]
            options = q.get('options')
            defaults = {
                'answer_text': q['answer_text'],
                'question_type': q['question_type'],
                'difficulty': q['difficulty'],
                'bloom_level': q.get('bloom_level'),
                'ai_approved': True,
            }
            if options:
                defaults['options_json'] = self._to_options_json(options)

            question, created = Question.objects.get_or_create(
                user=seed_user,
                topic=topic,
                question_text=q['question_text'],
                defaults=defaults,
            )
            if created:
                question.subjects.add(subject)

    @staticmethod
    def _to_options_json(options):
        import json
        return json.dumps(options, ensure_ascii=False)
