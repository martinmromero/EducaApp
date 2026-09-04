/*
 * Recorrido guiado (driver.js) específico de la pantalla "Nueva Institución"
 * (institutions_v2/create.html) — primer recorrido de esta pantalla.
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
        element: '#id_name',
        popover: {
          title: 'Nombre',
          description: 'Único dato obligatorio de esta pantalla.',
          side: 'bottom',
        },
      },
      {
        element: '#id_sigla',
        popover: {
          title: 'Sigla',
          description: 'Opcional — por ejemplo UBA, UAI. Se usa junto al nombre en listados y encabezados.',
          side: 'bottom',
        },
      },
      {
        element: '#campuses-container',
        popover: {
          title: 'Sedes',
          description: 'Opcional — se pueden cargar varias sedes de una, o dejarlo en blanco y agregarlas después.',
          side: 'top',
        },
      },
      {
        element: '#logo-container',
        popover: {
          title: 'Logo',
          description: 'Opcional. Acepta JPG, PNG o SVG de hasta 2MB — aparece en el encabezado impreso de los exámenes.',
          side: 'top',
        },
      },
      {
        element: '#faculties-container',
        popover: {
          title: 'Facultades',
          description: 'Opcional — se pueden cargar varias facultades de una, o dejarlo en blanco y agregarlas después.',
          side: 'top',
        },
      },
      {
        element: '#institution-form button[type="submit"]',
        popover: {
          title: 'Crear institución',
          description: 'Guarda la institución con las sedes y facultades cargadas.',
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
      console.error('No se pudo iniciar el recorrido de Nueva Institución:', e);
    }
  }

  window.EducaAppCreateInstitutionV2Tour = { start: start };

  document.addEventListener('DOMContentLoaded', function () {
    if (window.EducaAppTour && window.EducaAppTour.registerPageTour) {
      window.EducaAppTour.registerPageTour('create_institution_v2', {
        label: 'Crear una institución',
        start: start,
      });
    }
  });
})();
