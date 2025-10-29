"""
Ejemplo de Uso del Document Processor
======================================
Demuestra todas las funcionalidades del módulo con ejemplos prácticos.

Ejecutar: python example_document_processor.py
"""

from document_processor import DocumentProcessor, process_document, quick_token_count
import json


def ejemplo_crear_pdf_prueba():
    """Crea un PDF de prueba para demostración."""
    import fitz
    
    print("\n" + "="*70)
    print("1. CREANDO PDF DE PRUEBA")
    print("="*70)
    
    # Crear PDF de prueba
    doc = fitz.open()
    
    # Página 1 - Portada
    page1 = doc.new_page()
    page1.insert_text((100, 100), "Mi Tesis de Investigación", fontsize=20)
    page1.insert_text((100, 140), "Autor: Juan Pérez", fontsize=12)
    page1.insert_text((100, 160), "Universidad Nacional", fontsize=12)
    
    # Página 2 - Capítulo 1
    page2 = doc.new_page()
    page2.insert_text((100, 50), "Encabezado del Documento - Página 2", fontsize=8)  # Header repetitivo
    page2.insert_text((100, 100), "Capítulo 1: Introducción", fontsize=16)
    page2.insert_text((100, 140), "Este es el contenido del capítulo 1.", fontsize=11)
    page2.insert_text((100, 160), "Aquí explicamos los conceptos básicos de nuestra investigación.", fontsize=11)
    page2.insert_text((100, 180), "Es fundamental entender estos principios antes de continuar.", fontsize=11)
    page2.insert_text((100, 750), "2", fontsize=8)  # Número de página
    
    # Página 3 - Capítulo 1 continúa
    page3 = doc.new_page()
    page3.insert_text((100, 50), "Encabezado del Documento - Página 3", fontsize=8)  # Header repetitivo
    page3.insert_text((100, 100), "Continuación del Capítulo 1...", fontsize=11)
    page3.insert_text((100, 120), "Más contenido importante sobre la introducción.", fontsize=11)
    page3.insert_text((100, 750), "3", fontsize=8)
    
    # Página 4 - Capítulo 2
    page4 = doc.new_page()
    page4.insert_text((100, 50), "Encabezado del Documento - Página 4", fontsize=8)
    page4.insert_text((100, 100), "Capítulo 2: Metodología", fontsize=16)
    page4.insert_text((100, 140), "En este capítulo describimos los métodos utilizados.", fontsize=11)
    page4.insert_text((100, 160), "Aplicamos técnicas cuantitativas y cualitativas.", fontsize=11)
    page4.insert_text((100, 750), "4", fontsize=8)
    
    # Guardar con TOC
    toc = [
        [1, "Capítulo 1: Introducción", 2],
        [1, "Capítulo 2: Metodología", 4]
    ]
    doc.set_toc(toc)
    
    doc.save("ejemplo_documento.pdf")
    doc.close()
    
    print("✓ PDF de prueba creado: ejemplo_documento.pdf")
    print("  - 4 páginas")
    print("  - 2 capítulos con TOC")
    print("  - Headers repetitivos para demostrar limpieza")


def ejemplo_procesar_pdf():
    """Demuestra el procesamiento completo de un PDF."""
    print("\n" + "="*70)
    print("2. PROCESANDO PDF")
    print("="*70)
    
    processor = DocumentProcessor()
    
    # Procesar con todas las opciones
    result = processor.process_pdf(
        "ejemplo_documento.pdf",
        remove_headers=True,
        remove_footers=True,
        extract_toc=True
    )
    
    # Mostrar resumen
    print("\n" + processor.get_stats_summary(result))
    
    # Mostrar TOC
    if result['toc']:
        print("\nTabla de Contenidos detectada:")
        for item in result['toc']:
            indent = "  " * (item['level'] - 1)
            print(f"{indent}- {item['title']} (página {item['page']})")
    
    # Mostrar capítulos
    print("\nCapítulos extraídos:")
    for i, chapter in enumerate(result['chapters'], 1):
        print(f"\n  Capítulo {i}: {chapter['title']}")
        print(f"  Páginas: {chapter['pages']}")
        print(f"  Tokens: {chapter['tokens']}")
        print(f"  Preview: {chapter['content'][:100]}...")
    
    # Exportar a JSON
    processor.export_to_json(result, "ejemplo_resultado.json")
    print("\n✓ Resultado exportado a: ejemplo_resultado.json")
    
    return result


