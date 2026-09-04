/*
 * Recorrido guiado (driver.js) específico del asistente "Plantilla de
 * examen" (exams/create_exam_template_wizard.html) — alternativa paso a
 * paso a la pantalla completa de siempre (ver
 * static/js/page_tours/exam_template_tour.js).
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
          title: 'Asistente de plantilla',
          description: 'Se completa un paso a la vez, cada uno en su propia pantalla. Se puede volver atrás en cualquier momento y nada se guarda hasta el último paso.',
          side: 'bottom',
        },
      },
      {
        element: '[data-step-pill="1"]',
        popover: {
          title: 'Institución',
          description: 'Institución, facultad y carrera van en el encabezado impreso y son obligatorias. La sede es opcional.',
          side: 'bottom',
        },
      },
      {
        element: '[data-step-pill="2"]',
        popover: {
          title: 'Materia y profesor',
          description: 'Materia obligatoria; profesor, cátedra y formato de impresión son opcionales.',
          side: 'bottom',
        },
      },
      {
        element: '[data-step-pill="3"]',
        popover: {
          title: 'Resultados y rúbricas',
          description: 'Resultados de aprendizaje de la materia y rúbricas ya creadas — ambos opcionales, se pueden agregar después editando la plantilla.',
          side: 'bottom',
        },
      },
      {
        element: '[data-step-pill="4"]',
        popover: {
          title: 'Nombre y revisión',
          description: 'Si se deja vacío, se muestra "Materia - Tipo (Año)" en la lista de plantillas. Este último paso también muestra un resumen antes de crearla.',
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
      console.error('No se pudo iniciar el recorrido del Asistente de plantilla:', e);
    }
  }

  window.EducaAppExamTemplateWizardTour = { start: start };

  document.addEventListener('DOMContentLoaded', function () {
    if (window.EducaAppTour && window.EducaAppTour.registerPageTour) {
      window.EducaAppTour.registerPageTour('create_exam_template_wizard', {
        label: 'Asistente de plantilla',
        start: start,
      });
    }
  });
})();
