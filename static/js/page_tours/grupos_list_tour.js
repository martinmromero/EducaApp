/*
 * Recorrido guiado (driver.js) de la pantalla "Grupos" (groups/grupos_list.html)
 * — grupos de confianza para compartir el banco de preguntas por materia con
 * otros docentes.
 *
 * Disparado por el usuario desde el menú del botón "?" del navbar (ver
 * base.html + static/js/tour.js) en cualquier momento.
 */
(function () {
  function buildSteps() {
    var steps = [
      {
        element: '#groupIntroText',
        popover: {
          title: 'Grupos de confianza',
          description: 'Permiten compartir el banco de preguntas, por materia, con otros docentes elegidos. Nadie ve ni usa esas preguntas hasta aceptar compartirlas explícitamente, y solo dentro de los grupos de los que se es miembro.',
          side: 'bottom',
        },
      },
      {
        element: '#groupNewBtn',
        popover: {
          title: 'Nuevo grupo',
          description: 'Crea un grupo e invita a otros docentes por su usuario o email.',
          side: 'bottom',
        },
      },
      {
        element: '#groupInvitesBtn',
        popover: {
          title: 'Invitaciones',
          description: 'Acá aparecen las invitaciones a grupos de otros docentes que todavía no se respondieron — el número en rojo indica cuántas hay pendientes.',
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
      console.error('No se pudo iniciar el recorrido de Grupos:', e);
    }
  }

  window.EducaAppGruposListTour = { start: start };

  document.addEventListener('DOMContentLoaded', function () {
    if (window.EducaAppTour && window.EducaAppTour.registerPageTour) {
      window.EducaAppTour.registerPageTour('grupos_list', {
        label: 'Grupos',
        start: start,
      });
    }
  });
})();