def ejemplo_contar_tokens():
    """Demuestra el conteo de tokens."""
    print("\n" + "="*70)
    print("3. CONTEO DE TOKENS")
    print("="*70)
    
    processor = DocumentProcessor()
    
    textos_ejemplo = [
        "Este es un texto corto.",
        "Este es un texto mucho más largo que contiene varias oraciones. " * 10,
        "GPT-4 utiliza el encoding cl100k_base para contar tokens. "
        "Cada token puede ser una palabra, parte de palabra, o símbolo. "
        "Esto es importante para calcular costos de API."
    ]
    
    print("\nComparación de tokens:")
    for i, texto in enumerate(textos_ejemplo, 1):
        tokens = processor.count_tokens(texto)
        palabras = len(texto.split())
        caracteres = len(texto)
        
        print(f"\n  Texto {i}:")
        print(f"    Caracteres: {caracteres}")
        print(f"    Palabras: {palabras}")
        print(f"    Tokens (GPT-4): {tokens}")
        print(f"    Ratio tokens/palabras: {tokens/palabras:.2f}")


def ejemplo_dividir_por_tokens():
    """Demuestra la división de texto por límite de tokens."""
    print("\n" + "="*70)
    print("4. DIVISIÓN POR LÍMITE DE TOKENS")
    print("="*70)
    
    processor = DocumentProcessor()
    
    # Texto largo de ejemplo
    texto_largo = """
    La inteligencia artificial ha revolucionado múltiples campos de estudio.
    Desde el procesamiento de lenguaje natural hasta la visión por computadora,
    los avances han sido extraordinarios en las últimas décadas.
    """ * 50  # Repetir para hacer más largo
    
    tokens_totales = processor.count_tokens(texto_largo)
    print(f"\nTexto original: {tokens_totales} tokens")
    
    # Dividir en chunks de 100 tokens
    chunks = processor.split_by_token_limit(texto_largo, max_tokens=100)
    
    print(f"Dividido en {len(chunks)} chunks de máximo 100 tokens:")
    for i, chunk in enumerate(chunks, 1):
        chunk_tokens = processor.count_tokens(chunk)
        print(f"  Chunk {i}: {chunk_tokens} tokens")


def ejemplo_optimizacion():
    """Demuestra la optimización de texto para IA."""
    print("\n" + "="*70)
    print("5. OPTIMIZACIÓN DE TEXTO PARA IA")
    print("="*70)
    
    processor = DocumentProcessor()
    
    texto_sucio = """
    Este    texto   tiene    muchos     espacios.
    
    
    
    También tiene saltos de línea innecesarios.
    
    
    Además incluye URLs: https://www.ejemplo.com/pagina-larga
    Y emails: contacto@ejemplo.com
    
    
    Todo esto consume tokens sin aportar valor.
    """
    
    print("\nTexto original:")
    print(f"  Tokens: {processor.count_tokens(texto_sucio)}")
    print(f"  Contenido:\n{texto_sucio}")
    
    # Optimizar
    texto_limpio = processor.optimize_for_ai(
        texto_sucio,
        remove_extra_whitespace=True,
        remove_urls=True,
        remove_emails=True
    )
    
    print("\nTexto optimizado:")
    print(f"  Tokens: {processor.count_tokens(texto_limpio)}")
    print(f"  Contenido:\n{texto_limpio}")
    
    ahorro = processor.count_tokens(texto_sucio) - processor.count_tokens(texto_limpio)
    porcentaje = (ahorro / processor.count_tokens(texto_sucio)) * 100
    print(f"\n  Ahorro: {ahorro} tokens ({porcentaje:.1f}%)")


