/*
 * Recorrido guiado (driver.js) de la pantalla "Rúbricas" (rubricas/list.html)
 * — la biblioteca de rúbricas del usuario, puerta de entrada a "Crear una
 * rúbrica" (ver static/js/page_tours/rubric_form_tour.js para el tour de esa
 * otra pantalla).
 *
 * Disparado por el usuario desde el menú del botón "?" del navbar (ver
 * base.html + static/js/tour.js) en cualquier momento.
 */
(function () {
  function buildSteps() {
    var steps = [
      {
        element: '#rubricNewBtn',
        popover: {
          title: 'Nueva rúbrica',
          description: 'Abre un asistente paso a paso para armar la grilla de criterios y niveles — no hay que completarla toda de una vez.',
          side: 'bottom',
        },
      },
      {
        element: '#rubricColOrigen',
        popover: {
          title: 'Origen',
          description: '"Mía" son las rúbricas propias. Las demás llegaron de un grupo de confianza y se muestran con el nombre de quien las compartió — se pueden usar en un examen pero no editar ni borrar.',
          side: 'bottom',
        },
      },
      {
        element: '#rubricColStructure',
        popover: {
          title: 'Niveles y criterios',
          description: 'El tamaño de la grilla de esa rúbrica: cuántas columnas (niveles, ej. "Excelente"/"Bueno") y cuántas filas (criterios evaluados) tiene.',
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
      console.error('No se pudo iniciar el recorrido de Rúbricas:', e);
    }
  }

  window.EducaAppRubricListTour = { start: start };

  document.addEventListener('DOMContentLoaded', function () {
    if (window.EducaAppTour && window.EducaAppTour.registerPageTour) {
      window.EducaAppTour.registerPageTour('rubric_list', {
        label: 'Rúbricas',
        start: start,
      });
    }
  });
})();
