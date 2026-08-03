/*
 * Recorrido guiado de EducaApp (driver.js, vendorizado en static/js/vendor/).
 * Recorre el sidebar/navbar reales — no hace falta una página especial.
 *
 * window.EducaAppTour.start() lo dispara el botón "?" del navbar (ver
 * base.html) en cualquier página, y también se auto-dispara una sola vez
 * (localStorage) al entrar por primera vez al asistente de configuración
 * (ver onboarding_v2.html), antes de pedir cualquier dato.
 */
(function () {
  const STORAGE_KEY = 'educaapp_tour_done';

  // Pasos con selector + texto. Si un elemento no está en el DOM de la
  // página actual (ej. "Administración" solo existe para admins) se
  // descarta automáticamente al construir el tour.
  const STEP_DEFS = [
    {
      element: '#tourSidebarBrand',
      popover: {
        title: '¡Bienvenido a EducaApp!',
        description: 'Te mostramos rápido dónde está cada cosa. Podés volver a ver este recorrido cuando quieras con el botón "?" de arriba.',
        side: 'right',
        align: 'start',
      },
    },
    {
      element: '#tourMenuContenidos',
      popover: {
        title: 'Contenidos',
        description: 'Subí tus apuntes, PDFs o materiales de clase — la IA los usa como base para generar preguntas.',
        side: 'right',
      },
    },
    {
      element: '#tourMenuPreguntas',
      popover: {
        title: 'Preguntas',
        description: 'Acá vive tu banco de preguntas: las que subís vos y las que genera la IA a partir de tus contenidos.',
        side: 'right',
      },
    },
    {
      element: '#tourMenuExamenes',
      popover: {
        title: 'Exámenes',
        description: 'Armá exámenes con tu banco de preguntas. Acá también viven las plantillas, las rúbricas, los cuestionarios orales y el formato de impresión.',
        side: 'right',
      },
    },
    {
      element: '#tourMenuAcademico',
      popover: {
        title: 'Mi espacio académico',
        description: 'Institución, carrera y materia — se configuran una sola vez, no hace falta volver seguido acá.',
        side: 'right',
      },
    },
    {
      element: '#tourMenuGrupos',
      popover: {
        title: 'Grupos',
        description: 'Sumate a grupos de confianza con otros docentes para compartir preguntas por materia.',
        side: 'right',
      },
    },
    {
      element: '#visualThemeDropdown',
      popover: {
        title: 'Tema visual',
        description: 'Elegí el estilo de colores y tipografía que más te guste para toda la app.',
        side: 'top',
      },
    },
    {
      element: '#toggleMode',
      popover: {
        title: 'Modo claro / oscuro',
        description: 'Y acá alternás entre modo claro y oscuro cuando quieras.',
        side: 'top',
      },
    },
    {
      element: '#tourMisDatos',
      popover: {
        title: 'Mis datos',
        description: 'Tu perfil y configuración personal siempre a un click, acá abajo.',
        side: 'top',
      },
    },
  ];

  function buildSteps() {
    return STEP_DEFS.filter((step) => document.querySelector(step.element));
  }

  function start() {
    if (!window.driver || !window.driver.js) return;
    const steps = buildSteps();
    if (!steps.length) return;
    const tourDriver = window.driver.js.driver({
      showProgress: true,
      allowClose: true,
      overlayOpacity: 0.6,
      nextBtnText: 'Siguiente',
      prevBtnText: 'Anterior',
      doneBtnText: 'Listo',
      steps: steps,
      onDestroyed: () => {
        try { localStorage.setItem(STORAGE_KEY, '1'); } catch (e) {}
      },
    });
    tourDriver.drive();
  }

  function startIfFirstVisit() {
    let done = false;
    try { done = localStorage.getItem(STORAGE_KEY) === '1'; } catch (e) {}
    if (!done) start();
  }

  window.EducaAppTour = { start, startIfFirstVisit };
})();
