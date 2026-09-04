/*
 * Recorrido guiado (driver.js) específico del asistente "Nueva institución"
 * (institutions_v2/create_wizard.html) — alternativa paso a paso a la
 * pantalla completa de siempre (ver
 * static/js/page_tours/create_institution_v2_tour.js).
 *
 * Igual que en el asistente de examen (ver
 * static/js/page_tours/create_exam_wizard_tour.js para el detalle), este
 * recorrido apunta a los ítems del stepper (#wizStepper [data-step-pill]),
 * que siempre están en el DOM y visibles sin importar en qué paso esté el
 * usuario, en vez de forzar la navegación entre pasos.
 *
 * Disparado por el usuario desde el menú del botón "?" del navbar (ver
 * base.html + static/js/tour.js) en cualquier momento.
 */
(function () {
  function buildSteps() {
    var steps = [
      {
        element: '#wizStepper',
        popover: {
          title: 'Asistente de institución',
          description: 'Se completa un paso a la vez, cada uno en su propia pantalla. Se puede volver atrás en cualquier momento y nada se guarda hasta el último paso.',
          side: 'bottom',
        },
      },
      {
        element: '[data-step-pill="1"]',
        popover: {
          title: 'Institución',
          description: 'Nombre, sigla y logo — solo el nombre es obligatorio.',
          side: 'bottom',
        },
      },
      {
        element: '[data-step-pill="2"]',
        popover: {
          title: 'Sedes',
          description: 'Opcional — se puede dejar en blanco y agregar sedes después.',
          side: 'bottom',
        },
      },
      {
        element: '[data-step-pill="3"]',
        popover: {
          title: 'Facultades',
          description: 'Opcional — se puede dejar en blanco y agregar facultades después.',
          side: 'bottom',
        },
      },
      {
        element: '[data-step-pill="4"]',
        popover: {
          title: 'Revisión',
          description: 'Último paso: se muestra un resumen de todo lo cargado antes de crear la institución.',
          side: 'bottom',
        },
      },
      {
        element: '.wiz-nav a',
        popover: {
          title: 'Empezar de nuevo',
          description: 'Este enlace reinicia el asistente completo, por si conviene partir de cero.',
          side: 'top',
        },
      },
    ];
    return steps.filter(function (s) { return document.querySelector(s.element); });
  }

  function start() {
    if (!window.driver || !window.driver.js) return;
    var steps = buildSteps();
    if (!steps.length) return;
    try {
      window.driver.js.driver({
        showProgress: true,
        allowClose: true,
        overlayOpacity: 0.6,
        nextBtnText: 'Siguiente',
        prevBtnText: 'Anterior',
        doneBtnText: 'Listo',
        steps: steps,
      }).drive();
    } catch (e) {
      console.error('No se pudo iniciar el recorrido del Asistente de institución:', e);
    }
  }

  window.EducaAppInstitutionWizardTour = { start: start };

  document.addEventListener('DOMContentLoaded', function () {
    if (window.EducaAppTour && window.EducaAppTour.registerPageTour) {
      window.EducaAppTour.registerPageTour('create_institution_v2_wizard', {
        label: 'Asistente de institución',
        start: start,
      });
    }
  });
})();
