/*
 * Recorrido guiado (driver.js) específico de la pantalla "Crear examen".
 *
 * Se usa en dos modos:
 *  - demo:     disparado automáticamente desde el vistazo de onboarding
 *              (?demo_peek=1, ver create_exam.html), que además autoselecciona
 *              tópicos/preguntas de ejemplo (ahí el formulario es de solo
 *              lectura, pointer-events:none) y termina con un paso que lleva
 *              a "Ver examen".
 *  - consulta: disparado por el usuario desde el menú del botón "?" del
 *              navbar (ver base.html + static/js/tour.js) en cualquier
 *              momento, sobre el formulario real — nunca toca la selección
 *              que el usuario ya haya hecho.
 *
 * Sirve de referencia para agregar el mismo mecanismo a otras pantallas: ver
 * el comentario sobre registerPageTour en static/js/tour.js.
 */
(function () {
  // Los checkboxes de tópicos/preguntas se arman de forma asíncrona (fetch
  // disparado por el prefill de materia) — si el paso del recorrido llega
  // antes de que ese fetch resuelva, el contenedor puede estar vacío
  // todavía. Se reintenta un rato en vez de asumir que ya están. (Solo se
  // usa en modo demo, para la autoselección de ejemplo.)
  function checkFirst(containerId, count, attemptsLeft) {
    attemptsLeft = attemptsLeft === undefined ? 10 : attemptsLeft;
    var boxes = document.querySelectorAll('#' + containerId + ' input[type="checkbox"]');
    if (!boxes.length && attemptsLeft > 0) {
      setTimeout(function () { checkFirst(containerId, count, attemptsLeft - 1); }, 300);
      return;
    }
    var picked = Array.prototype.slice.call(boxes, 0, count);
    picked.forEach(function (cb) {
      if (!cb.checked) {
        cb.checked = true;
        cb.dispatchEvent(new Event('change'));
      }
    });
  }

  // Re-lee directo de los checkboxes tildados (en vez de confiar en que el
  // 'change' de cada uno ya sincronizó el <select> oculto) para no depender
  // del orden exacto de los listeners.
  function checkedValues(containerId, dataAttr) {
    return Array.from(document.querySelectorAll('#' + containerId + ' input[type="checkbox"]:checked'))
      .map(function (cb) { return cb.dataset[dataAttr]; })
      .filter(Boolean);
  }

  function baseSteps(areas) {
    return [
      {
        element: '#plantilla',
        popover: {
          title: 'Plantilla',
          description: 'Se pueden crear plantillas de examen y reutilizarlas acá para no repetir la configuración cada vez.',
          side: 'bottom',
        },
        onHighlightStarted: function () { areas.openArea(1); },
      },
      {
        element: '#id_subject',
        popover: {
          title: 'Materia',
          description: 'Al elegir la materia se habilitan los resultados de aprendizaje (si tiene cargados) y, más abajo, los tópicos con sus preguntas.',
          side: 'bottom',
        },
      },
      {
        element: '#examInstFacCarreraRow',
        popover: {
          title: 'Institución',
          description: 'Al elegir la institución se cargan automáticamente la facultad y las carreras disponibles, si ya están cargadas.',
          side: 'bottom',
        },
      },
      {
        element: '#examArea1Extra',
        popover: {
          title: 'Resto de las opciones',
          description: 'Sede, curso/comisión, turno, profesor, fecha, duración y período académico: todas estas opciones son opcionales.',
          side: 'top',
        },
      },
      {
        element: '#topics_checkbox_container',
        popover: {
          title: 'Tópicos',
          description: 'Acá se eligen los tópicos a evaluar — uno de los datos más importantes del examen.',
          side: 'right',
        },
        onHighlightStarted: function () {
          areas.closeArea(1);
          areas.openArea(3);
        },
      },
      {
        element: '#questions_checkbox_container',
        popover: {
          title: 'Preguntas',
          description: 'Al tildar tópicos, el panel de preguntas se filtra para mostrar solo las de esos tópicos.',
          side: 'top',
        },
      },
      {
        element: '#examSelectionHeaderRow',
        popover: {
          title: 'Selección',
          description: 'Tanto tópicos como preguntas se pueden seleccionar de a uno o todos juntos, con los botones superiores.',
          side: 'top',
        },
      },
      {
        element: '#examArea4',
        popover: {
          title: 'Temas del examen escrito',
          description: 'Se puede crear más de un tema con preguntas distintas para la misma fecha de examen, cada uno con su propio encabezado.',
          side: 'top',
        },
        onHighlightStarted: function () {
          areas.closeArea(3);
          areas.openArea(4);
        },
      },
    ];
  }

  // Variante demo (?demo_peek=1): además de mostrar, autoselecciona
  // tópicos/preguntas de ejemplo y agrega un paso final que lleva a "Ver
  // examen" — ninguna de las dos cosas tiene sentido en modo consulta sobre
  // el formulario real.
  function demoSteps(areas) {
    var steps = baseSteps(areas);

    var topicsStep = steps[4];
    var openTopicsArea = topicsStep.onHighlightStarted;
    topicsStep.onHighlightStarted = function () {
      openTopicsArea();
      // Dispara la selección de ejemplo apenas se muestra este paso (no en
      // el siguiente): así el fetch asincrónico de preguntas filtradas tiene
      // el tiempo real de lectura + clic en "Siguiente" para resolver antes
      // de llegar al paso de Preguntas, en vez de aparecer vacío.
      checkFirst('topics_checkbox_container', 2);
    };
    topicsStep.popover.description = 'Acá se eligen los tópicos a evaluar (en este ejemplo ya se tildan un par, para mostrar el resto del flujo).';

    var questionsStep = steps[5];
    questionsStep.onHighlightStarted = function () { checkFirst('questions_checkbox_container', 3); };
    questionsStep.popover.description = 'Al tildar algunos tópicos (como en este ejemplo), el panel de preguntas se filtra para mostrar solo las de esos tópicos.';

    steps.push({
      element: '#demoPeekContinueBtn',
      popover: {
        title: 'Ver examen',
        description: 'Para ver el resultado, hacer clic en este botón.',
        side: 'top',
        onNextClick: function () {
          document.getElementById('demoPeekContinueBtn')?.click();
        },
      },
    });
    return steps;
  }

  function buildSteps(opts) {
    var areas = window.EducaAppExamAreas || { openArea: function () {}, closeArea: function () {} };
    var steps = (opts && opts.demo) ? demoSteps(areas) : baseSteps(areas);
    // Defensivo: descarta pasos cuyo elemento no esté en el DOM (la pantalla
    // real siempre los tiene, pero evita romper el recorrido si el form se
    // llega a simplificar más adelante).
    return steps.filter(function (s) { return document.querySelector(s.element); });
  }

  function start(opts) {
    if (!window.driver || !window.driver.js) return;
    var steps = buildSteps(opts);
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
      console.error('No se pudo iniciar el recorrido de Crear Examen:', e);
    }
  }

  window.EducaAppCreateExamTour = { start: start, checkedValues: checkedValues };

  // Se registra recién en DOMContentLoaded: este script puede cargar antes
  // que static/js/tour.js (que vive en el bloque de scripts de base.html,
  // después del contenido de la página) según dónde se incluya, así que no
  // se puede asumir que window.EducaAppTour ya exista al correr este IIFE.
  document.addEventListener('DOMContentLoaded', function () {
    if (window.EducaAppTour && window.EducaAppTour.registerPageTour) {
      window.EducaAppTour.registerPageTour('create_exam', {
        label: 'Armar un examen',
        start: function () { start({ demo: false }); },
      });
    }
  });
})();
