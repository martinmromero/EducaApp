/*
 * Recorrido guiado (driver.js) para las pantallas de examen individual:
 * "Ver examen" (preview_exam.html, antes de guardar) y "Ver examen"
 * guardado (ver_examen.html). Ambas extienden base_exam_preview.html, que
 * es una página standalone (sin sidebar/navbar/botón "?" de base.html) —
 * por eso el botón "?" que dispara este recorrido vive directo en
 * base_exam_preview.html, no en el mecanismo de registerPageTour de
 * static/js/tour.js (pensado para páginas que sí extienden base.html).
 *
 * Se usa en dos modos:
 *  - demo:     disparado automáticamente en el vistazo de onboarding
 *              (preview_exam.html con is_demo=True). Termina con un paso
 *              que fuerza el clic en "Guardar Examen" (simulado, no
 *              persiste nada real).
 *  - consulta: disparado por el botón "?" en cualquier otro momento, sobre
 *              un examen real — el paso de "Guardar examen" (si existe en
 *              la pantalla) NUNCA dispara el clic automático, para no
 *              guardar el examen por accidente solo por completar el
 *              recorrido.
 *
 * Las dos pantallas comparten #examHeaderBlock/#examQuestionsSection/
 * #bloomSidebar; el resto de los controles difiere (preview_exam.html usa
 * #examSaveBtn y el panel Acciones (#examActionsBtn), ver_examen.html usa además
 * #viewShowAnswers y las rúbricas dentro del mismo panel) — los pasos de abajo cubren ambas
 * variantes y el filtro por document.querySelector descarta los que no
 * apliquen a la pantalla actual.
 */
(function () {
  function baseSteps() {
    return [
      {
        element: '#examHeaderBlock',
        popover: {
          title: 'Encabezado del examen',
          description: 'Institución, carrera, docente, materia y tipo de examen: se configuran en "Crear examen" o se completan automáticamente si se usa una plantilla.',
          side: 'bottom',
        },
      },
      {
        element: '#examQuestionsSection',
        popover: {
          title: 'Preguntas del examen',
          description: 'Estas son las preguntas elegidas para este examen, tomadas del banco de preguntas aprobadas.',
          side: 'top',
        },
      },
      {
        element: '#examActionsBtn',
        popover: {
          title: 'Acciones',
          description: document.getElementById('accExport') && document.getElementById('examRubricsBtn')
            ? 'Este botón abre el panel con todo lo demás: mostrar las respuestas y las rúbricas en pantalla, agregar o gestionar rúbricas, imprimir o descargar el examen en PDF o DOCX (con o sin respuestas y rúbricas) y ver la distribución de niveles de Bloom en forma de pirámide.'
            : 'Este botón abre el panel con todo lo demás: mostrar las respuestas en pantalla, imprimir el examen (con o sin respuestas), volver a editarlo y ver la distribución de niveles de Bloom en forma de pirámide.',
          side: 'top',
        },
      },
    ];
  }

  // Variante demo (onboarding): agrega el paso de "Guardar examen" con
  // clic automático al terminar — no tiene sentido en modo consulta sobre
  // un examen real (ver comentario del archivo).
  function demoSteps() {
    var steps = baseSteps();
    steps.push({
      element: '#examSaveBtn',
      popover: {
        title: 'Guardar examen',
        description: 'Guardar para continuar el ejemplo.',
        side: 'top',
        onNextClick: function () {
          document.getElementById('examSaveBtn')?.click();
        },
      },
    });
    return steps;
  }

  // Variante consulta: si la pantalla tiene botón de guardar (preview_exam
  // real, antes de guardar), se muestra como paso informativo nada más —
  // "Listo" jamás dispara un guardado real por sí solo.
  function consultaSteps() {
    var steps = baseSteps();
    steps.push({
      element: '#examSaveBtn',
      popover: {
        title: 'Guardar examen',
        description: 'Guardar este examen en "Mis exámenes". Al guardar, el aviso ofrece descargarlo en PDF o DOCX en el momento. Se puede seguir editando después.',
        side: 'top',
      },
    });
    return steps;
  }

  function buildSteps(opts) {
    var steps = (opts && opts.demo) ? demoSteps() : consultaSteps();
    return steps.filter(function (s) { return document.querySelector(s.element); });
  }

  function start(opts) {
    if (!window.driver || !window.driver.js) return;
    var steps = buildSteps(opts);
    if (!steps.length) return;
    try {
      var tourDriver = window.driver.js.driver({
        showProgress: true,
        progressText: '{{current}} de {{total}}',
        allowClose: true,
        overlayOpacity: 0.6,
        nextBtnText: 'Siguiente',
        prevBtnText: 'Anterior',
        doneBtnText: 'Listo',
        steps: steps,
      });
      // En modo demo, base_exam_preview.html (simulateSaveExam) destruye
      // esta instancia antes de mostrar el modal de guardado simulado, para
      // que no queden dos overlays oscuros superpuestos.
      if (opts && opts.demo) window._demoExamTourDriver = tourDriver;
      tourDriver.drive();
    } catch (e) {
      console.error('No se pudo iniciar el recorrido de Ver examen:', e);
    }
  }

  window.EducaAppPreviewExamTour = { start: start };

  document.addEventListener('DOMContentLoaded', function () {
    if (window.EducaAppTour && window.EducaAppTour.registerPageTour) {
      window.EducaAppTour.registerPageTour('preview_exam', {
        label: 'Ver un examen',
        start: function () { start({ demo: false }); },
      });
    }
  });
})();
