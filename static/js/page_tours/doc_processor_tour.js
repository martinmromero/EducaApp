/*
 * Recorrido guiado (driver.js) específico de la pantalla "Generar preguntas
 * con IA" (procesador de documentos).
 *
 * Disparado por el usuario desde el menú del botón "?" del navbar (ver
 * base.html + static/js/tour.js) en cualquier momento. Los pasos apuntan a
 * los dos bloques fijos del flujo (Documento / Elegir y generar, ver
 * document_processor_dashboard.html) más algunos elementos que solo existen
 * una vez que ya hay un documento procesado — esos se descartan solos si
 * todavía no están en el DOM (ver buildSteps), así el recorrido funciona
 * igual de bien recién entrando a la pantalla que con un documento ya
 * cargado.
 *
 * Sirve de referencia el mismo mecanismo en
 * static/js/page_tours/create_exam_tour.js.
 */
(function () {
  function buildSteps() {
    var steps = [
      {
        element: '#stepDocumento',
        popover: {
          title: 'Documento',
          description: 'Subir aquí un PDF, DOCX, PPTX o TXT. Una vez procesado, este bloque se resume solo a un renglón — se puede reabrir en cualquier momento con "Cambiar".',
          side: 'right',
          align: 'start',
        },
      },
      {
        element: '#stepContenido',
        popover: {
          title: 'Elegir y generar',
          description: 'Aquí aparecen los capítulos detectados de un documento ya cargado, para elegir cuáles analizar y generar las preguntas con IA.',
          side: 'right',
          align: 'start',
        },
      },
      {
        element: '#localAIStatus',
        popover: {
          title: 'Estado de la IA',
          description: 'Indica si el proveedor de IA configurado está conectado y listo para generar preguntas.',
          side: 'bottom',
        },
      },
      {
        element: '#aiStatusInfoBtn',
        popover: {
          title: 'Más detalles',
          description: 'Muestra el modelo activo y, si corresponde, el cupo compartido restante del día.',
          side: 'bottom',
        },
      },
      {
        element: '#chaptersGrid',
        popover: {
          title: 'Capítulos detectados',
          description: 'Elegir uno o más capítulos para generar preguntas — el color y el tamaño de cada tarjeta ayudan a estimar cuánto entra en una tanda.',
          side: 'top',
        },
      },
      {
        element: '#generateQuestionsBtn',
        popover: {
          title: 'Generar',
          description: 'Al elegir al menos un capítulo, este botón se habilita para generar las preguntas con IA.',
          side: 'top',
        },
      },
    ];
    // Defensivo: descarta pasos cuyo elemento todavía no esté en el DOM (los
    // últimos dos solo existen una vez que hay un documento procesado).
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
      console.error('No se pudo iniciar el recorrido del procesador de documentos:', e);
    }
  }

  window.EducaAppDocProcessorTour = { start: start };

  // Se registra recién en DOMContentLoaded: este script puede cargar antes
  // que static/js/tour.js (que vive en el bloque de scripts de base.html,
  // después del contenido de la página), así que no se puede asumir que
  // window.EducaAppTour ya exista al correr este IIFE.
  document.addEventListener('DOMContentLoaded', function () {
    if (window.EducaAppTour && window.EducaAppTour.registerPageTour) {
      window.EducaAppTour.registerPageTour('doc_processor', {
        label: 'Generar preguntas con IA',
        start: start,
      });
    }
  });
})();
