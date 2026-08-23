/*
 * Recorrido guiado (driver.js) de la pantalla "Solicitudes de catálogo"
 * (catalog_requests/bandeja.html) — bandeja admin para aprobar, rechazar
 * o fusionar los pedidos de alta que llegan del espacio personal de cada
 * usuario (ver static/js/page_tours/catalog_request_form_tour.js para el
 * tour de esa otra pantalla).
 *
 * Disparado por el usuario desde el menú del botón "?" del navbar (ver
 * base.html + static/js/tour.js) en cualquier momento.
 */
(function () {
  function buildSteps() {
    var steps = [
      {
        element: 'table.table',
        popover: {
          title: 'Solicitudes pendientes',
          description: 'Cada fila es un pedido de alta con su contexto (institución, facultad, carrera) y quién lo solicitó. "mismo pedido" agrupa filas que llegaron juntas en una misma cadena.',
          side: 'top',
        },
      },
      {
        element: 'button[name="accion"][value="aprobar"]',
        popover: {
          title: 'Aprobar o rechazar',
          description: 'Aprobar suma la fila al catálogo institucional. Rechazar la deja fuera — la nota es opcional y se le muestra a quien la pidió.',
          side: 'top',
        },
      },
      {
        element: '.btn-toggle-fusion',
        popover: {
          title: 'Fusionar con algo existente',
          description: 'Cuando el pedido es en realidad un duplicado que el matcheo automático no atrapó, "Fusionar" re-apunta todo lo que tenga cargado (temas, preguntas, vínculos) a una fila ya institucional y borra el borrador personal.',
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
      console.error('No se pudo iniciar el recorrido de Solicitudes de catálogo:', e);
    }
  }

  window.EducaAppCatalogRequestsBandejaTour = { start: start };

  document.addEventListener('DOMContentLoaded', function () {
    if (window.EducaAppTour && window.EducaAppTour.registerPageTour) {
      window.EducaAppTour.registerPageTour('catalog_requests_bandeja', {
        label: 'Solicitudes de catálogo',
        start: start,
      });
    }
  });
})();
