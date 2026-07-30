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
]

BASES_DE_DATOS_TOPICS = [
    ('Modelo relacional', 5),
    ('Consultas SQL', 5),
    ('Normalización', 4),
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
]

BIOLOGIA_TOPICS = [
    ('La célula y sus organelas', 5),
    ('Membrana celular y transporte', 4),
    ('División celular', 4),
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
            institucion1 = self._get_institution('Universidad Nacional Demostración')
            campus1 = self._get_campus(institucion1, 'Sede Central')
            facultad1 = self._get_faculty(institucion1, 'Facultad de Ciencias Exactas e Ingeniería')
            carrera1 = self._get_career(
                'Licenciatura en Sistemas de Información',
                faculties=[facultad1],
                campuses=[campus1],
            )

            institucion2 = self._get_institution('Instituto Superior del Profesorado Demo')
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

    def _get_institution(self, name):
        institucion, _ = InstitutionV2.objects.get_or_create(
            name=name,
            defaults={'is_active': True},
        )
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
        subject, _ = Subject.objects.get_or_create(name=subject_name)

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
