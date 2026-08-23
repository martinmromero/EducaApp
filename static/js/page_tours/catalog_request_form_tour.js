/*
 * Recorrido guiado (driver.js) de la pantalla "Agregar a mi catálogo"
 * (catalog_requests/form.html) — el asistente de chips paso a paso para
 * pedir alta de institución/facultad/carrera/materia/resultado de
 * aprendizaje.
 *
 * Disparado por el usuario desde el menú del botón "?" del navbar (ver
 * base.html + static/js/tour.js) en cualquier momento.
 */
(function () {
  function buildSteps() {
    var steps = [
      {
        element: '#id_tipo',
        popover: {
          title: 'Qué se quiere agregar',
          description: 'Institución, facultad, carrera, materia o un resultado de aprendizaje — la lista de pasos de abajo cambia según lo que se elija acá.',
          side: 'bottom',
        },
      },
      {
        element: '#catreqChips',
        popover: {
          title: 'Un paso a la vez',
          description: 'Cada chip pregunta por un nivel del contexto (institución, facultad, carrera). Se resuelve buscando algo ya cargado o creando uno nuevo — no hace falta completar todos de una — y el siguiente paso se abre solo.',
          side: 'top',
        },
      },
      {
        element: '#chipFinal',
        popover: {
          title: 'Lo que se está pidiendo',
          description: 'El nombre final propuesto. Si ya existe algo muy parecido en el catálogo, se ofrece usar eso en vez de crear un duplicado.',
          side: 'top',
        },
      },
      {
        element: '#catalogRequestForm button[type="submit"]',
        popover: {
          title: 'Crear',
          description: 'Queda disponible al instante en el espacio personal de quien lo carga, con una insignia que lo distingue de lo institucional. Más adelante puede sumarse al catálogo institucional.',
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
      console.error('No se pudo iniciar el recorrido de Agregar a mi catálogo:', e);
    }
  }

  window.EducaAppCatalogRequestFormTour = { start: start };

  document.addEventListener('DOMContentLoaded', function () {
    if (window.EducaAppTour && window.EducaAppTour.registerPageTour) {
      window.EducaAppTour.registerPageTour('catalog_request_form', {
        label: 'Agregar a mi catálogo',
        start: start,
      });
    }
  });
})();
