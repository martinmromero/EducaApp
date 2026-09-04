/*
 * Recorrido guiado (driver.js) específico de la pantalla "Plantilla de
 * examen" (create_exam_template.html, usada tanto para crear como para
 * editar).
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
        element: 'input[name="name"]',
        popover: {
          title: 'Nombre de la plantilla',
          description: 'Si se deja vacío, se muestra "Materia - Tipo (Año)" en la lista de plantillas.',
          side: 'bottom',
        },
      },
      {
        element: '.two-column-form',
        popover: {
          title: 'Institución, carrera y materia',
          description: 'Estos datos (más profesor y cátedra, opcionales) se pre-completan en cualquier examen que use esta plantilla. El botón "Nuevo" junto a cada campo permite cargar uno sin salir de esta pantalla.',
          side: 'top',
        },
      },
      {
        element: '#id_print_format',
        popover: {
          title: 'Formato de impresión',
          description: 'Cada plantilla puede tener su propio formato de impresión — útil si se trabaja con más de una institución. Sin elegir nada, se usa el formato predeterminado.',
          side: 'top',
        },
      },
      {
        element: '#learning_outcomes_container',
        popover: {
          title: 'Resultados de aprendizaje',
          description: 'Se habilitan al elegir una materia que ya los tenga cargados.',
          side: 'top',
        },
      },
      {
        element: '#rubrics_container',
        popover: {
          title: 'Rúbricas',
          description: 'Rúbricas ya creadas que se pueden asociar de entrada a cualquier examen que use esta plantilla.',
          side: 'top',
        },
      },
      {
        element: '#save-template-btn',
        popover: {
          title: 'Guardar',
          description: 'Al editar una plantilla existente, este botón actualiza la plantilla original.',
          side: 'top',
        },
      },
      {
        element: '#save-as-copy-btn',
        popover: {
          title: 'Guardar como copia',
          description: 'Guarda los cambios en una plantilla nueva, sin tocar la original — útil para partir de una existente y ajustarla para otro curso o materia.',
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
      console.error('No se pudo iniciar el recorrido de Plantilla de examen:', e);
    }
  }

  window.EducaAppExamTemplateTour = { start: start };

  // Se registra recién en DOMContentLoaded: este script puede cargar antes
  // que static/js/tour.js (que vive en el bloque de scripts de base.html,
  // después del contenido de la página), así que no se puede asumir que
  // window.EducaAppTour ya exista al correr este IIFE.
  document.addEventListener('DOMContentLoaded', function () {
    if (window.EducaAppTour && window.EducaAppTour.registerPageTour) {
      window.EducaAppTour.registerPageTour('exam_template', {
        label: 'Crear una plantilla',
        start: start,
      });
    }
  });
})();
