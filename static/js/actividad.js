/* Aviso de actividad: una barra fina arriba (y, si la espera se alarga, un mensaje) mientras la app
   trabaja, para que nunca parezca colgada. Es autónomo: no depende de que cada pantalla lo pida.
   Se activa cuando:
     - se toca un enlace interno o se envía un formulario (la página nueva todavía no llegó);
     - cualquier fetch() tarda más del umbral (listas que se completan, guardados, búsquedas).
   La barra aparece recién a los UMBRAL_MS: lo instantáneo no parpadea. Quien no quiere el aviso en un
   pedido de fondo pasa { sinAviso: true } como segundo argumento de fetch().
   Una lista que se completa con ese pedido (temas, carreras, resultados de aprendizaje) se marca con
   { cargando: '#lista' } (un selector, un elemento o un arreglo de ambos): mientras llega se ve atenuada
   con "Cargando…" (los select se deshabilitan). Sin esto la lista queda vacía o con lo anterior y no
   se entiende si no hay datos o si todavía no llegaron.
   Los envíos de formularios POST además los cubre submit_guard.js (botón "Guardando…") y las
   descargas descarga_guard.js; esta barra convive con ambos. */
(function () {
  var UMBRAL_MS = 300;        // antes de esto no se muestra nada
  var AVISO_1_MS = 5000;      // "tarda más de lo habitual"
  var AVISO_2_MS = 20000;     // "puede llevar hasta un minuto"
  var NAVEGACION_MAX_MS = 90000; // red de seguridad: una navegación que nunca llega (descarga, cancelada)
  var SIN_AVISO = /(export|download|descargar|\bpdf\b|docx|\/media\/)/i; // respuestas que son archivos

  var pedidos = 0;
  var navegando = false;
  var inicio = 0;
  var visible = false;
  var timers = [];
  var timerNavegacion = null;
  var barra = null;
  var aviso = null;

  var CARGANDO_MS = 250; // las listas que llegan al instante no parpadean

  function elementos(x) {
    if (!x) return [];
    return (Array.isArray(x) ? x : [x]).map(function (i) {
      return typeof i === 'string' ? document.querySelector(i) : i;
    }).filter(Boolean);
  }

  function marcarCargando(els) {
    els.forEach(function (el) {
      el.__eduCarg = (el.__eduCarg || 0) + 1;
      if (el.__eduCarg !== 1) return;
      el.__eduCargTimer = setTimeout(function () {
        el.classList.add('edu-cargando');
        el.setAttribute('aria-busy', 'true');
        if (el.tagName === 'SELECT') {
          el.__eduCargDeshab = el.disabled;
          el.disabled = true;
        }
      }, CARGANDO_MS);
    });
  }

  function desmarcarCargando(els) {
    els.forEach(function (el) {
      el.__eduCarg = Math.max(0, (el.__eduCarg || 1) - 1);
      if (el.__eduCarg) return;
      clearTimeout(el.__eduCargTimer);
      if (!el.classList.contains('edu-cargando')) return;
      el.classList.remove('edu-cargando');
      el.removeAttribute('aria-busy');
      if (el.tagName === 'SELECT') el.disabled = !!el.__eduCargDeshab;
    });
  }

  function inyectarEstilo() {
    if (document.getElementById('actividadEstilo')) return;
    var st = document.createElement('style');
    st.id = 'actividadEstilo';
    st.textContent =
      '#actividadBarra{position:fixed;top:0;left:0;right:0;height:3px;z-index:3000;pointer-events:none;' +
      'overflow:hidden;opacity:0;transition:opacity .15s}' +
      '#actividadBarra.activa{opacity:1}' +
      '#actividadBarra::before{content:"";position:absolute;top:0;bottom:0;left:-40%;width:40%;' +
      'background:var(--bs-primary,#0d6efd);border-radius:0 3px 3px 0;animation:actividadMover 1.1s ease-in-out infinite}' +
      '@keyframes actividadMover{0%{left:-40%}100%{left:100%}}' +
      '@media (prefers-reduced-motion:reduce){#actividadBarra::before{left:0;width:100%;animation:actividadPulso 1.6s ease-in-out infinite}' +
      '@keyframes actividadPulso{50%{opacity:.35}}}' +
      '.edu-cargando{opacity:.55;cursor:progress;transition:opacity .15s}' +
      '.edu-cargando:not(select):not(input):not(textarea)::before{content:"Cargando…";display:block;' +
      'font-size:.85rem;color:var(--bs-secondary-color,#6c757d);margin-bottom:.25rem}' +
      '#actividadAviso{position:fixed;top:.6rem;left:50%;transform:translateX(-50%);z-index:3001;' +
      'max-width:calc(100% - 1.5rem);padding:.45rem .9rem;border-radius:.5rem;font-size:.85rem;line-height:1.3;' +
      'text-align:center;color:var(--bs-body-color,#212529);background:var(--bs-body-bg,#fff);' +
      'border:1px solid var(--bs-border-color,#dee2e6);box-shadow:0 .25rem .75rem rgba(0,0,0,.2);pointer-events:none;display:none}' +
      '#actividadAviso.visible{display:block}';
    document.head.appendChild(st);
  }

  function crear() {
    if (barra || !document.body) return;
    inyectarEstilo();
    barra = document.createElement('div');
    barra.id = 'actividadBarra';
    barra.setAttribute('aria-hidden', 'true');
    aviso = document.createElement('div');
    aviso.id = 'actividadAviso';
    aviso.setAttribute('role', 'status');
    aviso.setAttribute('aria-live', 'polite');
    document.body.appendChild(barra);
    document.body.appendChild(aviso);
  }

  function mostrarBarra() {
    crear();
    if (!barra) return;
    visible = true;
    barra.classList.add('activa');
  }

  function mostrarAviso(texto) {
    if (!visible || !aviso) return;
    aviso.textContent = texto;
    aviso.classList.add('visible');
  }

  function limpiarTimers() {
    timers.forEach(clearTimeout);
    timers = [];
  }

  function ocultar() {
    limpiarTimers();
    visible = false;
    if (barra) barra.classList.remove('activa');
    if (aviso) aviso.classList.remove('visible');
  }

  function actualizar() {
    var activo = pedidos > 0 || navegando;
    if (activo && !inicio) {
      inicio = Date.now();
      timers.push(setTimeout(mostrarBarra, UMBRAL_MS));
      timers.push(setTimeout(function () {
        mostrarAviso('Está tardando más de lo habitual. Sigue en proceso.');
      }, AVISO_1_MS));
      timers.push(setTimeout(function () {
        mostrarAviso('Sigue en proceso. Si el servidor estaba inactivo, puede llevar hasta un minuto.');
      }, AVISO_2_MS));
    } else if (!activo && inicio) {
      inicio = 0;
      ocultar();
    }
  }

  function empezarNavegacion() {
    navegando = true;
    clearTimeout(timerNavegacion);
    timerNavegacion = setTimeout(function () { navegando = false; actualizar(); }, NAVEGACION_MAX_MS);
    actualizar();
  }

  function terminarNavegacion() {
    navegando = false;
    clearTimeout(timerNavegacion);
    actualizar();
  }

  // --- pedidos fetch() ---------------------------------------------------------------------
  if (typeof window.fetch === 'function') {
    var fetchOriginal = window.fetch.bind(window);
    window.fetch = function (entrada, opciones) {
      if (opciones && opciones.sinAviso) return fetchOriginal(entrada, opciones);
      var listas = elementos(opciones && opciones.cargando);
      marcarCargando(listas);
      pedidos += 1;
      actualizar();
      var fin = function () { pedidos = Math.max(0, pedidos - 1); actualizar(); desmarcarCargando(listas); };
      return fetchOriginal(entrada, opciones).then(
        function (r) { fin(); return r; },
        function (e) { fin(); throw e; }
      );
    };
  }

  // --- navegación por enlaces --------------------------------------------------------------
  document.addEventListener('click', function (e) {
    if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    var a = e.target && e.target.closest ? e.target.closest('a[href]') : null;
    if (!a) return;
    var destino = a.getAttribute('href') || '';
    if (!destino || destino.charAt(0) === '#' || /^(javascript|mailto|tel|sms|blob|data):/i.test(destino)) return;
    if (a.hasAttribute('download') || a.hasAttribute('data-bs-toggle') || a.hasAttribute('data-sin-aviso')) return;
    if (a.target && a.target !== '_self') return;
    var url;
    try { url = new URL(a.href, window.location.href); } catch (err) { return; }
    if (url.origin !== window.location.origin) return;
    if (url.pathname === window.location.pathname && url.search === window.location.search && url.hash) return;
    if (SIN_AVISO.test(url.pathname)) return;
    empezarNavegacion();
  });

  // --- envío de formularios ----------------------------------------------------------------
  document.addEventListener('submit', function (e) {
    var form = e.target;
    if (!form || form.tagName !== 'FORM' || e.defaultPrevented) return;
    if (form.hasAttribute('data-sin-aviso') || (form.target && form.target !== '_self')) return;
    if (SIN_AVISO.test(form.getAttribute('action') || '')) return;
    empezarNavegacion();
  });

  // Volver con "atrás" desde el caché del navegador no recarga la página: se apaga lo que haya quedado.
  window.addEventListener('pageshow', function (e) { if (e.persisted) { pedidos = 0; terminarNavegacion(); } });

  window.EducaAppActividad = {
    empezar: function () { pedidos += 1; actualizar(); },
    terminar: function () { pedidos = Math.max(0, pedidos - 1); actualizar(); },
  };
})();
