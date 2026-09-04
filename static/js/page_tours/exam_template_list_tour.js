/*
 * Recorrido guiado (driver.js) de la pantalla "Plantillas"
 * (exams/list_exam_templates.html) — puerta de entrada a "Crear plantilla"
 * (ver static/js/page_tours/exam_template_tour.js para el tour de esa otra
 * pantalla).
 *
 * Disparado por el usuario desde el menú del botón "?" del navbar (ver
 * base.html + static/js/tour.js) en cualquier momento.
 */
(function () {
  function buildSteps() {
    var steps = [
      {
        element: '#templateNewBtn',
        popover: {
          title: 'Nueva plantilla',
          description: 'Arma una configuración reutilizable (institución, materia, formato de impresión, rúbricas) para no repetirla en cada examen.',
          side: 'bottom',
        },
      },
      {
        element: '#templateWizardBtn',
        popover: {
          title: 'Asistente',
          description: 'La misma información, pero pedida un paso a la vez — útil para armar la primera plantilla o cuando conviene ir de a poco.',
          side: 'bottom',
        },
      },
      {
        element: '#templateFavoritosBtn',
        popover: {
          title: 'Favoritas',
          description: 'Filtra la lista para mostrar solo las plantillas marcadas con la estrella — útil si se maneja más de una institución o materia.',
          side: 'bottom',
        },
      },
      {
        element: '#selectAll',
        popover: {
          title: 'Selección múltiple',
          description: 'Tildando el casillero de una o más plantillas aparece una barra con la cantidad seleccionada y el botón para eliminarlas juntas.',
          side: 'bottom',
        },
      },
      {
        element: '#templateColInstitution',
        popover: {
          title: 'Filtros por columna',
          description: 'Cada columna con este ícono de embudo se puede filtrar de forma independiente (institución, facultad, carrera, materia, profesor, año).',
          side: 'bottom',
        },
      },
      {
        element: '#templateColActions',
        popover: {
          title: 'Acciones',
          description: 'Ver (previsualiza), Editar, el botón verde crea directamente un examen nuevo con esta plantilla ya aplicada, y Eliminar.',
          side: 'left',
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
      console.error('No se pudo iniciar el recorrido de Plantillas:', e);
    }
  }

  window.EducaAppExamTemplateListTour = { start: start };

  document.addEventListener('DOMContentLoaded', function () {
    if (window.EducaAppTour && window.EducaAppTour.registerPageTour) {
      window.EducaAppTour.registerPageTour('exam_template_list', {
        label: 'Plantillas',
        start: start,
      });
    }
  });
})();
