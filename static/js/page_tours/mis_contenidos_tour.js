/*
 * Recorrido guiado (driver.js) de la pantalla "Mis Contenidos"
 * (questions/mis_contenidos.html) — puerta de entrada a "Subir Contenido" y
 * a "Generar con IA" (ver static/js/page_tours/doc_processor_tour.js).
 *
 * Disparado por el usuario desde el menú del botón "?" del navbar (ver
 * base.html + static/js/tour.js) en cualquier momento.
 */
(function () {
  function buildSteps() {
    var steps = [
      {
        element: '#contenidoUploadBtn',
        popover: {
          title: 'Subir contenido',
          description: 'Sube un apunte, PDF o material de clase para poder analizarlo con IA y generar preguntas a partir de él.',
          side: 'bottom',
        },
      },
      {
        element: '#contenidoPolicyAlert',
        popover: {
          title: 'Política de almacenamiento',
          description: 'El archivo original se borra al cerrar sesión — no queda guardado indefinidamente. Las preguntas ya generadas a partir de él y los metadatos (título, ISBN, materias) se conservan siempre.',
          side: 'bottom',
        },
      },
      {
        element: '#contenidoDeleteBtn',
        popover: {
          title: 'Borrado múltiple',
          description: 'Al tildar el casillero de uno o más contenidos vigentes, este botón borra sus archivos juntos (los metadatos y las preguntas generadas se conservan).',
          side: 'top',
        },
      },
      {
        element: '#contenidoBorradosSection',
        popover: {
          title: 'Ya borrados',
          description: 'Historial de contenidos cuyo archivo ya se eliminó (por la política de arriba) pero cuyos datos y preguntas generadas siguen disponibles.',
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
      console.error('No se pudo iniciar el recorrido de Mis Contenidos:', e);
    }
  }

  window.EducaAppMisContenidosTour = { start: start };

  document.addEventListener('DOMContentLoaded', function () {
    if (window.EducaAppTour && window.EducaAppTour.registerPageTour) {
      window.EducaAppTour.registerPageTour('mis_contenidos', {
        label: 'Mis Contenidos',
        start: start,
      });
    }
  });
})();
