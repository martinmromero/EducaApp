/*
 * Recorrido guiado (driver.js) de la pantalla "Mis Exámenes"
 * (exams/mis_examenes_new.html) — puerta de entrada a "Nuevo Examen" (ver
 * static/js/page_tours/create_exam_tour.js para el tour de esa otra
 * pantalla). Lista tanto exámenes individuales como lotes (varios temas
 * generados juntos).
 *
 * Disparado por el usuario desde el menú del botón "?" del navbar (ver
 * base.html + static/js/tour.js) en cualquier momento.
 */
(function () {
  function buildSteps() {
    var steps = [
      {
        element: '#examNewBtn',
        popover: {
          title: 'Nuevo examen',
          description: 'Abre el formulario de armado: institución, materia, tópicos y preguntas.',
          side: 'bottom',
        },
      },
      {
        element: '#examWizardBtn',
        popover: {
          title: 'Asistente de Examen',
          description: 'La misma información, pero pedida un paso a la vez — útil para armar el primer examen o cuando conviene ir de a poco.',
          side: 'bottom',
        },
      },
      {
        element: '#examFavoritosBtn',
        popover: {
          title: 'Favoritos',
          description: 'Filtra la lista para mostrar solo los exámenes o lotes marcados con la estrella.',
          side: 'bottom',
        },
      },
      {
        element: '#selectAll',
        popover: {
          title: 'Selección múltiple',
          description: 'Tildando el casillero de uno o más exámenes o lotes aparece una barra con la cantidad seleccionada y el botón para borrarlos juntos.',
          side: 'bottom',
        },
      },
      {
        element: '#examColTipo',
        popover: {
          title: 'Individual vs. Lote',
          description: '"Individual" es un examen suelto. "Lote" agrupa varios temas (versiones distintas de preguntas) generados juntos para la misma fecha — por ejemplo, para dificultar la copia entre estudiantes.',
          side: 'bottom',
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
      console.error('No se pudo iniciar el recorrido de Mis Exámenes:', e);
    }
  }

  window.EducaAppMisExamenesTour = { start: start };

  document.addEventListener('DOMContentLoaded', function () {
    if (window.EducaAppTour && window.EducaAppTour.registerPageTour) {
      window.EducaAppTour.registerPageTour('mis_examenes', {
        label: 'Mis Exámenes',
        start: start,
      });
    }
  });
})();
