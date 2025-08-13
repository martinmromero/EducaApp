from material.models import Contenido, Question

def limpiar_contenidos_automaticos():
    # Buscar contenidos automáticos por título
    titulos_auto = [
        "Contenido Automático",
        "Contenido generado automáticamente",
        "Contenido por Defecto"
    ]
    contenidos_auto = Contenido.objects.filter(title__in=titulos_auto)
    print(f"Encontrados {contenidos_auto.count()} contenidos automáticos.")
    # Desasociar preguntas
    preguntas_afectadas = Question.objects.filter(contenido__in=contenidos_auto)
    print(f"Desasociando {preguntas_afectadas.count()} preguntas...")
    preguntas_afectadas.update(contenido=None)
    # Eliminar contenidos automáticos
    eliminados = contenidos_auto.count()
    contenidos_auto.delete()
    print(f"Eliminados {eliminados} contenidos automáticos.")

if __name__ == "__main__":
    limpiar_contenidos_automaticos()
