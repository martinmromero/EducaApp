# Plan de contingencia: migrar EducaApp a otro hosting y a otra base

Qué hacer si Render o Neon dejan de funcionar. Escrito el 2026-10-29. Los precios cambian seguido: **antes de contratar nada, verificar en la página oficial** (los enlaces están en la sección 7).

## 1. Qué hay y dónde vive

| Pieza | Hoy | Se puede reemplazar por |
|---|---|---|
| Aplicación (Django + gunicorn) | Render, plan gratuito | Cualquier hosting que corra Python 3.11 o un contenedor |
| Base de datos (PostgreSQL) | Neon, plan gratuito | Cualquier PostgreSQL (solo Postgres: SQLite no está soportado) |
| Dominio público | `educaapp.vercel.app` (Vercel solo redirige hacia Render) | Cambiar el destino en Vercel, o un dominio propio |
| Archivos estáticos | WhiteNoise, dentro de la propia app | No requieren nada aparte |
| Correo | No se usa (`console`) | — |
| Claves de IA (Groq, Gemini, de cada usuario) | **Dentro de la base**, cifradas con `SECRET_KEY` | Viajan con el volcado de la base |

**Ningún dato crítico vive en el disco de la app.** Las imágenes de preguntas y los logos de instituciones se guardan en la base (campos `*_b64`). Los archivos subidos en "Contenidos" son temporales por diseño: se borran al cerrar sesión y el registro queda en la base. Por eso la carpeta `media/` **no se migra**.

## 2. Lo único irreemplazable: guardar estas dos cosas fuera de Render y Neon

1. **`SECRET_KEY`.** De ella se deriva el cifrado de las claves de IA guardadas en la base. Si se pierde o cambia, la base sigue sirviendo pero esas claves dejan de poder leerse y hay que volver a cargarlas en Django Admin → Configuraciones globales de IA. Guardarla en un gestor de contraseñas.
2. **Una copia reciente de la base (volcado).** Neon gratis solo permite restaurar hasta **6 horas** atrás y no hace copias externas: si la cuenta de Neon se pierde, la base se pierde. Hacer un volcado cada semana y antes de cada cambio grande, y guardarlo en otro lugar (disco propio, Drive).

Volcado (necesita las herramientas cliente de PostgreSQL, versión igual o mayor a la del servidor; en Windows suelen quedar en `C:\Program Files\PostgreSQL\<versión>\bin`. En la máquina de desarrollo `pg_dump` no está en el PATH):

```bash
pg_dump "postgres://USUARIO:CLAVE@HOST/BASE?sslmode=require" --format=custom --no-owner --no-acl -f educaapp_AAAA-MM-DD.dump
```

La cadena de conexión de Neon está en Render → Environment → `DATABASE_URL` (o en el panel de Neon → Connection string, con la opción "Direct", no "Pooled").

Alternativa sin herramientas de Postgres: `python manage.py dumpdata --natural-foreign --natural-primary -e contenttypes -e auth.permission -e sessions --indent 1 > educaapp.json` con `DATABASE_URL` apuntando a Neon. Es más lento y más frágil que `pg_dump`; sirve como respaldo del respaldo.

## 3. Variables de entorno (todas)

Hay una plantilla en `.env.example`. Qué hace cada una:

| Variable | Obligatoria | Si falta o está mal |
|---|---|---|
| `DATABASE_URL` | Sí | La app **no arranca** (falla a propósito). Formato `postgres://usuario:clave@host:5432/base?sslmode=require` |
| `SECRET_KEY` | Sí (fija) | Si cambia: se pierden las claves de IA guardadas y se cierran todas las sesiones |
| `DEBUG` | Sí = `False` | Con `True` muestra páginas de depuración con datos internos |
| `ALLOWED_HOSTS` | Sí | Error 400 "Bad Request". Dominios separados por coma, **sin** `https://`. `educaapp.vercel.app`, `localhost` y `127.0.0.1` ya están incluidos |
| `CSRF_TRUSTED_ORIGINS` | Sí en un dominio nuevo | El login falla con "CSRF verification failed". Mismos dominios **con** `https://`. Se suma a los de Render y Vercel que ya están en el código |
| `PUBLIC_BASE_URL` | Recomendada | Los enlaces de invitación apuntan a `https://educaapp.vercel.app`. Ponerla en el dominio público nuevo |
| `DJANGO_SUPERUSER_USERNAME`, `_EMAIL`, `_PASSWORD` | Solo el primer arranque | Sin ellas no se crea el administrador y hay que crearlo con `python manage.py createsuperuser` (en hostings con consola) |
| `SELECTORES_INTELIGENTES` | No | `0` apaga el buscador de materias |
| `NEON_API_KEY`, `NEON_PROJECT_ID` | No | Solo la pantalla "Uso de Neon". Si se sale de Neon, ignorarlas |

