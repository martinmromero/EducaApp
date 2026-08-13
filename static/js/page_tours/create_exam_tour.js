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

  // Las 4 "áreas" son acordeones Bootstrap — un solo lugar que decide "de
  // las 4, esta es la única abierta" en vez de que cada paso abra/cierre
  // relativo al paso anterior. Con la versión anterior (relativa),
  // retroceder con "Anterior" a un paso cuya área ya se había cerrado al
  // avanzar la dejaba colapsada — el recorrido resaltaba un elemento
  // invisible y el popover aparecía en cualquier lugar. Al ser siempre
  // absoluta ("mostrar solo el área N"), da igual desde qué paso se venga.
  //
  // El collapse de Bootstrap anima ~350ms — driver.js mide la posición del
  // paso de forma SÍNCRONA apenas termina onHighlightStarted, sin esperar
  // a que esa animación termine, así que se veía un salto visible al lugar
  // viejo/vacío antes de autocorregirse solo un rato después (más notorio
  // cuanto más se tardaba en corregir). Se desactiva la transición del
  // collapse mientras cambia el área (clase .tour-no-transition, ver CSS en
  // create_exam.html) para que el cambio sea instantáneo y no haya nada que
  // corregir después.
  function showOnlyArea(areas, n) {
    var bodies = [1, 2, 3, 4].map(function (i) { return document.getElementById('examArea' + i + 'Body'); });
    bodies.forEach(function (el) { if (el) el.classList.add('tour-no-transition'); });
    [1, 2, 3, 4].forEach(function (i) {
      if (i === n) areas.openArea(i); else areas.closeArea(i);
    });
    // Fuerza a que el navegador aplique el cambio ya (reflow síncrono), y
    // recién en el siguiente frame se reactiva la transición normal — así
    // no afecta la apertura/cierre manual que el usuario haga con el mouse
    // fuera del recorrido.
    bodies.forEach(function (el) { if (el) void el.offsetHeight; });
    requestAnimationFrame(function () {
      bodies.forEach(function (el) { if (el) el.classList.remove('tour-no-transition'); });
    });
  }

  function baseSteps() {
    return [
      {
        element: '#plantilla',
        area: 1,
        popover: {
          title: 'Plantilla',
          description: 'Se pueden crear plantillas de examen y reutilizarlas aquí para no repetir la configuración cada vez.',
          side: 'bottom',
        },
      },
      {
        element: '#id_subject',
        area: 1,
        popover: {
          title: 'Materia',
          description: 'Al elegir la materia se habilitan los resultados de aprendizaje (si tiene cargados) y, más abajo, los tópicos con sus preguntas.',
          side: 'bottom',
        },
      },
      {
        element: '#examInstFacCarreraRow',
        area: 1,
        popover: {
          title: 'Institución',
          description: 'Al elegir la institución se cargan automáticamente la facultad y las carreras disponibles, si ya están cargadas.',
          side: 'bottom',
        },
      },
      {
        element: '#examArea1Extra',
        area: 1,
        popover: {
          title: 'Resto de las opciones',
          description: 'Sede, curso/comisión, turno, profesor, fecha, duración y período académico: todas estas opciones son opcionales.',
          side: 'top',
        },
      },
      {
        element: '#topics_checkbox_container',
        area: 3,
        popover: {
          title: 'Tópicos',
          description: 'Aquí se eligen los tópicos a evaluar — uno de los datos más importantes del examen.',
          side: 'right',
        },
      },
      {
        element: '#questions_checkbox_container',
        area: 3,
        popover: {
          title: 'Preguntas',
          description: 'Al tildar tópicos, el panel de preguntas se filtra para mostrar solo las de esos tópicos.',
          side: 'top',
        },
      },
      {
        element: '#examSelectionHeaderRow',
        area: 3,
        popover: {
          title: 'Selección',
          description: 'Tanto tópicos como preguntas se pueden seleccionar de a uno o todos juntos, con los botones superiores.',
          side: 'top',
        },
      },
      {
        element: '#examArea4',
        area: 4,
        popover: {
          title: 'Temas del examen escrito',
          description: 'Se puede crear más de un tema con preguntas distintas para la misma fecha de examen, cada uno con su propio encabezado.',
          side: 'top',
        },
      },
    ];
  }

  // Variante demo (?demo_peek=1): además de mostrar, autoselecciona
  // tópicos/preguntas de ejemplo y agrega un paso final que lleva a "Ver
  // examen" — ninguna de las dos cosas tiene sentido en modo consulta sobre
  // el formulario real.
  function demoSteps() {
    var steps = baseSteps();

    var topicsStep = steps[4];
    topicsStep.onHighlightStarted = function () {
      // Dispara la selección de ejemplo apenas se muestra este paso (no en
      // el siguiente): así el fetch asincrónico de preguntas filtradas tiene
      // el tiempo real de lectura + clic en "Siguiente" para resolver antes
      // de llegar al paso de Preguntas, en vez de aparecer vacío.
      checkFirst('topics_checkbox_container', 2);
    };
    topicsStep.popover.description = 'Aquí se eligen los tópicos a evaluar (en este ejemplo ya se tildan un par, para mostrar el resto del flujo).';

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

  // Envuelve el onHighlightStarted de cada paso (si lo tiene) para que,
  // antes que nada, se asegure de que su área quede abierta — sin importar
  // desde qué paso se venga ni en qué dirección (ver showOnlyArea).
  //
  // driver.js llama a onHighlightStarted y RECIÉN DESPUÉS hace su propio
  // scrollIntoView() del elemento (si no está ya visible) antes de pintar
  // el resaltado. Cambiar de área cambia cuánto scroll hace falta (p.ej. al
  // cerrarse un área de arriba, el resto de la página sube) — si se deja
  // que driver.js decida y ejecute ese scroll por su cuenta después de que
  // este callback ya terminó, a veces el resaltado se pinta con la página
  // todavía en la posición de scroll vieja, y se ve un salto chico antes de
  // asentarse (más notorio en pasos más abajo en la página, donde hace
  // falta scrollear más). Se hace el scroll acá mismo, ya con el área en su
  // tamaño final — así cuando driver.js revisa si hace falta scrollear, el
  // elemento ya está a la vista y no hace nada.
  function attachAreaHandling(steps, areas, tourDriver) {
    steps.forEach(function (step) {
      if (step.area === undefined) return;
      var stepOwnHandler = step.onHighlightStarted;
      step.onHighlightStarted = function () {
        showOnlyArea(areas, step.area);
        if (stepOwnHandler) stepOwnHandler();
        var el = document.querySelector(step.element);
        if (el) el.scrollIntoView({ behavior: 'auto', block: 'center', inline: 'center' });
        requestAnimationFrame(function () { tourDriver.refresh(); });
      };
    });
    return steps;
  }

  function buildSteps(opts, areas, tourDriver) {
    var steps = (opts && opts.demo) ? demoSteps() : baseSteps();
    attachAreaHandling(steps, areas, tourDriver);
    // Defensivo: descarta pasos cuyo elemento no esté en el DOM (la pantalla
    // real siempre los tiene, pero evita romper el recorrido si el form se
    // llega a simplificar más adelante).
    return steps.filter(function (s) { return document.querySelector(s.element); });
  }

  function start(opts) {
    if (!window.driver || !window.driver.js) return;
    var areas = window.EducaAppExamAreas || { openArea: function () {}, closeArea: function () {} };
    try {
      // Se crea el driver primero (sin steps) para que los propios steps
      // puedan llamar a tourDriver.refresh() desde su onHighlightStarted —
      // ver attachAreaHandling.
      var tourDriver = window.driver.js.driver({
        showProgress: true,
        allowClose: true,
        overlayOpacity: 0.6,
        nextBtnText: 'Siguiente',
        prevBtnText: 'Anterior',
        doneBtnText: 'Listo',
        steps: [],
      });
      var steps = buildSteps(opts, areas, tourDriver);
      if (!steps.length) return;
      tourDriver.setSteps(steps);
      tourDriver.drive();
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
