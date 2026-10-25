/*
 * Recorrido guiado (driver.js) del asistente de grupos de confianza
 * (groups/grupo_asistente.html): crear un grupo, invitar docentes y elegir
 * qué compartir, en un solo recorrido.
 *
 * Apunta a los ítems del stepper (#wizStepper [data-step-pill]), que siempre
 * están en el DOM, igual que los demás asistentes (ver
 * static/js/page_tours/create_oral_exam_wizard_tour.js).
 *
 * Disparado por el usuario desde el menú del botón "?" del navbar (ver
 * base.html + static/js/tour.js) en cualquier momento.
 */
(function () {
  function buildSteps() {
    var steps = [
      {
        element: '#wizStepper',
        popover: {
          title: 'Asistente de grupos',
          description: 'Se completa un paso a la vez. Nada se guarda ni se envía hasta el último paso.',
          side: 'bottom',
        },
      },
      {
        element: '[data-step-pill="1"]',
        popover: {
          title: 'A quién invitar',
          description: 'Elegir los docentes que van a recibir la invitación. En un grupo nuevo, acá también se escribe el nombre. Se puede dejar a nadie y invitar más tarde.',
          side: 'bottom',
        },
      },
      {
        element: '[data-step-pill="2"]',
        popover: {
          title: 'Materias',
          description: 'Las preguntas propias de cada materia tildada quedan disponibles para el resto del grupo, para armar exámenes sin poder editarlas ni borrarlas.',
          side: 'bottom',
        },
      },
      {
        element: '[data-step-pill="3"]',
        popover: {
          title: 'Rúbricas, plantillas y formatos',
          description: 'Opcional. Lo tildado queda disponible para que el resto del grupo lo use en sus propios exámenes.',
          side: 'bottom',
        },
      },
      {
        element: '[data-step-pill="4"]',
        popover: {
          title: 'Revisión',
          description: 'Resumen de lo que se va a invitar y compartir antes de confirmar. En un grupo existente, también muestra lo que deja de compartirse.',
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
        progressText: '{{current}} de {{total}}',
        allowClose: true,
        overlayOpacity: 0.6,
        nextBtnText: 'Siguiente',
        prevBtnText: 'Anterior',
        doneBtnText: 'Listo',
        steps: steps,
      }).drive();
    } catch (e) {
      console.error('No se pudo iniciar el recorrido del asistente de grupos:', e);
    }
  }

  window.EducaAppGrupoAsistenteTour = { start: start };

  document.addEventListener('DOMContentLoaded', function () {
    if (window.EducaAppTour && window.EducaAppTour.registerPageTour) {
      window.EducaAppTour.registerPageTour('grupo_asistente', {
        label: 'Asistente de grupos',
        start: start,
      });
    }
  });
})();
