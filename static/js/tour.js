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

  function expandExamenesSubmenu() {
    const group = document.getElementById('tourMenuExamenes');
    if (group) group.classList.add('active');
  }

  function collapseExamenesSubmenu() {
    const group = document.getElementById('tourMenuExamenes');
    if (group) group.classList.remove('active');
  }

  // Pasos con selector + texto. Si un elemento no está en el DOM de la
  // página actual (ej. "Administración" solo existe para admins) se
  // descarta automáticamente al construir el tour.
  const STEP_DEFS = [
    {
      element: '#tourSidebarBrand',
      popover: {
        title: '¡Bienvenido a EducaApp!',
        description: 'Este recorrido presenta brevemente la ubicación de las funciones principales. Puede repetirse en cualquier momento desde el botón "?" de arriba.',
        side: 'right',
        align: 'start',
      },
    },
    {
      element: '#tourMenuContenidos',
      popover: {
        title: 'Contenidos',
        description: 'Aquí se suben los apuntes, PDFs o materiales de clase para que la IA genere preguntas a partir de ellos. Si ya hay preguntas armadas con su respuesta, no hace falta pasar por aquí: se suben directo en "Preguntas".',
        side: 'right',
      },
    },
    {
      element: '#tourMenuPreguntas',
      popover: {
        title: 'Preguntas',
        description: 'Aquí vive el banco de preguntas: las que se suben ya armadas y las que genera la IA. Al generar con IA se puede aprobar o rechazar cada una, pero se guardan todas — aprobadas y rechazadas — para que la IA tenga memoria de las preferencias la próxima vez.',
        side: 'right',
      },
    },
    {
      element: '#tourMenuExamenes',
      popover: {
        title: 'Exámenes',
        description: 'Aquí se arman exámenes con el banco de preguntas — al elegir, solo aparecen las que fueron aprobadas. También viven aquí las plantillas, las rúbricas y los cuestionarios orales.',
        side: 'right',
      },
    },
    {
      element: '#tourMenuFormatos',
      popover: {
        title: 'Formatos de Impresión',
        description: 'Aquí se define cómo se ve el examen impreso (membrete, colores, tamaño de hoja). Si se trabaja con más de una institución, se pueden guardar varios formatos — uno por cada una — para tener los exámenes listos con el membrete correspondiente.',
        side: 'right',
      },
      onHighlightStarted: expandExamenesSubmenu,
    },
    {
      element: '#tourMenuAcademico',
      popover: {
        title: 'Mi espacio académico',
        description: 'Institución, carrera y materia — se configuran una sola vez, no hace falta volver seguido aquí.',
        side: 'right',
      },
      onHighlightStarted: collapseExamenesSubmenu,
    },
    {
      element: '#tourMenuGrupos',
      popover: {
        title: 'Grupos',
        description: 'Grupos de confianza para compartir preguntas por materia con otros docentes.',
        side: 'right',
      },
    },
    {
      element: '#visualThemeDropdown',
      popover: {
        title: 'Tema visual',
        description: 'Aquí se elige el estilo de colores y tipografía para toda la app.',
        side: 'top',
      },
    },
    {
      element: '#toggleMode',
      popover: {
        title: 'Modo claro / oscuro',
        description: 'Y aquí se alterna entre modo claro y oscuro, según preferencia.',
        side: 'top',
      },
    },
    {
      element: '#tourMisDatos',
      popover: {
        title: 'Mis datos',
        description: 'El perfil y la configuración personal, siempre a un click, aquí abajo.',
        side: 'top',
      },
    },
  ];

  function buildSteps() {
    return STEP_DEFS.filter((step) => document.querySelector(step.element));
  }

  // El navegador no permite mover el cursor real del mouse por seguridad,
  // así que en su lugar destacamos el botón "Siguiente": lo enfocamos (para
  // que Enter/Espacio lo dispare) y le agregamos un pulso visual que llama
  // la atención hacia él en cada paso.
  function focusNextButton(popover) {
    const btn = popover && popover.nextButton;
    if (!btn || btn.style.display === 'none') return;
    btn.classList.add('tour-next-pulse');
    btn.focus({ preventScroll: true });
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
      onPopoverRender: focusNextButton,
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
