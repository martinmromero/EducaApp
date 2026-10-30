# Imagen para correr EducaApp en cualquier hosting que acepte contenedores (Fly.io, Railway, DigitalOcean App
# Platform, un VPS con Docker, etc.). Guía completa: docs/migrar_hosting.md
#
# NO PROBADA: se escribió sin Docker disponible. Si falla algo en el primer build, el error va a estar en el paso
# que se indica; el resto de la guía (Procfile + variables) sigue valiendo para hostings sin Docker.
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# settings.py exige DATABASE_URL al importarse, incluso para collectstatic: se le da un valor de relleno solo en
# este paso (no se guarda en la imagen). La base real llega en tiempo de ejecución.
RUN DATABASE_URL=postgres://build:build@localhost/build SECRET_KEY=build \
    python manage.py collectstatic --noinput --clear

EXPOSE 8000

# Al arrancar: migrar y sembrar (los mismos pasos que el Build Command de Render, ver render.yaml), y servir.
# gunicorn toma el puerto de $PORT si el hosting lo define; si no, 8000. Un solo worker a propósito (la caché de
# sesiones es en memoria, ver settings.py).
CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py clean_seed_subjects && python manage.py seed_demo_content && python manage.py seed_test_checklist && python manage.py ensure_training_spare_pool && (python manage.py createsuperuser --noinput || true) && exec gunicorn educaapp.wsgi --workers 1 --threads 4 --timeout 120 --bind 0.0.0.0:${PORT:-8000}"]
