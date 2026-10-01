/*
 * Vista configurable de un listado: oculta y reordena las columnas de la
 * tabla según la preferencia del usuario y maneja el panel "Columnas".
 * El lado servidor está en material/list_columns.py.
 *
 * Convención que debe respetar la página:
 * - <table class="lc-table"> con data-col="<clave>" en cada <th> y <td> de
 *   las columnas configurables, y data-col-fixed="first" / "last" en las que
 *   no se mueven (casilla de selección y Acciones).
 * - La configuración efectiva en <script type="application/json" id="lcCfg">.
 * - El panel de components/_list_columns_button.html.
 * - El texto largo dentro de <div class="lc-text">, que se recorta por
 *   líneas con CSS (ver static/css/styles.css, sección "Vista configurable").
 *
 * Uso: EducaAppListColumns.init({ url: '/preferencias-listado/preguntas/' }).
 */
(function () {
  'use strict';

  function getCookie(name) {
    var m = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
    return m ? decodeURIComponent(m[2]) : null;
  }

  function csrfToken() {
    var input = document.querySelector('input[name="csrfmiddlewaretoken"]');
    return input ? input.value : getCookie('csrftoken');
  }

  function init(opts) {
    var table = document.querySelector('table.lc-table');
    var btn = document.getElementById('listColumnsBtn');
    var cfgEl = document.getElementById('lcCfg');
    var preStyle = document.getElementById('lcPreStyle');
    if (!cfgEl) return null;
    if (!table) {
      // Sin filas no hay nada que configurar (listado vacío o con filtros
      // que no devuelven nada).
      if (btn) btn.classList.add('d-none');
      return null;
    }

    var cfg = JSON.parse(cfgEl.textContent);
    var listEl = document.getElementById('listColumnsList');
    var linesWrap = document.getElementById('listColumnsLinesWrap');
    var linesSeg = document.getElementById('listColumnsLines');
    var resetBtn = document.getElementById('listColumnsReset');
    var presentKeys = {};
    table.querySelectorAll('thead [data-col]').forEach(function (th) { presentKeys[th.dataset.col] = true; });

    var state = {};
    function loadState(c) {
      state.order = c.columns.map(function (x) { return x.key; });
      state.visible = {};
      c.columns.forEach(function (x) { state.visible[x.key] = x.visible; });
      state.lines = c.lines;
    }
    loadState(cfg);

    var labels = {};
    cfg.columns.forEach(function (c) { labels[c.key] = c.label; });

    /* ── Tabla ─────────────────────────────────────────────────────────── */
    function applyRow(row) {
      var cells = Array.prototype.slice.call(row.children);
      var byCol = {};
      var first = null, last = null, loose = [];
      cells.forEach(function (c) {
        if (c.dataset.colFixed === 'first') first = c;
        else if (c.dataset.colFixed === 'last') last = c;
        else if (c.dataset.col) byCol[c.dataset.col] = c;
        else loose.push(c);
      });
      // Fila sin celdas configurables (ej. el "no hay resultados" con
      // colspan): no se toca.
      if (!Object.keys(byCol).length) return;
      var seq = [];
      if (first) seq.push(first);
      state.order.forEach(function (k) { if (byCol[k]) seq.push(byCol[k]); });
      loose.forEach(function (c) { seq.push(c); });
      if (last) seq.push(last);
      seq.forEach(function (c) { row.appendChild(c); });
      Object.keys(byCol).forEach(function (k) {
        byCol[k].classList.toggle('lc-hidden', !state.visible[k]);
      });
    }

    function markOverflow() {
      table.querySelectorAll('.lc-text').forEach(function (el) {
        if (el.classList.contains('lc-expanded')) return;
        var clipped = state.lines !== 0 && el.scrollHeight > el.clientHeight + 1;
        el.classList.toggle('lc-more', clipped);
        if (clipped) el.setAttribute('role', 'button'); else el.removeAttribute('role');
        el.tabIndex = clipped ? 0 : -1;
      });
    }

    function applyTable() {
      table.querySelectorAll('tr').forEach(applyRow);
      table.className = table.className.replace(/\blc-lines-\d\b/g, '').trim() + ' lc-lines-' + state.lines;
      requestAnimationFrame(markOverflow);
    }

    /* ── Panel ─────────────────────────────────────────────────────────── */
    function fixedRow(text, hint) {
      var li = document.createElement('div');
      li.className = 'lc-row lc-row-fixed';
      li.innerHTML = '<span class="lc-grip"><i class="bi bi-lock" aria-hidden="true"></i></span>' +
        '<input type="checkbox" class="form-check-input" checked disabled aria-label="' + text + ' (fija)">' +
        '<span class="flex-grow-1"></span><span class="small text-body-secondary"></span>';
      li.children[2].textContent = text;
      li.children[3].textContent = hint;
      return li;
    }

    function move(i, d) {
      var j = i + d;
      var shown = state.order.filter(function (k) { return presentKeys[k]; });
      if (j < 0 || j >= shown.length) return;
      var a = state.order.indexOf(shown[i]);
      var b = state.order.indexOf(shown[j]);
      var t = state.order[a]; state.order[a] = state.order[b]; state.order[b] = t;
      changed();
      renderPanel();
      var again = listEl.querySelector('[data-move="' + (d < 0 ? 'up' : 'down') + '"][data-pos="' + j + '"]');
      if (again) again.focus();
    }

    function renderPanel() {
      var shown = state.order.filter(function (k) { return presentKeys[k]; });
      listEl.innerHTML = '';
      listEl.appendChild(fixedRow('Casilla de selección', 'siempre primera'));
      shown.forEach(function (k, i) {
        var row = document.createElement('div');
        row.className = 'lc-row';
        row.draggable = true;
        row.dataset.key = k;
        row.innerHTML =
          '<span class="lc-grip lc-drag" aria-hidden="true"><i class="bi bi-grip-vertical"></i></span>' +
          '<input type="checkbox" class="form-check-input">' +
          '<span class="flex-grow-1"></span>' +
          '<button type="button" class="btn btn-sm btn-outline-secondary lc-ib" data-move="up" aria-label="Subir"><i class="bi bi-arrow-up" aria-hidden="true"></i></button>' +
          '<button type="button" class="btn btn-sm btn-outline-secondary lc-ib" data-move="down" aria-label="Bajar"><i class="bi bi-arrow-down" aria-hidden="true"></i></button>';
        var cb = row.querySelector('input');
        cb.checked = !!state.visible[k];
        cb.setAttribute('aria-label', 'Mostrar ' + labels[k]);
        row.children[2].textContent = labels[k];
        var up = row.querySelector('[data-move="up"]');
        var down = row.querySelector('[data-move="down"]');
        up.dataset.pos = down.dataset.pos = i;
        listEl.appendChild(row);
      });
      listEl.appendChild(fixedRow('Acciones', 'siempre última'));

      if (linesWrap) {
        linesWrap.classList.toggle('d-none', !cfg.text_column);
        linesSeg.querySelectorAll('button').forEach(function (b) {
          var on = Number(b.dataset.lines) === state.lines;
          b.classList.toggle('active', on);
          b.setAttribute('aria-pressed', on ? 'true' : 'false');
        });
      }
    }

    /* ── Guardado ──────────────────────────────────────────────────────── */
    var timer = null;
    function post(body) {
      return fetch(opts.url, {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken() || '' },
        body: JSON.stringify(body),
      }).then(function (r) {
        return r.json().then(function (data) { return { ok: r.ok && data.ok, data: data }; });
      });
    }
    function fail(msg) {
      if (window.EducaAppToast) window.EducaAppToast.show(msg || 'No se pudo guardar la vista del listado', { variant: 'danger' });
    }
    function changed() {
      applyTable();
      clearTimeout(timer);
      timer = setTimeout(function () {
        post({
          order: state.order,
          visible: state.order.filter(function (k) { return state.visible[k]; }),
          lines: state.lines,
        }).then(function (res) { if (!res.ok) fail(res.data && res.data.error); })
          .catch(function () { fail(); });
      }, 400);
    }

    /* ── Eventos ───────────────────────────────────────────────────────── */
    listEl.addEventListener('click', function (e) {
      var b = e.target.closest('button[data-move]');
      if (!b) return;
      move(Number(b.dataset.pos), b.dataset.move === 'up' ? -1 : 1);
    });
    listEl.addEventListener('change', function (e) {
      var row = e.target.closest('.lc-row[data-key]');
      if (!row) return;
      var on = e.target.checked;
      var visibleCount = state.order.filter(function (k) { return presentKeys[k] && state.visible[k]; }).length;
      if (!on && visibleCount <= 1) {
        e.target.checked = true;
        if (window.EducaAppToast) window.EducaAppToast.show('Tiene que quedar al menos una columna visible', { variant: 'warning' });
        return;
      }
      state.visible[row.dataset.key] = on;
      changed();
    });

    var dragKey = null;
    listEl.addEventListener('dragstart', function (e) {
      var row = e.target.closest('.lc-row[data-key]');
      if (!row) return;
      dragKey = row.dataset.key;
      e.dataTransfer.effectAllowed = 'move';
      e.dataTransfer.setData('text/plain', dragKey);
    });
    listEl.addEventListener('dragover', function (e) {
      if (dragKey) e.preventDefault();
    });
    listEl.addEventListener('drop', function (e) {
      var row = e.target.closest('.lc-row[data-key]');
      if (!row || !dragKey) return;
      e.preventDefault();
      var from = state.order.indexOf(dragKey);
      var to = state.order.indexOf(row.dataset.key);
      dragKey = null;
      if (from < 0 || to < 0 || from === to) return;
      state.order.splice(to, 0, state.order.splice(from, 1)[0]);
      changed();
      renderPanel();
    });
    listEl.addEventListener('dragend', function () { dragKey = null; });

    if (linesSeg) {
      linesSeg.addEventListener('click', function (e) {
        var b = e.target.closest('button[data-lines]');
        if (!b) return;
        state.lines = Number(b.dataset.lines);
        table.querySelectorAll('.lc-text.lc-expanded').forEach(function (el) { el.classList.remove('lc-expanded'); });
        changed();
        renderPanel();
      });
    }

    if (resetBtn) {
      resetBtn.addEventListener('click', function () {
        clearTimeout(timer);
        post({ reset: true }).then(function (res) {
          if (!res.ok) { fail(res.data && res.data.error); return; }
          loadState(res.data.config);
          applyTable();
          renderPanel();
        }).catch(function () { fail(); });
      });
    }

    // Clic (o Enter/Espacio) en un texto recortado: lo expande o contrae.
    function toggleText(el) {
      if (!el || !el.classList.contains('lc-text')) return;
      if (!el.classList.contains('lc-more') && !el.classList.contains('lc-expanded')) return;
      var open = el.classList.toggle('lc-expanded');
      el.setAttribute('aria-expanded', open ? 'true' : 'false');
      if (!open) requestAnimationFrame(markOverflow);
    }
    table.addEventListener('click', function (e) {
      if (e.target.closest('a, button, input, label')) return;
      toggleText(e.target.closest('.lc-text'));
    });
    table.addEventListener('keydown', function (e) {
      if (e.key !== 'Enter' && e.key !== ' ') return;
      var el = e.target.closest('.lc-text');
      if (!el) return;
      e.preventDefault();
      toggleText(el);
    });

    var resizeTimer = null;
    window.addEventListener('resize', function () {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(markOverflow, 150);
    });

    // Las fuentes web y las imágenes cambian el alto del texto: se vuelve a
    // medir qué textos quedaron recortados cuando terminan de cargar.
    window.addEventListener('load', markOverflow);
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(markOverflow);

    applyTable();
    renderPanel();
    // Ya con las clases lc-hidden puestas, el CSS provisorio del servidor
    // (que evitaba el parpadeo) sobra.
    if (preStyle) preStyle.remove();
    return applyTable;
  }

  // Listados que repintan sus filas por AJAX (ej. materias) tienen que volver
  // a aplicar la vista sobre las filas nuevas: EducaAppListColumns.reapply().
  var current = null;

  window.EducaAppListColumns = {
    init: function (opts) { current = init(opts) || null; },
    reapply: function () { if (current) current(); },
  };
})();
