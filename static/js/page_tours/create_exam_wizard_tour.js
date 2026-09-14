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
          title: 'Uno o varios temas',
          description: 'Se puede armar más de un tema con preguntas distintas para la misma fecha de examen, cada uno con su propio encabezado.',
          side: 'bottom',
        },
      },
      {
        element: '[data-step-pill="5"]',
        popover: {
          title: 'Docente y fecha',
          description: 'Quién lo toma, cuándo y con qué duración.',
          side: 'bottom',
        },
      },
      {
        element: '[data-step-pill="6"]',
        popover: {
          title: 'Institución y sede',
          description: 'Institución, facultad, carrera, sede, cátedra y turno — todo opcional, se usa para el encabezado impreso.',
          side: 'bottom',
        },
      },
      {
        element: '[data-step-pill="7"]',
        popover: {
          title: 'Tipo y modalidad',
          description: 'Tipo de examen, modalidad individual o grupal, modalidad de resolución, nombre del examen y notas.',
          side: 'bottom',
        },
      },
      {
        element: '[data-step-pill="8"]',
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

  // ── Variante demo (?demo_peek=1) ──────────────────────────────────────
  // A diferencia del recorrido de consulta de arriba (que resalta los
  // ítems SIEMPRE VISIBLES del stepper, sin navegar), acá el objetivo es
  // mostrar el contenido real de cada paso ya precargado por el ejemplo
  // (materia, tópicos/preguntas coloreados, docente, institución) — para
  // eso hace falta ir avanzando el asistente en sincro con el recorrido,
  // ya que cada paso solo es visible cuando está activo (ver
  // wizard_engine.js). El prefill de datos (create_exam_wizard.js) ya
  // corrió antes de llamar a startDemo(), así que acá solo se narra.
  function goToWizardStep(n) {
    var wiz = window.EducaAppExamWizardCtrl;
    if (!wiz) return;
    if (n <= wiz.current()) { wiz.goToStep(n); return; }
    while (wiz.current() < n) { wiz.goNext(); }
  }

  function demoSteps(tourDriver) {
    // onNextClick REEMPLAZA el avance por defecto de driver.js (no lo
    // complementa) — sin el moveNext() explícito acá, el popover se queda
    // pegado en el mismo paso aunque el asistente sí avance de pantalla.
    function next(n) {
      return function () {
        goToWizardStep(n);
        tourDriver.moveNext();
      };
    }
    return [
      {
        element: '.wiz-step[data-step="1"] .wiz-step-card',
        stepNumber: 1,
        popover: {
          title: 'Plantilla',
          description: 'Este ejemplo arranca sin plantilla — se puede elegir una ya guardada para no repetir la configuración la próxima vez.',
          side: 'bottom',
          onNextClick: next(2),
        },
      },
      {
        element: '#id_subject',
        stepNumber: 2,
        popover: {
          title: 'Materia',
          description: 'La materia de este ejemplo ya viene elegida.',
          side: 'bottom',
          onNextClick: next(3),
        },
      },
      {
        element: '#wizTopicsWrap',
        stepNumber: 3,
        popover: {
          title: 'Tópicos y preguntas',
          description: 'Tópicos y preguntas de ejemplo ya tildados — cada tópico con su color propio para distinguir de un vistazo qué pregunta pertenece a cuál (de niveles de Bloom variados, para mostrar esa clasificación).',
          side: 'top',
          onNextClick: next(4),
        },
      },
      {
        element: '.wiz-step[data-step="4"] .wiz-step-card',
        stepNumber: 4,
        popover: {
          title: 'Uno o varios temas',
          description: 'Se puede armar más de un tema con preguntas distintas para la misma fecha de examen, cada uno con su propio encabezado.',
          side: 'bottom',
          onNextClick: next(5),
        },
      },
      {
        element: '#profesor_dropdown',
        stepNumber: 5,
        popover: {
          title: 'Docente y fecha',
          description: 'El docente ya viene precargado con la cuenta actual — el resto de este paso es opcional.',
          side: 'bottom',
          onNextClick: next(6),
        },
      },
      {
        element: '#wizInstitucionBlock',
        stepNumber: 6,
        popover: {
          title: 'Institución y sede',
          description: 'Institución y sede del ejemplo ya cargadas — se usan para el encabezado impreso, todo opcional.',
          side: 'top',
          onNextClick: next(7),
        },
      },
      {
        element: '.wiz-step[data-step="7"] .wiz-step-card',
        stepNumber: 7,
        popover: {
          title: 'Tipo y modalidad',
          description: 'Tipo de examen, modalidad individual o grupal, y cómo se resuelve.',
          side: 'bottom',
          onNextClick: next(8),
        },
      },
      {
        element: '.wiz-step[data-step="8"] .wiz-step-card',
        stepNumber: 8,
        popover: {
          title: 'Rúbricas',
          description: 'Rúbricas opcionales para incluir al imprimir o exportar. Este último paso también muestra un resumen antes de generar la vista previa.',
          side: 'bottom',
        },
      },
      {
        element: '#wizSubmitBtn',
        stepNumber: 8,
        popover: {
          title: 'Ver vista previa',
          description: 'Para ver el resultado, hacer clic en este botón.',
          side: 'top',
          onNextClick: function () {
            document.getElementById('wizSubmitBtn')?.click();
          },
        },
      },
    ];
  }

  function attachStepHandling(steps, tourDriver) {
    steps.forEach(function (step) {
      if (step.stepNumber === undefined) return;
      var ownHandler = step.onHighlightStarted;
      step.onHighlightStarted = function () {
        goToWizardStep(step.stepNumber);
        if (ownHandler) ownHandler();
        var el = document.querySelector(step.element);
        if (el) el.scrollIntoView({ behavior: 'auto', block: 'center', inline: 'center' });
        requestAnimationFrame(function () { tourDriver.refresh(); });
      };
    });
    return steps;
  }

  function startDemo() {
    if (!window.driver || !window.driver.js) return;
    try {
      var tourDriver = window.driver.js.driver({
        showProgress: true,
        allowClose: true,
        overlayOpacity: 0.6,
        animate: false,
        nextBtnText: 'Siguiente',
        prevBtnText: 'Anterior',
        doneBtnText: 'Listo',
        steps: [],
      });
      var steps = attachStepHandling(demoSteps(tourDriver), tourDriver)
        .filter(function (s) { return document.querySelector(s.element); });
      if (!steps.length) return;
      tourDriver.setSteps(steps);
      tourDriver.drive();
    } catch (e) {
      console.error('No se pudo iniciar el recorrido demo del Asistente de examen:', e);
    }
  }

  window.EducaAppCreateExamWizardTour = { start: start, startDemo: startDemo };

  document.addEventListener('DOMContentLoaded', function () {
    if (window.EducaAppTour && window.EducaAppTour.registerPageTour) {
      window.EducaAppTour.registerPageTour('create_exam_wizard', {
        label: 'Asistente de examen',
        start: start,
      });
    }
  });
})();
