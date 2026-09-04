/*
 * Recorrido guiado (driver.js) específico del asistente "Nuevo examen"
 * (exams/create_exam_wizard.html) — alternativa paso a paso a la pantalla
 * completa de siempre (ver static/js/page_tours/create_exam_tour.js).
 *
 * A diferencia del recorrido de la pantalla completa, este no fuerza la
 * navegación entre pasos del asistente (wizard_engine.js solo permite
 * avanzar a un paso ya alcanzado — goToStep(n) revisa maxStepReached).
 * En cambio, recorre directamente los ítems del stepper (#wizStepper
 * [data-step-pill]), que siempre están en el DOM y visibles sin importar
 * en qué paso esté el usuario (ver wizard_common.css: .wiz-step-pill nunca
 * se oculta, solo cambia de estilo con .is-active/.is-done).
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
          title: 'Asistente de examen',
          description: 'Se completa un paso a la vez, cada uno en su propia pantalla. Se puede volver atrás en cualquier momento y nada se guarda hasta el último paso.',
          side: 'bottom',
        },
      },
      {
        element: '[data-step-pill="1"]',
        popover: {
          title: 'Plantilla',
          description: 'Elegir una plantilla ya guardada completa institución, rúbricas y más de una sola vez, y todo se puede seguir editando en los pasos siguientes. También se puede arrancar en blanco.',
          side: 'bottom',
        },
      },
      {
        element: '[data-step-pill="2"]',
        popover: {
          title: 'Materia',
          description: 'Al elegir la materia se habilitan los resultados de aprendizaje (si tiene cargados) y los tópicos del paso siguiente.',
          side: 'bottom',
        },
      },
      {
        element: '[data-step-pill="3"]',
        popover: {
          title: 'Tópicos y preguntas',
          description: 'Se eligen los tópicos a evaluar y, debajo, las preguntas correspondientes — cada tópico tiene su propio color para distinguirlas de un vistazo.',
          side: 'bottom',
        },
      },
      {
        element: '[data-step-pill="4"]',
        popover: {
          title: 'Cuándo y detalles',
          description: 'Profesor, fecha y duración, más institución/sede/curso y tipo de examen (todo opcional, para el encabezado impreso).',
          side: 'bottom',
        },
      },
      {
        element: '[data-step-pill="5"]',
        popover: {
          title: 'Uno o varios temas',
          description: 'Se puede armar más de un tema con preguntas distintas para la misma fecha de examen, cada uno con su propio encabezado.',
          side: 'bottom',
        },
      },
      {
        element: '[data-step-pill="6"]',
        popover: {
          title: 'Rúbricas',
          description: 'Rúbricas opcionales para incluir al imprimir o exportar. Este último paso también muestra un resumen antes de generar la vista previa.',
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
      console.error('No se pudo iniciar el recorrido del Asistente de examen:', e);
    }
  }

  window.EducaAppCreateExamWizardTour = { start: start };

  document.addEventListener('DOMContentLoaded', function () {
    if (window.EducaAppTour && window.EducaAppTour.registerPageTour) {
      window.EducaAppTour.registerPageTour('create_exam_wizard', {
        label: 'Asistente de examen',
        start: start,
      });
    }
  });
})();
