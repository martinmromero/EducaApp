/*
 * Recorrido guiado (driver.js) del asistente "Subir preguntas"
 * (questions/upload_questions_wizard.html) — alternativa paso a paso al
 * formulario completo de /upload-questions/.
 *
 * Igual que los demás asistentes (ver create_oral_exam_wizard_tour.js), apunta
 * al stepper y a la barra inferior, que están siempre visibles sin importar
 * el paso en el que esté la persona. Los pasos del stepper cambian según se
 * elija cargar una pregunta o un lote, así que el recorrido describe ambos
 * caminos en un único globo en vez de apuntar a pastillas puntuales.
 *
 * Disparado por el usuario desde el menú del botón "?" del navbar (ver
 * base.html + static/js/tour.js) en cualquier momento.
 */
(function () {
  function buildSteps() {
    var steps = [
      {
        element: '[data-uqw] [data-role="stepper"]',
        popover: {
          title: 'Asistente para subir preguntas',
          description: 'Se completa un paso a la vez. Al principio se elige la materia y si se carga una pregunta sola o un lote; los pasos siguientes cambian según esa elección. Se puede volver atrás tocando una pastilla ya recorrida.',
          side: 'bottom',
        },
      },
      {
        element: '[data-uqw] [data-role="subject-chips"]',
        popover: {
          title: 'Materia',
          description: 'Aparecen primero las materias propias (favoritas o con preguntas ya cargadas). Para otra, se busca por nombre abajo; si no existe, se crea en el momento y queda en el espacio personal.',
          side: 'bottom',
        },
      },
      {
        element: '[data-uqw] [data-role="nav"]',
        popover: {
          title: 'Navegación',
          description: 'Una sola pregunta: se escribe el enunciado y la respuesta, se elige tópico y dificultad, y se revisa antes de guardar. Un lote: se sube un archivo CSV o TXT, se muestra una vista previa (con las filas que fallan y los tópicos que se crearían) y recién entonces se importa.',
          side: 'top',
        },
      },
    ];
    return steps.filter(function (s) {
      return window.EducaAppTour && window.EducaAppTour.isVisible
        ? window.EducaAppTour.isVisible(s.element)
        : document.querySelector(s.element);
    });
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
      console.error('No se pudo iniciar el recorrido del Asistente de subir preguntas:', e);
    }
  }

  window.EducaAppUploadQuestionsWizardTour = { start: start };

  document.addEventListener('DOMContentLoaded', function () {
    if (window.EducaAppTour && window.EducaAppTour.registerPageTour) {
      window.EducaAppTour.registerPageTour('upload_questions_wizard', {
        label: 'Asistente para subir preguntas',
        start: start,
      });
    }
  });
})();
