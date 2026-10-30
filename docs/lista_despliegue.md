# Lista de despliegue para el jurado

Render no tiene consola: todo lo que se configura se hace en el panel (Environment y Build Command). El archivo `render.yaml` solo documenta; **el panel manda**. Revisar cada punto en el panel antes de dar acceso.

## 1. Variables de entorno (Render → Environment)

| Variable | Valor | Por qué |
|---|---|---|
| `DEBUG` | `False` | Con `True` se muestran páginas de depuración con datos internos. Desde el 2026-10-26 el valor por defecto también es `False`. |
| `SECRET_KEY` | Una clave fija (no `generateValue` en cada deploy) | De ella se deriva el cifrado de las claves de IA que guarda cada cuenta: si cambia, esas claves dejan de poder leerse. |
| `ALLOWED_HOSTS` | `educaapp.onrender.com` | Ya se suman `educaapp.vercel.app`, `localhost` y `127.0.0.1`. |
| `DATABASE_URL` | La de Neon | |
| `PUBLIC_BASE_URL` | `https://educaapp.vercel.app` | Es el dominio que usan los enlaces de invitación. |
| `SELECTORES_INTELIGENTES` | `1` (o `0` para apagar el buscador de materias) | Se cambia sin tocar código; hay que reiniciar el servicio. |
| `NEON_API_KEY`, `NEON_PROJECT_ID` | Opcionales | Solo para la pantalla de uso de Neon (admin). |

## 2. Build Command (Render → Settings)

Debe correr, en este orden: instalar dependencias, `collectstatic --noinput --clear`, `migrate`, `clean_seed_subjects`, `seed_demo_content`, `seed_test_checklist`, `ensure_training_spare_pool` y `createsuperuser --noinput || true`. Esto está en `render.yaml`; hay que comprobar que el panel tenga lo mismo (ya pasó que no).

**`migrate` es obligatorio:** las migraciones 0109 y 0110 (turno de las plantillas) tienen que aplicarse o fallan las plantillas.

Start Command: `gunicorn educaapp.wsgi --workers 1 --threads 4 --timeout 120`. Un solo worker, porque las sesiones usan caché en memoria.

## 3. IA pública

- Django Admin → Configuraciones globales de IA: las dos filas (Groq y Gemini) **activas y con clave**. Gemini es la única que ve imágenes y el respaldo cuando Groq agota su cupo.
- Herramientas → Prompt de generación IA: comprobar que está el texto por defecto (botón "Restaurar default").
- La IA pública es un cupo compartido: si varias personas generan a la vez puede agotarse. El mensaje que ven explica qué hacer.

## 4. Cuentas para el jurado

- Cuentas **docentes planas** (sin rol admin). Alta por invitación (Invitaciones → generar enlace) o desde Usuarios → Nuevo.
- En el primer ingreso cada cuenta elige su pregunta de seguridad y pasa por "Comenzar".
- Lo que no pueden hacer solas (alta directa en el catálogo, administrar usuarios, herramientas) les muestra un aviso "solo para administradores". Para el catálogo tienen el botón "Agregar", que genera una solicitud que llega a la bandeja del admin.
- Revisar la bandeja de solicitudes (Administración → Solicitudes de catálogo) mientras dure la evaluación.

## 5. Datos

- Decidir antes si se limpia la base (`wipe_production_content`, conserva superusuario y configuración de IA) o se deja el contenido actual. El contenido de ejemplo (`seed_demo_content`) se sincroniza solo en cada build.
- Área de Pruebas: cada cuenta puede entrar a una copia con exámenes de ejemplo sin tocar lo suyo.

## 6. Disponibilidad

- UptimeRobot apuntando a `/health/` cada 5 minutos evita que Render duerma el servicio. El primer PDF después de un rato de inactividad tarda más (arranque en frío): conviene abrir la app unos minutos antes de una demostración.

## 7. Verificación después de cada despliegue (5 minutos)

1. Entrar con una cuenta docente y abrir Inicio.
2. Asistente paso a paso hasta guardar un examen y descargarlo en PDF.
3. Generar con IA con un PDF corto (el visor de páginas tiene que cargar).
4. Nuevo grupo con el asistente y aceptar la invitación con otra cuenta.
5. Abrir `/users/` con la cuenta docente: debe volver al inicio con el aviso.
6. Mirar los logs de Render por errores 500.

## 8. Si Render o Neon fallan

Ver `docs/migrar_hosting.md`: variables, receta de alta en otro hosting, copias de la base y costos de alternativas.

## 9. Cómo volver atrás

- Apagar el buscador de materias: `SELECTORES_INTELIGENTES=0` y reiniciar.
- Volver a una versión anterior: `git revert <commit>` y push; cada cambio grande quedó en su propio commit.
- Una página de error 500 amable ya existe (`500.html`); si aparece, el detalle está en los logs de Render.
