# ONBOARDING WIZARD V2 — ROLLBACK: eliminar este archivo y quitarlo de MIDDLEWARE en settings.py
"""
Mantiene "encerrado" en el asistente de configuración a un usuario que todavía
no lo completó ni salió explícitamente: cualquier otra pantalla del sistema
redirige a /comenzar/. Se libera al terminar el asistente de verdad
(onboarding_v2_finish) o al salir a propósito ("Saltar asistente" /
"Salir del asistente", ambos marcan onboarding_completed=True).
"""
from django.shortcuts import redirect

# Prefijos de URL que un usuario con el wizard pendiente puede seguir usando:
# la SPA del asistente y sus endpoints, más las páginas reales a las que el
# propio asistente te manda en los pasos 5 y 6 (generar preguntas, crear examen).
ALLOWED_PREFIXES = (
    '/comenzar/',
    '/onboarding/',
    '/doc-processor/',
    '/create-exam/',
    '/save-exam/',
    '/preview-exam/',
    '/configuracion-ia/',
    '/accounts/',
    '/admin/',
    '/static/',
    '/media/',
    '/health/',
)


class OnboardingGateMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)
        if (
            user is not None
            and user.is_authenticated
            and not user.is_staff
            and not request.path.startswith(ALLOWED_PREFIXES)
        ):
            try:
                completed = user.profile.onboarding_completed
            except Exception:
                completed = True  # sin perfil resoluble, no bloqueamos por las dudas
            if not completed:
                return redirect('material:onboarding_v2_page')
        return self.get_response(request)