Requisitos del servidor: Python **3.11** (`.python-version`), unos **512 MB de RAM** como mínimo (la app está medida para eso: 1 worker de gunicorn, 4 hilos, timeout 120 s), y un proxy que termine HTTPS y mande `X-Forwarded-Proto` (lo hacen todos los PaaS; con un VPS propio hay que ponerlo en el proxy, por ejemplo Caddy o nginx). Con 1 solo worker a propósito: la caché de sesiones es en memoria; si algún día se suben workers hay que pasar a Redis.

## 4. Receta: dar de alta la app en otro hosting (objetivo: menos de 30 minutos)

**A. Con un volcado reciente y la `SECRET_KEY` a mano.**

1. **Crear la base nueva** (ver opciones en la sección 6) y copiar su cadena de conexión.
2. **Restaurar el volcado:**
   ```bash
   pg_restore --no-owner --no-acl --clean --if-exists -d "postgres://USUARIO:CLAVE@HOST/BASE?sslmode=require" educaapp_AAAA-MM-DD.dump
   ```
   Si el volcado está vacío o es de otra versión de la app, alcanza con arrancar: `migrate` crea el esquema.
3. **Crear el servicio web** desde el repositorio de GitHub (`martinmromero/EducaApp`, rama `main`).
   - Con **Docker** (Fly.io, Railway, DigitalOcean, VPS): el repo trae `Dockerfile`. Corre migraciones y siembras y arranca gunicorn solo. *No fue probado todavía* (sin Docker en la máquina de desarrollo): si falla el primer build, el mensaje indica el paso.
   - Sin Docker (hostings con buildpacks o "Procfile"): el repo trae `Procfile`. Comando de build: `pip install -r requirements.txt && python manage.py collectstatic --noinput --clear && python manage.py migrate && python manage.py clean_seed_subjects && python manage.py seed_demo_content && python manage.py seed_test_checklist && python manage.py ensure_training_spare_pool && python manage.py createsuperuser --noinput || true`. Comando de inicio: `gunicorn educaapp.wsgi --workers 1 --threads 4 --timeout 120`.
