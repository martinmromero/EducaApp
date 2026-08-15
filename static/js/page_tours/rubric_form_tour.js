/*
 * Recorrido guiado (driver.js) específico de la pantalla "Crear/Editar
 * rúbrica" (rubricas/form.html) — la grilla de criterios (filas) x niveles
 * (columnas) con una celda de texto por cruce.
 *
 * Disparado por el usuario desde el menú del botón "?" del navbar (ver
 * base.html + static/js/tour.js) en cualquier momento.
 *
 * Sirve de referencia el mismo mecanismo en
 * static/js/page_tours/create_exam_tour.js.
 */
(function () {
  function buildSteps() {
    var steps = [
      {
        element: 'input[name="title"]',
        popover: {
          title: 'Título',
          description: 'El nombre con el que esta rúbrica va a aparecer en la biblioteca y al asociarla a un examen.',
          side: 'bottom',
        },
      },
      {
        element: '#btnAddLevel',
        popover: {
          title: 'Agregar nivel (columna)',
          description: 'Los niveles son las columnas de la grilla — por ejemplo "Excelente", "Bueno", "Insuficiente". Cada uno se puede renombrar o quitar después.',
          side: 'bottom',
        },
      },
      {
        element: '#btnAddCriterion',
        popover: {
          title: 'Agregar criterio (fila)',
          description: 'Los criterios son las filas — cada aspecto que se va a evaluar (por ejemplo "Claridad" o "Fundamentación").',
          side: 'bottom',
        },
      },
      {
        element: '#rubricTable',
        popover: {
          title: 'La grilla',
          description: 'En cada celda se describe cómo se ve ese criterio en ese nivel. El botón "×" de cada fila/columna la quita (debe quedar al menos una de cada una).',
          side: 'top',
        },
      },
      {
        element: 'button[type="submit"]',
        popover: {
          title: 'Guardar rúbrica',
          description: 'Guarda la rúbrica en la biblioteca. Después se puede asociar a cualquier examen desde "Rúbricas del examen".',
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
      console.error('No se pudo iniciar el recorrido de Crear rúbrica:', e);
    }
  }

  window.EducaAppRubricFormTour = { start: start };

  document.addEventListener('DOMContentLoaded', function () {
    if (window.EducaAppTour && window.EducaAppTour.registerPageTour) {
      window.EducaAppTour.registerPageTour('rubric_form', {
        label: 'Crear una rúbrica',
        start: start,
      });
    }
  });
})();
