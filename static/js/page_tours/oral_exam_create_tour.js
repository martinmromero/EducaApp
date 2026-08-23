/*
 * Recorrido guiado (driver.js) específico de la pantalla "Crear cuestionario
 * oral" (oral_exams/create.html) — un formulario de revelado secuencial: cada
 * campo se habilita recién cuando el anterior tiene un valor válido, y
 * "Número de grupos" / "Estudiantes por grupo" se calculan solos (aunque se
 * pueden ajustar a mano).
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
        element: '#id_subject',
        popover: {
          title: 'Materia',
          description: 'Al elegir la materia se cargan sus tópicos. El resto de los campos permanece deshabilitado hasta completar este paso.',
          side: 'bottom',
        },
      },
      {
        element: '#topics-container',
        popover: {
          title: 'Tópicos a evaluar',
          description: 'Se pueden tildar de a uno o todos juntos con los botones "Todo" / "Ninguno". Elegir al menos uno habilita "Total de estudiantes" y muestra un panel con las preguntas y sub-tópicos disponibles para esa selección.',
          side: 'top',
        },
      },
      {
        element: '#id_total_students',
        popover: {
          title: 'Total de estudiantes',
          description: 'La cantidad de estudiantes que van a rendir este cuestionario oral.',
          side: 'bottom',
        },
      },
      {
        element: '#id_questions_per_student',
        popover: {
          title: 'Preguntas por estudiante',
          description: 'Cuántas preguntas le toca responder a cada estudiante — habilita el cálculo automático de grupos.',
          side: 'bottom',
        },
      },
      {
        element: '#id_num_groups',
        popover: {
          title: 'Grupos',
          description: '"Número de grupos" y "Estudiantes por grupo" se calculan automáticamente entre sí. Se puede ajustar cualquiera de los dos a mano: el otro se recalcula solo.',
          side: 'top',
        },
      },
      {
        element: '#id_name',
        popover: {
          title: 'Nombre del cuestionario',
          description: 'Sirve para identificarlo después en la lista de Cuestionarios Orales.',
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
      console.error('No se pudo iniciar el recorrido de Crear cuestionario oral:', e);
    }
  }

  window.EducaAppOralExamCreateTour = { start: start };

  document.addEventListener('DOMContentLoaded', function () {
    if (window.EducaAppTour && window.EducaAppTour.registerPageTour) {
      window.EducaAppTour.registerPageTour('oral_exam_create', {
        label: 'Crear un cuestionario oral',
        start: start,
      });
    }
  });
})();
