"""
Script de prueba para validar extracción de metadata de libros PDF.
Ejecutar: python test_metadata_extraction.py
"""

import sys
sys.path.insert(0, '.')

from material.ia_processor import extract_book_metadata

def test_pdf(pdf_path):
    """Prueba la extracción de metadata de un PDF."""
    print("\n" + "="*70)
    print(f"Analizando: {pdf_path.split('/')[-1]}")
    print("="*70)
    
    try:
        metadata = extract_book_metadata(pdf_path)
        
        # Mostrar resultados
        for key, value in metadata.items():
            status = "✓" if value else "✗"
            value_str = str(value) if value else "(no detectado)"
            print(f"  {status} {key.upper():12} : {value_str}")
        
        # Calcular score
        fields_detected = sum(1 for v in metadata.values() if v)
        total_fields = len(metadata)
        score = (fields_detected / total_fields) * 100
        
        print(f"\n  Score: {fields_detected}/{total_fields} campos ({score:.1f}%)")
        
        return metadata
        
    except Exception as e:
        print(f"  ✗ ERROR: {e}")
        return None


if __name__ == "__main__":
    print("\n" + "="*70)
    print("TEST DE EXTRACCIÓN DE METADATA DE LIBROS PDF")
    print("="*70)
    
    # PDF de prueba
    test_pdf_path = r"media\contenidos\La_docencia_universitaria_en_tiempos_de_IA.pdf"
    
    metadata = test_pdf(test_pdf_path)
    
    print("\n" + "="*70)
    print("VALIDACIÓN COMPLETA")
    print("="*70)
    
    if metadata:
        critical_fields = ['isbn', 'title', 'year']
        all_critical = all(metadata.get(field) for field in critical_fields)
        
        if all_critical:
            print("✓ Todos los campos críticos (ISBN, Título, Año) fueron detectados")
        else:
            print("✗ Faltan campos críticos:")
            for field in critical_fields:
                if not metadata.get(field):
                    print(f"    - {field.upper()}")
        
        # Recomendaciones
        print("\nRECOMENDACIONES:")
        if not metadata.get('edition'):
            print("  • Edición no detectada - Verificar si el PDF menciona 'Primera edición', '2da edición', etc.")
        if not metadata.get('publisher'):
            print("  • Editorial no detectada - Buscar 'Editorial:', 'Ediciones', 'Publisher' en páginas iniciales")
        if not metadata.get('author'):
            print("  • Autor no detectado - Revisar metadata del PDF o primera página")
    
    print("\n" + "="*70)
    print("¡Prueba completada!")
    print("="*70)