def ejemplo_funcion_rapida():
    """Demuestra las funciones de conveniencia."""
    print("\n" + "="*70)
    print("6. FUNCIONES DE CONVENIENCIA")
    print("="*70)
    
    # Función rápida para cualquier tipo de documento
    print("\nUsando process_document() - detecta automáticamente el formato:")
    result = process_document("ejemplo_documento.pdf")
    print(f"  Documento procesado: {result['metadata'].get('title', 'Sin título')}")
    print(f"  Total tokens: {result['stats']['total_tokens']}")
    
    # Conteo rápido
    print("\nUsando quick_token_count() - solo cuenta tokens:")
    tokens = quick_token_count("ejemplo_documento.pdf")
    print(f"  Tokens totales: {tokens}")


def ejemplo_integracion_ia():
    """Ejemplo de cómo usar el módulo para preparar datos para IA."""
    print("\n" + "="*70)
    print("7. INTEGRACIÓN CON IA (Ejemplo de flujo)")
    print("="*70)
    
    processor = DocumentProcessor()
    
    print("\nFlujo típico para enviar documento a GPT-4:")
    print("\n1. Procesar documento")
    result = processor.process_pdf("ejemplo_documento.pdf")
    
    print("\n2. Seleccionar capítulo relevante")
    capitulo = result['chapters'][0]
    print(f"   Capítulo seleccionado: {capitulo['title']}")
    print(f"   Tokens: {capitulo['tokens']}")
    
    print("\n3. Verificar límite de tokens")
    LIMITE_GPT4 = 8000  # Ejemplo: GPT-4 con 8k tokens de contexto
    if capitulo['tokens'] > LIMITE_GPT4:
        print(f"   ⚠️ Excede límite ({capitulo['tokens']} > {LIMITE_GPT4})")
        print("   → Dividiendo en chunks...")
        chunks = processor.split_by_token_limit(capitulo['content'], max_tokens=LIMITE_GPT4)
        print(f"   → Dividido en {len(chunks)} chunks")
    else:
        print(f"   ✓ Dentro del límite ({capitulo['tokens']} <= {LIMITE_GPT4})")
        chunks = [capitulo['content']]
    
    print("\n4. Optimizar antes de enviar")
    chunk_optimizado = processor.optimize_for_ai(chunks[0])
    tokens_antes = processor.count_tokens(chunks[0])
    tokens_despues = processor.count_tokens(chunk_optimizado)
    print(f"   Tokens antes: {tokens_antes}")
    print(f"   Tokens después: {tokens_despues}")
    print(f"   Ahorro: {tokens_antes - tokens_despues} tokens")
    
    print("\n5. Preparar prompt para IA")
    prompt = f"""
Analiza el siguiente capítulo de un documento académico:

Título: {capitulo['title']}

Contenido:
{chunk_optimizado}

Por favor, genera un resumen ejecutivo de 3 puntos clave.
"""
    
    tokens_prompt = processor.count_tokens(prompt)
    print(f"   Tokens del prompt completo: {tokens_prompt}")
    print(f"   ✓ Listo para enviar a API de OpenAI/Claude")


# ============================================================================
# EJECUTAR TODOS LOS EJEMPLOS
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*70)
    print(" DEMOSTRACIÓN: Document Processor Module")
    print("="*70)
    
    try:
        # 1. Crear PDF de prueba
        ejemplo_crear_pdf_prueba()
        
        # 2. Procesar PDF completo
        ejemplo_procesar_pdf()
        
        # 3. Contar tokens
        ejemplo_contar_tokens()
        
        # 4. Dividir por límite
        ejemplo_dividir_por_tokens()
        
        # 5. Optimizar texto
        ejemplo_optimizacion()
        
        # 6. Funciones rápidas
        ejemplo_funcion_rapida()
        
        # 7. Integración con IA
        ejemplo_integracion_ia()
        
        print("\n" + "="*70)
        print(" ✓ DEMOSTRACIÓN COMPLETADA")
        print("="*70)
        print("\nArchivos generados:")
        print("  - ejemplo_documento.pdf")
        print("  - ejemplo_resultado.json")
        print("\nPara usar en tu proyecto:")
        print("  from document_processor import DocumentProcessor")
        print("  processor = DocumentProcessor()")
        print("  result = processor.process_pdf('tu_archivo.pdf')")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
