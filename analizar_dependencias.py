import os
import re
import subprocess
from collections import defaultdict

# Configuración
PROJECT_ROOT = os.getcwd()  # Directorio raíz del proyecto
IGNORE_DIRS = [".venv", "venv", "__pycache__", "migrations"]  # Carpetas a ignorar
PYTHON_FILES = []  # Lista de archivos .py en el proyecto

# Obtener la lista de dependencias instaladas
def get_installed_packages():
    result = subprocess.run(["pip", "freeze"], capture_output=True, text=True)
    packages = [line.split("==")[0].lower() for line in result.stdout.splitlines()]
    return set(packages)

# Buscar archivos .py en el proyecto
def find_python_files(directory):
    python_files = []
    for root, dirs, files in os.walk(directory):
        # Ignorar carpetas no deseadas
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        for file in files:
            if file.endswith(".py"):
                python_files.append(os.path.join(root, file))
    return python_files

# Analizar importaciones en los archivos .py
def analyze_imports(python_files):
    imports = defaultdict(int)
    import_pattern = re.compile(r"^\s*(?:from|import)\s+([\w\.]+)")

    for file in python_files:
        with open(file, "r", encoding="utf-8") as f:
            for line in f:
                match = import_pattern.match(line)
                if match:
                    module = match.group(1).split(".")[0].lower()
                    imports[module] += 1
    return imports

# Comparar importaciones con dependencias instaladas
def compare_imports_with_packages(imports, installed_packages):
    used_packages = set()
    unused_packages = installed_packages.copy()

    for module, count in imports.items():
        if module in installed_packages:
            used_packages.add(module)
            unused_packages.discard(module)
    
    return used_packages, unused_packages

# Generar informe
def generate_report(used_packages, unused_packages):
    print("=== Dependencias usadas ===")
    for package in sorted(used_packages):
        print(f"- {package}")

    print("\n=== Dependencias no usadas ===")
    for package in sorted(unused_packages):
        print(f"- {package}")

def main():
    print("Analizando dependencias...\n")
    
    # Paso 1: Obtener dependencias instaladas
    installed_packages = get_installed_packages()
    print(f"Se encontraron {len(installed_packages)} dependencias instaladas.")

    # Paso 2: Buscar archivos .py en el proyecto
    python_files = find_python_files(PROJECT_ROOT)
    print(f"Se encontraron {len(python_files)} archivos .py en el proyecto.")

    # Paso 3: Analizar importaciones
    imports = analyze_imports(python_files)
    print(f"Se encontraron {len(imports)} módulos importados en el código.")

    # Paso 4: Comparar importaciones con dependencias instaladas
    used_packages, unused_packages = compare_imports_with_packages(imports, installed_packages)
    print(f"\nSe identificaron {len(used_packages)} dependencias usadas y {len(unused_packages)} no usadas.")

    # Paso 5: Generar informe
    generate_report(used_packages, unused_packages)

if __name__ == "__main__":
    main()