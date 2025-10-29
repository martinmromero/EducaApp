# ============================================================================
# 🚀 INSTALACIÓN: Document Processing Module
# ============================================================================
# Ejecutá estos comandos en PowerShell desde la raíz del proyecto
# ============================================================================

# ----------------------------------------------------------------------------
# ✅ Paso 1: Activar entorno virtual
# ----------------------------------------------------------------------------
.\.venv\Scripts\Activate.ps1

# ----------------------------------------------------------------------------
# 📦 Paso 2: Elegí UNA de estas opciones
# ----------------------------------------------------------------------------

# OPCIÓN A: Stack Completo (RECOMENDADO)
# ----------------------------------------
# Incluye: PyMuPDF, pdfplumber, tiktoken, markdownify
# Instala las 4 librerías nuevas críticas
pip install PyMuPDF==1.25.1 pdfplumber==0.11.0 tiktoken==0.9.0 markdownify==0.13.1

# OPCIÓN B: Stack Minimalista
# ----------------------------------------
# Solo lo esencial: PyMuPDF (reemplaza PyPDF2) + tiktoken (conteo de tokens)
# pip install PyMuPDF==1.25.1 tiktoken==0.9.0

# OPCIÓN C: Desde archivo requirements
# ----------------------------------------
# Instala todas las del archivo requirements_document_processing.txt
# pip install -r requirements_document_processing.txt

# ----------------------------------------------------------------------------
# ✅ Paso 3: Verificar instalación
# ----------------------------------------------------------------------------

# Test rápido de imports
python -c "import fitz; import pdfplumber; import tiktoken; import docx; import pptx; print('✅ Todas las librerías instaladas correctamente')"

# Ver versiones instaladas
python -c "import fitz; import tiktoken; print(f'PyMuPDF: {fitz.__version__}\ntiktoken: {tiktoken.__version__}')"

# ----------------------------------------------------------------------------
# 🧪 Paso 4: Test funcional con un PDF de ejemplo
# ----------------------------------------------------------------------------

# Guardá este código en test_document_processing.py y corré:
# python test_document_processing.py

<#
# test_document_processing.py
import fitz  # PyMuPDF
import tiktoken

def test_pdf_processing():
    # Creá un PDF de prueba
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((100, 100), "Capítulo 1: Introducción\nEste es un texto de prueba.")
    doc.save("test.pdf")
    doc.close()
    
    # Abrilo y procesá
    doc = fitz.open("test.pdf")
    texto = ""
    for page in doc:
        texto += page.get_text()
    doc.close()
    
    print(f"📄 Texto extraído:\n{texto}")
    
    # Contá tokens
    encoding = tiktoken.get_encoding("cl100k_base")  # GPT-4
    tokens = len(encoding.encode(texto))
    print(f"\n🧮 Tokens (GPT-4): {tokens}")
    
    print("\n✅ Test completado exitosamente")

if __name__ == "__main__":
    test_pdf_processing()
#>

# ----------------------------------------------------------------------------
# 🔄 Paso 5 (Opcional): Actualizar requirements.txt principal
# ----------------------------------------------------------------------------

# Si querés agregar las nuevas librerías al requirements.txt principal:
# Editá manualmente o usá este comando para mergear:

# Opción manual:
# Abrí requirements.txt y agregá estas líneas después de las existentes:
<#
PyMuPDF==1.25.1
pdfplumber==0.11.0
tiktoken==0.9.0
markdownify==0.13.1
#>

# Opción automática (PowerShell):
# Add-Content -Path .\requirements.txt -Value "`nPyMuPDF==1.25.1`npdfplumber==0.11.0`ntiktoken==0.9.0`nmarkdownify==0.13.1"

# ----------------------------------------------------------------------------
# 📊 Paso 6: Generar requirements.txt actualizado (freeze)
# ----------------------------------------------------------------------------

# Si querés un snapshot completo del entorno:
pip freeze > requirements_full_$(Get-Date -Format yyyyMMdd).txt

# ----------------------------------------------------------------------------
# 🗑️ Paso 7 (Opcional): Desinstalar PyPDF2 si no lo usás más
# ----------------------------------------------------------------------------

# PyMuPDF reemplaza completamente a PyPDF2, podés quitarlo:
# pip uninstall PyPDF2 -y

# Y eliminar la línea de requirements.txt:
# (Get-Content .\requirements.txt) | Where-Object { $_ -notmatch 'PyPDF2' } | Set-Content .\requirements.txt

# ============================================================================
# 📚 RECURSOS Y EJEMPLOS
# ============================================================================

# Documentación oficial:
# - PyMuPDF: https://pymupdf.readthedocs.io/
# - pdfplumber: https://github.com/jsvine/pdfplumber
# - tiktoken: https://github.com/openai/tiktoken
# - python-docx: https://python-docx.readthedocs.io/
# - python-pptx: https://python-pptx.readthedocs.io/

# ============================================================================
# ⚠️ TROUBLESHOOTING
# ============================================================================

# Error: "Could not find a version that satisfies the requirement PyMuPDF"
# Solución: Actualizá pip primero
# python -m pip install --upgrade pip

# Error: "Microsoft Visual C++ 14.0 or greater is required"
# Solución: Instalá las Build Tools de Microsoft
# https://visualstudio.microsoft.com/visual-cpp-build-tools/

# Error con tiktoken: "No module named 'tiktoken_ext'"
# Solución: Reinstalá con --force-reinstall
# pip install tiktoken==0.9.0 --force-reinstall

# ============================================================================
# 🎯 RESUMEN DE COMANDOS COPIABLES
# ============================================================================

<#
# 1) Activar entorno
.\.venv\Scripts\Activate.ps1

# 2) Instalar stack completo
pip install PyMuPDF==1.25.1 pdfplumber==0.11.0 tiktoken==0.9.0 markdownify==0.13.1

# 3) Verificar
python -c "import fitz, pdfplumber, tiktoken; print('✅ OK')"

# 4) (Opcional) Actualizar requirements.txt
Add-Content -Path .\requirements.txt -Value "`nPyMuPDF==1.25.1`npdfplumber==0.11.0`ntiktoken==0.9.0`nmarkdownify==0.13.1"
#>
