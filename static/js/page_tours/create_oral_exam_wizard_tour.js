/*
 * Recorrido guiado (driver.js) específico del asistente "Cuestionario oral"
 * (oral_exams/create_oral_exam_wizard.html) — alternativa paso a paso a la
 * pantalla completa de siempre (ver
 * static/js/page_tours/oral_exam_create_tour.js).
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
          title: 'Asistente de cuestionario oral',
          description: 'Se completa un paso a la vez, cada uno en su propia pantalla. Se puede volver atrás en cualquier momento y nada se guarda hasta el último paso.',
          side: 'bottom',
        },
      },
      {
        element: '[data-step-pill="1"]',
        popover: {
          title: 'Materia y tópicos',
          description: 'Al elegir la materia se cargan sus tópicos, para tildar los que se van a evaluar.',
          side: 'bottom',
        },
      },
      {
        element: '[data-step-pill="2"]',
        popover: {
          title: 'Alumnos y grupos',
          description: 'Total de alumnos, cantidad de grupos y preguntas por alumno — cada grupo rinde en simultáneo, con preguntas de sub-temas distintos para que no se repitan entre sí.',
          side: 'bottom',
        },
      },
      {
        element: '[data-step-pill="3"]',
        popover: {
          title: 'Nombre y revisión',
          description: 'El nombre sirve para identificarlo después en la lista de Cuestionarios Orales. Este último paso también muestra un resumen antes de crearlo.',
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
      console.error('No se pudo iniciar el recorrido del Asistente de cuestionario oral:', e);
    }
  }

  window.EducaAppOralExamWizardTour = { start: start };

  document.addEventListener('DOMContentLoaded', function () {
    if (window.EducaAppTour && window.EducaAppTour.registerPageTour) {
      window.EducaAppTour.registerPageTour('create_oral_exam_wizard', {
        label: 'Asistente de cuestionario oral',
        start: start,
      });
    }
  });
})();
