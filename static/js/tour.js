/*
 * Recorrido guiado de EducaApp (driver.js, vendorizado en static/js/vendor/).
 * Recorre el sidebar/navbar reales — no hace falta una página especial.
 *
 * window.EducaAppTour.start() lo dispara el botón "?" del navbar (ver
 * base.html) en cualquier página, y también se auto-dispara una sola vez
 * (localStorage) al entrar por primera vez al asistente de configuración
 * (ver onboarding_v2.html), antes de pedir cualquier dato.
 */
(function () {
  const STORAGE_KEY = 'educaapp_tour_done';

  // El sidebar tiene grupos con submenú (Exámenes, Mi espacio académico) e
  // ítems simples sin submenú (Asistente, Generar con IA, Preguntas,
  // Grupos). expandMenu() sirve para ambos: en un ítem simple la clase
  // "active" no tiene efecto visible (no hay .submenu que mostrar), pero
  // igual cierra cualquier otro submenú que haya quedado abierto.
  function expandMenu(menuId) {
    document.querySelectorAll('.sidebar .menu-item').forEach((item) => {
      item.classList.remove('active');
    });
    const group = document.getElementById(menuId);
    if (group) group.classList.add('active');
  }

  function collapseAllMenus() {
    document.querySelectorAll('.sidebar .menu-item').forEach((item) => {
      item.classList.remove('active');
    });
  }

  // Resalte secundario del paso 1: además del elemento principal del paso
  // (que driver.js recorta del overlay), se destaca a la vez el botón "?"
  // arriba a la derecha, para que quede claro desde el primer paso que el
  // recorrido se puede repetir desde ahí (ver .tour-secondary-highlight en
  // styles.css).
  function highlightHelpBtn() {
    const btn = document.getElementById('tourHelpBtn');
    if (btn) btn.classList.add('tour-secondary-highlight');
  }

  function unhighlightHelpBtn() {
    const btn = document.getElementById('tourHelpBtn');
    if (btn) btn.classList.remove('tour-secondary-highlight');
  }

  // Último paso: abre de verdad el dropdown "?" (Bootstrap) para poder
  // resaltar dentro de él la opción "Área de Pruebas".
  function openTourHelpDropdown() {
    const btn = document.getElementById('tourHelpBtn');
    if (!btn || !window.bootstrap) return;
    window.bootstrap.Dropdown.getOrCreateInstance(btn).show();
  }

  function closeTourHelpDropdown() {
    const btn = document.getElementById('tourHelpBtn');
    if (!btn || !window.bootstrap) return;
    const dropdown = window.bootstrap.Dropdown.getInstance(btn);
    if (dropdown) dropdown.hide();
  }

  // Pasos con selector + texto. Si un elemento no está en el DOM de la
  // página actual (ej. "Administración" solo existe para admins) se
  // descarta automáticamente al construir el tour.
  const STEP_DEFS = [
    {
      element: '#tourHelpBtn',
      popover: {
        title: '¡Bienvenido a EducaApp!',
        description: 'Este recorrido presenta brevemente la ubicación de las funciones principales. Puede repetirse en cualquier momento desde el botón "?" resaltado arriba a la derecha.',
        side: 'bottom',
        align: 'end',
      },
      onHighlightStarted: highlightHelpBtn,
      onDeselected: unhighlightHelpBtn,
    },
    {
      element: '#tourMenuAsistente',
      popover: {
        title: 'Asistente paso a paso',
        description: 'El recorrido paso a paso: institución, carrera, materia, preguntas y examen, todo en un mismo lugar. Es el primer ítem del menú y la puerta de entrada.',
        side: 'right',
      },
      onHighlightStarted: () => expandMenu('tourMenuAsistente'),
    },
    {
      element: '#tourMenuGenerarIA',
      popover: {
        title: 'Generar con IA',
        description: 'Se sube un apunte, PDF o material de clase y la IA genera preguntas automáticamente a partir de su contenido. Es la función más usada de EducaApp. Dentro de esa pantalla, el botón "Configuración de IA" permite elegir el proveedor de IA y cargar una clave propia.',
        side: 'right',
      },
      onHighlightStarted: () => expandMenu('tourMenuGenerarIA'),
    },
    {
      element: '#tourMenuPreguntas',
      popover: {
        title: 'Preguntas',
        description: 'Aquí vive el banco de preguntas: si ya hay preguntas armadas con su respuesta, se pueden subir directo, tanto individualmente como en lotes. Las que genera la IA se pueden aprobar o rechazar cada una, pero se guardan todas, para que la IA tenga memoria de las preferencias la próxima vez.',
        side: 'right',
      },
      onHighlightStarted: () => expandMenu('tourMenuPreguntas'),
    },
    {
      element: '#tourMenuExamenes',
      popover: {
        title: 'Mis exámenes',
        description: 'Aquí están los exámenes armados con el banco de preguntas — al elegir, solo aparecen las que fueron aprobadas. Se dividen en Escritos y Orales.',
        side: 'right',
      },
      onHighlightStarted: () => expandMenu('tourMenuExamenes'),
    },
    {
      // En el modo simple reemplaza a "Mi espacio académico": el estado de lo propuesto al catálogo.
      element: '#tourMenuAgregados',
      popover: {
        title: 'Mis agregados',
        description: 'Los elementos (materias, carreras, tópicos...) que se cargaron al espacio personal.',
        side: 'right',
      },
      onHighlightStarted: () => expandMenu('tourMenuAgregados'),
    },
    {
      element: '#tourMenuAcademico',
      popover: {
        title: 'Mi espacio académico',
        description: 'Lo que se agregó al espacio personal, más institución, carrera, materia y los contenidos subidos — la estructura académica, que se configura una vez y se cambia ocasionalmente.',
        side: 'right',
      },
      onHighlightStarted: () => expandMenu('tourMenuAcademico'),
    },
    {
      element: '#tourMenuContenidos',
      popover: {
        title: 'Contenidos',
        description: 'Biblioteca de todo lo que se subió: apuntes, PDFs y materiales de clase. Vive dentro de Mi espacio académico.',
        side: 'right',
      },
      onHighlightStarted: () => expandMenu('tourMenuAcademico'),
    },
    {
      element: '#tourMenuFormatosPlantillas',
      popover: {
        title: 'Formatos y plantillas',
        description: 'Los modelos que se reutilizan al armar exámenes: plantillas, rúbricas y formatos de impresión.',
        side: 'right',
      },
      onHighlightStarted: () => expandMenu('tourMenuFormatosPlantillas'),
    },
    {
      element: '#tourMenuPlantillas',
      popover: {
        title: 'Plantillas',
        description: 'Aquí se pueden crear plantillas de examen reutilizables, para no repetir la misma configuración cada vez.',
        side: 'right',
      },
      onHighlightStarted: () => expandMenu('tourMenuFormatosPlantillas'),
    },
    {
      element: '#tourMenuFormatos',
      popover: {
        title: 'Formatos de Impresión',
        description: 'Aquí se define cómo se ve el examen impreso (membrete, colores, tamaño de hoja). Si se trabaja con más de una institución, se pueden guardar varios formatos — uno por cada una — para tener los exámenes listos con el membrete correspondiente.',
        side: 'right',
      },
      onHighlightStarted: () => expandMenu('tourMenuFormatosPlantillas'),
    },
    {
      element: '#tourMenuGrupos',
      popover: {
        title: 'Grupos',
        description: 'Grupos de confianza para compartir materias, rúbricas, plantillas y formatos con otros docentes.',
        side: 'right',
      },
      onHighlightStarted: collapseAllMenus,
    },
    {
      element: '#tourTamanoLetra',
      popover: {
        title: 'Tamaño de letra',
        description: 'Si el texto se ve chico, aquí se agranda en toda la app. Automático agranda un poco en el celular.',
        side: 'right',
      },
    },
    {
      element: '#visualThemeDropdown',
      popover: {
        title: 'Tema visual',
        description: 'Aquí se elige el estilo de colores y tipografía para toda la app.',
        side: 'top',
      },
    },
    {
      element: '#toggleMode',
      popover: {
        title: 'Modo claro / oscuro',
        description: 'Y aquí se alterna entre modo claro y oscuro, según preferencia.',
        side: 'top',
      },
    },
    {
      element: '#tourModeToggle',
      popover: {
        title: 'Modo simple o avanzado',
        description: 'Apagado, el modo simple muestra solo lo esencial y arma todo con asistentes. Encendido, el modo avanzado suma el menú completo (contenidos, instituciones, carreras, materias, plantillas, rúbricas, grupos) y los formularios de siempre. Se puede cambiar entre modos cuando se desee.',
        side: 'bottom',
      },
    },
    {
      element: '#tourMisDatos',
      popover: {
        title: 'Mis datos',
        description: 'El perfil y la configuración personal, siempre a un click, aquí abajo.',
        side: 'top',
      },
    },
    {
      element: '#tourAreaPruebasItem',
      popover: {
        title: 'Área de Pruebas',
        description: 'En este espacio se pueden hacer pruebas de uso, sin afectar al resto del sistema. Ahí también está el botón "Ver el ejemplo paso a paso", con un examen ya armado y explicado.',
        side: 'left',
        align: 'start',
      },
      onHighlightStarted: openTourHelpDropdown,
      onDeselected: closeTourHelpDropdown,
    },
    {
      // Vive dentro del menú "?" (Ayuda), último ítem: el paso lo abre, igual que el de Área de Pruebas de arriba.
      element: '#tourContactoAutor',
      popover: {
        title: 'Hablar con el autor',
        description: 'Desde aquí se puede contactar al autor de la aplicación.',
        side: 'left',
        align: 'start',
      },
      onHighlightStarted: openTourHelpDropdown,
      onDeselected: closeTourHelpDropdown,
    },
  ];

  // El recorrido que arranca solo en el primer ingreso deja afuera lo que no hace falta para empezar o que la propia
  // pantalla inicial ya explica (el modo simple/avanzado se elige ahí mismo). Todo sigue en el recorrido del botón "?".
  const OMITIR_EN_PRIMER_INGRESO = ['#visualThemeDropdown', '#toggleMode', '#tourModeToggle', '#tourAreaPruebasItem', '#tourTamanoLetra'];

  function buildSteps(primerIngreso) {
    const celular = window.innerWidth <= 768;
    return STEP_DEFS.filter((step) => document.querySelector(step.element)
      && !(primerIngreso && OMITIR_EN_PRIMER_INGRESO.indexOf(step.element) !== -1))
      .map((step) => {
        // En el celular el menú ocupa 250 de los ~375 px: un globo "a la derecha" no entra y tapaba justo el ítem
        // señalado. Para los ítems del menú el globo va debajo (el motor lo pasa arriba si abajo no hay lugar).
        if (!celular || !step.popover || !document.querySelector(step.element).closest('#sidebar')) return step;
        return Object.assign({}, step, { popover: Object.assign({}, step.popover, { side: 'bottom', align: 'start' }) });
      });
  }

  // El navegador no permite mover el cursor real del mouse por seguridad,
  // así que en su lugar destacamos el botón "Siguiente": lo enfocamos (para
  // que Enter/Espacio lo dispare) y le agregamos un pulso visual que llama
  // la atención hacia él en cada paso.
  function focusNextButton(popover) {
    const btn = popover && popover.nextButton;
    if (!btn || btn.style.display === 'none') return;
    btn.classList.add('tour-next-pulse');
    btn.focus({ preventScroll: true });
  }

  // En mobile el sidebar arranca oculto fuera de pantalla (clase
  // "mobile-open" lo trae a la vista, ver base.html). driver.js igual
  // encuentra los elementos con document.querySelector (siguen en el DOM),
  // así que el tour "corría" en silencio contra un sidebar invisible —
  // se veía como si no pasara nada. Se abre el sidebar antes de arrancar
  // si hace falta, y se cierra de nuevo al terminar.
  function isMobileViewport() {
    return window.innerWidth <= 768;
  }

  // En escritorio el menú puede estar colapsado (modo simple arranca así): el recorrido lo abre
  // y lo deja como estaba. toggleSidebar(true) no guarda eso como elección de quien lo usa.
  function ensureSidebarVisible() {
    const sidebar = document.getElementById('sidebar');
    if (!sidebar) return false;
    if (!isMobileViewport()) {
      // "sb-pre": el modo simple arranca colapsado solo con CSS y la clase real llega después (ver base.html).
      const teniaPre = document.documentElement.classList.contains('sb-pre');
      if (teniaPre) document.documentElement.classList.remove('sb-pre');
      if (!sidebar.classList.contains('collapsed') || typeof window.toggleSidebar !== 'function') return teniaPre ? 'desktop' : false;
      window.toggleSidebar(true);
      return 'desktop';
    }
    if (sidebar.classList.contains('mobile-open')) return false;
    if (typeof window.toggleSidebar === 'function') {
      window.toggleSidebar();
      return 'mobile';
    }
    return false;
  }

  function restoreSidebar(openedByTour) {
    if (openedByTour === 'desktop') {
      // Solo si sigue abierto (onDestroyed puede llegar más de una vez): se vuelve a colapsar.
      const sidebar = document.getElementById('sidebar');
      if (sidebar && !sidebar.classList.contains('collapsed') && typeof window.toggleSidebar === 'function') {
        window.toggleSidebar(true);
      }
    } else if (openedByTour && typeof window.closeSidebarMobile === 'function') {
      window.closeSidebarMobile();
    }
  }

  function leerCookie(nombre) {
    const par = document.cookie.split('; ').find((c) => c.indexOf(nombre + '=') === 0);
    return par ? decodeURIComponent(par.slice(nombre.length + 1)) : '';
  }

  // Aviso al querer salir del recorrido que arranca solo en el primer ingreso: pregunta si se quiere salir y ofrece
  // "No volver a mostrar" (se guarda en la cuenta, no en el navegador). Devuelve true si se sale.
  async function confirmarSalida() {
    const ModalApp = window.EducaAppModal;
    if (!ModalApp || !ModalApp.confirm) return true;
    const respuesta = await ModalApp.confirm(
      '¿Salir del recorrido? Se puede volver a ver cuando se quiera desde el botón "?" (Ayuda) de arriba a la derecha.',
      {
        title: 'Salir del recorrido',
        variant: 'warning',
        okLabel: 'Salir',
        cancelLabel: 'Seguir con el recorrido',
        checkboxLabel: 'No volver a mostrar este recorrido al ingresar',
      }
    );
    if (!respuesta.ok) return false;
    if (respuesta.checked) {
      try {
        await fetch('/ayuda/no-mostrar/', {
          method: 'POST',
          headers: { 'X-CSRFToken': leerCookie('csrftoken') },
          sinAviso: true,
        });
      } catch (e) { /* si falla, el recorrido simplemente puede volver a aparecer */ }
    }
    return true;
  }

  // Primer ingreso: arranca recién cuando la página terminó de cargar. En el celular base.html cierra el menú
  // lateral en el evento "load"; si el recorrido abre el menú antes, ese cierre lo deja señalando algo que no se ve.
  function startFirstUse() {
    const arrancar = () => setTimeout(() => start({ primerIngreso: true }), 150);
    if (document.readyState === 'complete') arrancar();
    else window.addEventListener('load', arrancar, { once: true });
  }

  function start(opciones) {
    if (!window.driver || !window.driver.js) return;
    const primerIngreso = !!(opciones && opciones.primerIngreso);
    const steps = buildSteps(primerIngreso);
    if (!steps.length) return;
    const openedSidebar = ensureSidebarVisible();
    let tourDriver = null;
    tourDriver = window.driver.js.driver({
      showProgress: true,
      progressText: '{{current}} de {{total}}',
      allowClose: true,
      overlayOpacity: 0.6,
      nextBtnText: 'Siguiente',
      prevBtnText: 'Anterior',
      doneBtnText: 'Listo',
      steps: steps,
      onPopoverRender: focusNextButton,
      // En el celular el menú se desliza al abrirse: el motor calcula el recuadro con el menú todavía a medio camino y
      // lo deja desfasado. Se recalcula cuando termina el deslizamiento.
      onHighlighted: () => {
        if (!isMobileViewport()) return;
        setTimeout(() => { if (tourDriver && tourDriver.isActive()) tourDriver.refresh(); }, 450);
      },
      // Solo en el recorrido que arranca solo: cerrar a mitad de camino (X, Escape, clic afuera) pregunta antes.
      // El que se pide a propósito desde "?" se cierra sin preguntar.
      onDestroyStarted: () => {
        if (!primerIngreso || tourDriver.isLastStep()) { tourDriver.destroy(); return; }
        confirmarSalida().then((salir) => { if (salir) tourDriver.destroy(); });
      },
      onDestroyed: () => {
        try { localStorage.setItem(STORAGE_KEY, '1'); } catch (e) {}
        restoreSidebar(openedSidebar);
        unhighlightHelpBtn();
        closeTourHelpDropdown();
      },
    });
    tourDriver.drive();
    // driver.js no siempre llama a onDestroyed al cerrar con la X: se vigila también que el
    // recorrido deje de estar activo para dejar el menú como estaba.
    if (openedSidebar) {
      const observer = new MutationObserver(() => {
        if (document.body.classList.contains('driver-active')) return;
        observer.disconnect();
        restoreSidebar(openedSidebar);
      });
      observer.observe(document.body, { attributes: true, attributeFilter: ['class'] });
    }
  }

  function startIfFirstVisit() {
    let done = false;
    try { done = localStorage.getItem(STORAGE_KEY) === '1'; } catch (e) {}
    if (!done) start();
  }

  // ── Recorridos específicos por pantalla ──────────────────────────────────
  // Además del recorrido general de arriba, una pantalla puede registrar su
  // propio recorrido corto (ver static/js/page_tours/create_exam_tour.js
  // para el primer caso, "Crear examen"). El botón "?" del navbar (ver
  // base.html) ofrece elegir entre ambos cuando hay uno registrado para la
  // pantalla actual; si no hay ninguno, arranca directo el recorrido
  // general, igual que antes.
  //
  // Convención para agregar un recorrido a una pantalla nueva:
  //   1. En la plantilla, setear <body data-tour-page="mi_pantalla">
  //      (ver {% block body_extra_attrs %} en base.html).
  //   2. Cargar un script propio (ej. static/js/page_tours/mi_pantalla_tour.js)
  //      que llame a window.EducaAppTour.registerPageTour('mi_pantalla', {
  //        label: 'Texto para el botón del menú',
  //        start: function () { ... arma los steps y llama a .drive() ... },
  //      });
  const pageTours = {};

  function registerPageTour(key, def) {
    pageTours[key] = def;
  }

  function getCurrentPageTour() {
    const key = document.body && document.body.dataset.tourPage;
    return key ? (pageTours[key] || null) : null;
  }

  // Un paso de recorrido solo tiene sentido si su elemento se ve: una
  // columna que el usuario ocultó desde "Columnas" sigue en el DOM (con
  // display:none) y driver.js la resaltaría como un recuadro vacío. Los
  // recorridos de listados filtran sus pasos con esto en vez de con un
  // querySelector pelado.
  function isVisible(selector) {
    const el = document.querySelector(selector);
    return !!el && el.getClientRects().length > 0;
  }

  window.EducaAppTour = { start, startFirstUse, startIfFirstVisit, registerPageTour, getCurrentPageTour, isVisible };
})();
