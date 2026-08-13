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

  function expandAcademicoSubmenu() {
    const group = document.getElementById('tourMenuAcademico');
    if (group) group.classList.add('active');
  }

  function expandContenidosSubmenu() {
    const group = document.getElementById('tourMenuContenidos');
    if (group) group.classList.add('active');
  }

  function collapseContenidosSubmenu() {
    const group = document.getElementById('tourMenuContenidos');
    if (group) group.classList.remove('active');
  }

  function expandPreguntasSubmenu() {
    const group = document.getElementById('tourMenuPreguntas');
    if (group) group.classList.add('active');
  }

  function collapsePreguntasSubmenu() {
    const group = document.getElementById('tourMenuPreguntas');
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
        description: 'Este recorrido presenta brevemente la ubicación de las funciones principales. Puede repetirse en cualquier momento desde el botón "?" disponible.',
        side: 'right',
        align: 'start',
      },
    },
    {
      element: '#tourMenuContenidos',
      popover: {
        title: 'Contenidos',
        description: 'Aquí se suben los apuntes, PDFs o materiales de clase para que la IA genere preguntas a partir de ellos.',
        side: 'right',
      },
      onHighlightStarted: expandContenidosSubmenu,
    },
    {
      element: '#tourMenuPreguntas',
      popover: {
        title: 'Preguntas',
        description: 'Aquí vive el banco de preguntas: si ya hay preguntas armadas con su respuesta, se pueden subir directo tanto individualmente como en lotes. Las que genera la IA se pueden aprobar o rechazar cada una, pero se guardan todas, para que la IA tenga memoria de las preferencias la próxima vez.',
        side: 'right',
      },
      onHighlightStarted: function () {
        collapseContenidosSubmenu();
        expandPreguntasSubmenu();
      },
    },
    {
      element: '#tourMenuExamenes',
      popover: {
        title: 'Exámenes',
        description: 'Aquí se arman exámenes con el banco de preguntas — al elegir, solo aparecen las que fueron aprobadas. También viven aquí las plantillas, las rúbricas y los cuestionarios orales.',
        side: 'right',
      },
      onHighlightStarted: collapsePreguntasSubmenu,
    },
    {
      element: '#tourMenuPlantillas',
      popover: {
        title: 'Plantillas',
        description: 'Aquí se pueden crear plantillas de examen reutilizables, para no repetir la misma configuración cada vez.',
        side: 'right',
      },
      onHighlightStarted: expandExamenesSubmenu,
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
        description: 'Institución, carrera y materia — se configuran ocasionalmente.',
        side: 'right',
      },
      onHighlightStarted: function () {
        collapseExamenesSubmenu();
        expandAcademicoSubmenu();
      },
    },
    {
      element: '#tourMenuGrupos',
      popover: {
        title: 'Grupos',
        description: 'Grupos de confianza para compartir preguntas por materia con otros docentes.',
        side: 'right',
      },
      onHighlightStarted: function () {
        const group = document.getElementById('tourMenuAcademico');
        if (group) group.classList.remove('active');
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

  // En mobile el sidebar arranca oculto fuera de pantalla (clase
  // "mobile-open" lo trae a la vista, ver base.html). driver.js igual
  // encuentra los elementos con document.querySelector (siguen en el DOM),
  // así que el tour "corría" en silencio contra un sidebar invisible —
  // se veía como si no pasara nada. Se abre el sidebar antes de arrancar
  // si hace falta, y se cierra de nuevo al terminar.
  function isMobileViewport() {
    return window.innerWidth <= 768;
  }

  function ensureSidebarVisible() {
    if (!isMobileViewport()) return false;
    const sidebar = document.getElementById('sidebar');
    if (!sidebar || sidebar.classList.contains('mobile-open')) return false;
    if (typeof window.toggleSidebar === 'function') {
      window.toggleSidebar();
      return true;
    }
    return false;
  }

  function restoreSidebar(openedByTour) {
    if (openedByTour && typeof window.closeSidebarMobile === 'function') {
      window.closeSidebarMobile();
    }
  }

  function start() {
    if (!window.driver || !window.driver.js) return;
    const steps = buildSteps();
    if (!steps.length) return;
    const openedSidebar = ensureSidebarVisible();
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
        restoreSidebar(openedSidebar);
      },
    });
    tourDriver.drive();
  }

  function startIfFirstVisit() {
    let done = false;
    try { done = localStorage.getItem(STORAGE_KEY) === '1'; } catch (e) {}
    if (!done) start();
  }

  // ── Recorridos específicos por pantalla ──────────────────────────────────
  // Además del recorrido general de arriba, una pantalla puede registrar su
  // propio recorrido corto (ver static/js/page_tours/create_exam_tour.js
  // para el primer caso, "Crear examen"). El botón "?" del navbar (ver
  // base.html) ofrece elegir entre ambos cuando hay uno registrado para la
  // pantalla actual; si no hay ninguno, arranca directo el recorrido
  // general, igual que antes.
  //
  // Convención para agregar un recorrido a una pantalla nueva:
  //   1. En la plantilla, setear <body data-tour-page="mi_pantalla">
  //      (ver {% block body_extra_attrs %} en base.html).
  //   2. Cargar un script propio (ej. static/js/page_tours/mi_pantalla_tour.js)
  //      que llame a window.EducaAppTour.registerPageTour('mi_pantalla', {
  //        label: 'Texto para el botón del menú',
  //        start: function () { ... arma los steps y llama a .drive() ... },
  //      });
  const pageTours = {};

  function registerPageTour(key, def) {
    pageTours[key] = def;
  }

  function getCurrentPageTour() {
    const key = document.body && document.body.dataset.tourPage;
    return key ? (pageTours[key] || null) : null;
  }

  window.EducaAppTour = { start, startIfFirstVisit, registerPageTour, getCurrentPageTour };
})();
