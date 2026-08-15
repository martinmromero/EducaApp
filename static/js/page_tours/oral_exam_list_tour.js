/*
 * Recorrido guiado (driver.js) de la pantalla "Cuestionarios Orales"
 * (oral_exams/list.html) — puerta de entrada a "Crear cuestionario oral"
 * (ver static/js/page_tours/oral_exam_create_tour.js para el tour de esa
 * otra pantalla).
 *
 * Disparado por el usuario desde el menú del botón "?" del navbar (ver
 * base.html + static/js/tour.js) en cualquier momento.
 */
(function () {
  function buildSteps() {
    var steps = [
      {
        element: '#oralNewBtn',
        popover: {
          title: 'Nuevo cuestionario',
          description: 'Arma un cuestionario oral: elegí materia y tópicos, y el sistema distribuye las preguntas entre los grupos de estudiantes.',
          side: 'bottom',
        },
      },
      {
        element: '#oralFavoritosBtn',
        popover: {
          title: 'Favoritos',
          description: 'Filtra la lista para mostrar solo los cuestionarios marcados con la estrella.',
          side: 'bottom',
        },
      },
      {
        element: '#selectAll',
        popover: {
          title: 'Selección múltiple',
          description: 'Tildando el casillero de uno o más cuestionarios aparece una barra con la cantidad seleccionada y el botón para eliminarlos juntos.',
          side: 'bottom',
        },
      },
      {
        element: '#oralColGroups',
        popover: {
          title: 'Grupos, estudiantes y preguntas',
          description: 'Estas cuatro columnas resumen la configuración: en cuántos grupos se dividió el curso, cuántos estudiantes entran en cada uno, cuántas preguntas responde cada estudiante y el total de estudiantes contemplado.',
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
      console.error('No se pudo iniciar el recorrido de Cuestionarios Orales:', e);
    }
  }

  window.EducaAppOralExamListTour = { start: start };

  document.addEventListener('DOMContentLoaded', function () {
    if (window.EducaAppTour && window.EducaAppTour.registerPageTour) {
      window.EducaAppTour.registerPageTour('oral_exam_list', {
        label: 'Cuestionarios Orales',
        start: start,
      });
    }
  });
})();
