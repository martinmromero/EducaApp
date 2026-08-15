/*
 * Recorrido guiado (driver.js) de la pantalla "Formatos de Impresión"
 * (formatos_impresion/list.html) — puerta de entrada a "Nuevo formato".
 *
 * Disparado por el usuario desde el menú del botón "?" del navbar (ver
 * base.html + static/js/tour.js) en cualquier momento.
 */
(function () {
  function buildSteps() {
    var steps = [
      {
        element: '#formatoNewBtn',
        popover: {
          title: 'Nuevo formato',
          description: 'Define cómo se ve el examen impreso: membrete, colores, fuente y tamaño de hoja, con vista previa en vivo.',
          side: 'bottom',
        },
      },
      {
        element: '#formatoColAlcance',
        popover: {
          title: 'Alcance',
          description: '"Usuario" aplica a toda la cuenta. "Institución" aplica solo a los exámenes de esa institución (útil si se trabaja en más de una). "Global" es el que trae el sistema por defecto.',
          side: 'bottom',
        },
      },
      {
        element: '#formatoColDefault',
        popover: {
          title: 'Predeterminado',
          description: 'El formato marcado como predeterminado es el que se usa automáticamente en cualquier examen o plantilla que no elija uno explícitamente.',
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
      console.error('No se pudo iniciar el recorrido de Formatos de Impresión:', e);
    }
  }

  window.EducaAppFormatoImpresionListTour = { start: start };

  document.addEventListener('DOMContentLoaded', function () {
    if (window.EducaAppTour && window.EducaAppTour.registerPageTour) {
      window.EducaAppTour.registerPageTour('formato_impresion_list', {
        label: 'Formatos de Impresión',
        start: start,
      });
    }
  });
})();
