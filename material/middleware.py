# ONBOARDING WIZARD V2 — ROLLBACK: eliminar este archivo y quitarlo de MIDDLEWARE en settings.py
"""
Invita a un usuario que todavía no completó (ni salió de) el asistente de
configuración a terminarlo, redirigiéndolo a /comenzar/ solo cuando entra a
Inicio (la home, '/') — el resto del sistema queda con funcionalidad normal
sin bloquear nada.

Antes este middleware "encerraba" al usuario: cualquier página que no
estuviera en una lista de excepciones lo mandaba de vuelta al asistente,
reiniciado desde el paso 1 (mala experiencia — se sentía como perder el
progreso, aunque los datos ya guardados de institución/materia/contenido no
se perdían realmente). Ahora solo se lo invita una vez, al entrar a Inicio;
si navega a cualquier otra pantalla (sidebar, links, etc.) tiene el sistema
completo disponible, y puede volver a terminar el asistente cuando quiera
desde ahí.

Se libera del todo (onboarding_completed=True) al terminar el asistente de
verdad (onboarding_v2_finish) o al salir a propósito ("Saltar asistente" /
"Salir del asistente").
"""
from django.shortcuts import redirect

# Único punto de entrada que dispara la invitación al asistente.
INDEX_PATH = '/'


class OnboardingGateMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)
        if (
            user is not None
            and user.is_authenticated
            and not user.is_staff
            and request.path == INDEX_PATH
        ):
            try:
                completed = user.profile.onboarding_completed
            except Exception:
                completed = True  # sin perfil resoluble, no bloqueamos por las dudas
            if not completed:
                return redirect('material:onboarding_v2_page')
        return self.get_response(request)
