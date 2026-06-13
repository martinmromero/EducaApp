"""
Script para cargar datos locales en Neon.
Los signals ya tienen raw=True check, no crean Profiles durante loaddata.

Uso:
    $env:DATABASE_URL="postgresql://..."
    python load_to_neon.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'educaapp.settings')
django.setup()

from django.db import connection
from django.core.management import call_command

# 1. Asegurar esquema completo
print("Asegurando esquema actualizado...")
call_command('migrate', '--run-syncdb', verbosity=0)
print("Migraciones OK.")

# 2. Truncar todas las tablas (excepto django_migrations)
print("Truncando tablas en Neon...")
with connection.cursor() as cursor:
    cursor.execute("""
        SELECT tablename FROM pg_tables
        WHERE schemaname = 'public'
        AND tablename != 'django_migrations'
    """)
    tables = [row[0] for row in cursor.fetchall()]
    tables_sql = ', '.join(f'"{t}"' for t in tables)
    cursor.execute(f"TRUNCATE TABLE {tables_sql} RESTART IDENTITY CASCADE")
print(f"Truncadas {len(tables)} tablas OK.")

# 3. Cargar fixture
print("Cargando datos...")
call_command('loaddata', 'datos_locales.json', verbosity=1)
print("--- CARGA COMPLETA ---")

