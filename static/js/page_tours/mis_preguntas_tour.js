/*
 * Recorrido guiado (driver.js) de la pantalla "Mis Preguntas"
 * (questions/lista_preguntas.html) — puerta de entrada a "Nueva Pregunta" y
 * banco de preguntas propias + generadas por IA + compartidas por grupos.
 *
 * Disparado por el usuario desde el menú del botón "?" del navbar (ver
 * base.html + static/js/tour.js) en cualquier momento.
 */
(function () {
  function buildSteps() {
    var steps = [
      {
        element: '#questionNewBtn',
        popover: {
          title: 'Nueva pregunta',
          description: 'Carga una pregunta ya armada (con su respuesta) directo al banco, sin pasar por la IA.',
          side: 'bottom',
        },
      },
      {
        element: '#questionStatsRow',
        popover: {
          title: 'Contadores',
          description: 'Resumen rápido: preguntas totales, materias y tópicos con preguntas cargadas, y cuántas fueron generadas por IA.',
          side: 'bottom',
        },
      },
      {
        element: '#select-all',
        popover: {
          title: 'Selección múltiple',
          description: 'Tildando el casillero de una o más preguntas aparece una barra con la cantidad seleccionada, para exportarlas (CSV o TXT) o eliminarlas juntas.',
          side: 'bottom',
        },
      },
      {
        element: '#questionColEstadoIA',
        popover: {
          title: 'Estado IA',
          description: 'Las preguntas generadas por IA quedan "Sin revisar" hasta aprobarlas o rechazarlas — se guardan todas de todos modos, para que la IA aprenda las preferencias la próxima vez.',
          side: 'bottom',
        },
      },
      {
        element: '#questionColOrigen',
        popover: {
          title: 'Origen',
          description: '"Propia" son las preguntas cargadas por esta cuenta. Las demás llegaron compartidas por otro docente a través de un grupo de confianza.',
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
      console.error('No se pudo iniciar el recorrido de Mis Preguntas:', e);
    }
  }

  window.EducaAppMisPreguntasTour = { start: start };

  document.addEventListener('DOMContentLoaded', function () {
    if (window.EducaAppTour && window.EducaAppTour.registerPageTour) {
      window.EducaAppTour.registerPageTour('mis_preguntas', {
        label: 'Mis Preguntas',
        start: start,
      });
    }
  });
})();