4. **Cargar las variables** de la sección 3 (mínimo: `DATABASE_URL`, `SECRET_KEY`, `DEBUG=False`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`).
5. **Health check:** la ruta es `/health/` (responde sin consultar la base casi siempre).
6. **Apuntar el dominio:** en Vercel, cambiar el destino hacia la URL nueva (ver nota abajo) y ajustar `PUBLIC_BASE_URL`.
7. **Verificar** con la lista de 5 minutos de `docs/lista_despliegue.md` (sección 7) y entrar a Administración → Configuraciones globales de IA: las dos filas (Groq y Gemini) deben seguir **activas y con clave**.

> **Nota sobre Vercel:** la configuración del redirect/proxy de Vercel **no está en este repositorio**, así que esta guía no puede decir en qué archivo se cambia. Dónde mirar: el panel de Vercel → proyecto `educaapp` → Settings → Rewrites/Redirects, o un `vercel.json` del proyecto de Vercel. **Pendiente: anotar acá el destino actual** una vez confirmado.

**B. Sin volcado (la base de Neon ya no existe).** La app arranca igual con una base vacía: `migrate` crea todo, `seed_demo_content` repone los datos de ejemplo y `createsuperuser` crea el administrador. Se pierden usuarios, exámenes y preguntas; hay que volver a cargar las claves de IA en Django Admin.

## 5. Particularidades de Render que no se arrastran

- `render.yaml` es **documentación**: el servicio no se creó como Blueprint y el **Build Command y el Start Command reales están en el panel** de Render (Settings). Si cambia el yaml, hay que reflejarlo a mano en el panel.
- Render gratis **bloquea los puertos de correo saliente** (25, 465, 587) y no tiene consola. En otro hosting con consola se puede correr `python manage.py <comando>` directamente (migraciones, `createsuperuser`, `wipe_production_content`).
- El disco de Render gratis es **efímero**: lo que la app escriba en `media/` se pierde en cada despliegue. Por eso nada crítico se guarda ahí (sección 1).

## 6. Dónde ir: costos (USD por mes salvo que se aclare; leídos el 2026-10-29)

### Hosting de la aplicación (1 instancia siempre encendida, ~512 MB)

| Opción | Costo | Notas |
|---|---|---|
| **Render Starter** (quedarse en Render, pasar a pago) | ~7 (dato de un tercero; la página oficial no mostró precios, **verificar**) | Deja de dormirse y se habilitan los puertos de correo; el disco sigue siendo efímero salvo que se agregue uno persistente (no hace falta). Mismos pasos de hoy |
| **DigitalOcean App Platform** | 5 (512 MiB, 1 instancia) o 10 (1 GiB) | Despliega desde GitHub con interfaz simple. Crédito de 5 USD por 90 días en cuentas nuevas |
| **Fly.io** | 3,69 (shared-cpu-1x, 512 MB), más 2 si se pide IPv4 dedicada (la compartida es gratis) | Sin plan gratuito. Usa el `Dockerfile`. Su Postgres administrado cuesta desde 38: usar otra base |
| **Railway** | Hobby 5 con 5 de uso incluido; 512 MB siempre encendido ≈ 5 de memoria más CPU (estimación propia, ≈ 7 a 10 en total) | Deploy desde GitHub; el plan gratuito (1 USD de crédito, 0,5 GB) no alcanza |
| **VPS (Hetzner CX23: 2 vCPU, 4 GB)** | 5,99 EUR sin IVA | Solo Europa en ese plan; el sitio mostró varios planes "no disponible", **verificar**. Se administra todo a mano (Docker, HTTPS, actualizaciones, copias) |
| Koyeb | Pro 29 más cómputo | **No recomendada**: el sitio anuncia que se une a Mistral AI y la hoja de precios no mostró cómputo de CPU |
| PythonAnywhere | Developer 10 | **No sirve**: no ofrece PostgreSQL y la app lo exige |

### Base de datos

| Opción | Costo | Notas |
|---|---|---|
| **Neon Free** (hoy) | 0 | 100 horas de cómputo y 1 GB por proyecto, se suspende a los 5 min sin uso, restauración de 6 h, **se suspende si se agotan las horas del mes** (en agosto llegó a 80 de 100 horas en 14 días porque el ping de `/health/` mantenía la base despierta; ya se limitó) |
| **Neon Launch** | Por uso: 0,106 por hora de cómputo, 0,35 por GB-mes, sin mínimo. Un proyecto chico anda en ≈ 1 a 3 por mes | Restauración hasta 7 días (0,20 por GB-mes). Es el cambio más barato y sin migrar nada: solo subir de plan |
| Supabase Free | 0 | 500 MB, **se pausa tras 1 semana sin uso**, sin copias de seguridad: no apto para el jurado |
| Supabase Pro | 25 | 8 GB, copias diarias de 7 días, nunca se pausa |
| DigitalOcean Managed Postgres | desde 15,15 (1 GiB) | La "dev database" de 7 no tiene copias y solo la usa su app |
| Render Postgres gratis | 0 | **Descartada**: expira a los 30 días y se borra |
| Postgres dentro de un VPS | Sin costo extra sobre el VPS | Las copias y actualizaciones quedan a cargo propio |

**Recomendación de contingencia:**
- *Si se cae Render:* **DigitalOcean App Platform** (5) o **Fly.io** (3,69) con el `Dockerfile`, y la base sigue en Neon: no se toca nada de datos. Costo total ≈ 5 a 8 por mes.
- *Si se cae o limita Neon:* subir a **Neon Launch** (≈ 1 a 3). Si Neon como empresa deja de existir: volcado con `pg_dump` y restaurar en **DigitalOcean Managed Postgres** (15,15) o **Supabase Pro** (25).
- Mientras dure la evaluación del jurado, evaluar pasar a pago **ambos** (≈ 10 por mes en total): elimina el arranque en frío, el límite de horas y el riesgo de suspensión.

## 7. Fuentes (consultadas el 2026-10-29)

- Render: https://render.com/docs/free (límites del plan gratuito, disco efímero, puertos de correo), https://render.com/docs/disks, https://render.com/docs/compute-plans. Los precios no se vieron en la página de precios (se carga con JavaScript): verificar en https://render.com/pricing.
- Neon: https://neon.com/pricing y https://neon.com/docs/introduction/plans
- Supabase: https://supabase.com/pricing
- Railway: https://railway.com/pricing
- Fly.io: https://docs.fly.io/about/pricing
- Koyeb: https://www.koyeb.com/pricing
- DigitalOcean: https://www.digitalocean.com/pricing/app-platform y https://www.digitalocean.com/pricing/managed-databases
- Hetzner: https://www.hetzner.com/cloud/
- PythonAnywhere: https://www.pythonanywhere.com/pricing/

## 8. Qué falta para que esto sea "cuestión de minutos"

- [ ] Guardar la `SECRET_KEY` actual fuera de Render.
- [ ] Hacer el primer volcado con `pg_dump` y guardarlo fuera de Neon; repetirlo cada semana.
- [ ] Anotar el destino actual del redirect de Vercel (sección 4, nota).
- [ ] Probar el `Dockerfile` una vez (en la máquina propia con Docker, o en Fly.io/DigitalOcean con una cuenta de prueba) antes de necesitarlo.
- [ ] Probar una restauración real del volcado en una base descartable (Neon permite crear otro proyecto gratis).
