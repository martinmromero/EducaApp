/*
 * Selector con búsqueda para listas largas (materias hoy; sirve para cualquier <select>).
 *
 * Se aplica sobre un <select data-smart-select> ya existente: el <select> sigue siendo la fuente de la
 * verdad (valor, eventos 'change', validación, envío del formulario), este script solo dibuja encima un
 * desplegable que muestra primero lo relevante y deja buscar el resto tipeando. Si el script no carga, o
 * el interruptor SELECTORES_INTELIGENTES está apagado, queda el desplegable normal.
 *
 * Cada <option> puede traer:
 *   data-tier   'mias' | 'carrera' | 'resto'  (lo decide el servidor, ver content_visibility.anotar_materias)
 *   data-extra  texto chico debajo del nombre (carrera y origen)
 *
 * Con 12 opciones o menos (EducaAppSmartSelectConfig.umbral) no se toca nada: el desplegable es el de
 * siempre. Por encima del umbral, sin escribir se ven solo "mias" y "carrera"; el resto aparece al tipear
 * (sin importar tildes ni mayúsculas).
 */
window.EducaAppSmartSelect = (function () {
    var cfg = window.EducaAppSmartSelectConfig || { enabled: true, umbral: 12 };
    var MAX_RESULTADOS = 40;
    var TITULOS = { mias: 'Mis materias', carrera: 'De esta carrera', resto: 'Otras materias' };

    function norm(s) { return (s || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase(); }
    function el(tag, cls, text) { var e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; }

    function injectStyle() {
        if (document.getElementById('smartSelectStyle')) return;
        var st = document.createElement('style');
        st.id = 'smartSelectStyle';
        st.textContent =
            '.ss-wrap{position:relative;flex:1 1 auto;min-width:0;width:100%}' +
            '.ss-native{position:absolute;left:0;bottom:0;width:100%;height:1px;opacity:0;pointer-events:none}' +
            '.ss-trigger{width:100%;text-align:left;display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;cursor:pointer}' +
            '.ss-trigger.is-placeholder{color:var(--bs-secondary-color)}' +
            '.ss-trigger:disabled{cursor:not-allowed;opacity:.65}' +
            '.ss-panel{position:absolute;z-index:1060;left:0;right:0;top:100%;margin-top:2px;background:var(--bs-body-bg);color:var(--bs-body-color);' +
            'border:1px solid var(--bs-border-color);border-radius:.375rem;box-shadow:0 .5rem 1rem rgba(0,0,0,.25);padding:.5rem}' +
            '.ss-list{max-height:260px;overflow-y:auto;margin-top:.5rem}' +
            '.ss-title{font-size:.72rem;text-transform:uppercase;letter-spacing:.05em;color:var(--bs-secondary-color);padding:.35rem .5rem .15rem}' +
            '.ss-item{padding:.35rem .5rem;border-radius:.25rem;cursor:pointer}' +
            '.ss-item small{display:block;color:var(--bs-secondary-color);line-height:1.15}' +
            '.ss-item:hover,.ss-item.is-active{background:var(--bs-tertiary-bg)}' +
            '.ss-item.is-selected{font-weight:600}' +
            '.ss-hint{font-size:.85rem;color:var(--bs-secondary-color);padding:.35rem .5rem}';
        document.head.appendChild(st);
    }

    function enhance(sel) {
        if (sel.dataset.ssReady) return null;
        var base = Array.from(sel.querySelectorAll('option')).filter(function (o) { return o.value !== ''; });
        if (base.length <= cfg.umbral) return null;   // lista corta: el desplegable de siempre
        sel.dataset.ssReady = '1';
        injectStyle();

        var placeholderOpt = Array.from(sel.querySelectorAll('option')).filter(function (o) { return o.value === ''; })[0];
        var placeholder = (placeholderOpt && placeholderOpt.textContent.trim()) || 'Seleccionar';

        var wrap = el('div', 'ss-wrap');
        var trigger = el('button', (sel.className || 'form-select') + ' ss-trigger');
        trigger.type = 'button';
        trigger.setAttribute('aria-haspopup', 'listbox');
        trigger.setAttribute('aria-expanded', 'false');
        var panel = el('div', 'ss-panel');
        panel.hidden = true;
        var search = el('input', 'form-control form-control-sm');
        search.type = 'search';
        search.autocomplete = 'off';
        search.placeholder = 'Escribir para buscar…';
        search.setAttribute('aria-label', 'Buscar en la lista');
        var list = el('div', 'ss-list');
        list.setAttribute('role', 'listbox');
        panel.appendChild(search);
        panel.appendChild(list);

        sel.parentNode.insertBefore(wrap, sel);
        wrap.appendChild(trigger);
        wrap.appendChild(panel);
        wrap.appendChild(sel);
        sel.classList.add('ss-native');
        sel.tabIndex = -1;
        sel.setAttribute('aria-hidden', 'true');

        // Los <label for="..."> del select llevan al botón.
        if (sel.id) {
            document.querySelectorAll('label[for="' + sel.id + '"]').forEach(function (lb) {
                lb.addEventListener('click', function (e) { e.preventDefault(); trigger.focus(); });
            });
        }

        var items = [];      // [{opt, texto, extra, tier, hayTexto}]
        var activo = -1;

        function leerOpciones() {
            items = Array.from(sel.querySelectorAll('option')).filter(function (o) { return o.value !== ''; }).map(function (o) {
                var extra = o.dataset.extra || '';
                var nombre = o.dataset.nombre || o.textContent.trim();
                return { opt: o, texto: nombre, extra: extra, tier: o.dataset.tier || 'resto', buscable: norm(nombre + ' ' + extra) };
            });
        }

        function refrescarBoton() {
            var o = sel.options[sel.selectedIndex];
            var hay = o && o.value !== '';
            trigger.textContent = hay ? o.textContent.trim() : placeholder;
            trigger.classList.toggle('is-placeholder', !hay);
            trigger.disabled = sel.disabled;
        }

        function filas(query) {
            var q = norm(query.trim());
            var todasVisibles = items.length <= cfg.umbral;
            var grupos = { mias: [], carrera: [], resto: [] };
            var restoOculto = 0;
            items.forEach(function (it) {
                var coincide = !q || it.buscable.indexOf(q) !== -1;
                if (q) { if (coincide) grupos[it.tier in grupos ? it.tier : 'resto'].push(it); return; }
                if (todasVisibles || it.tier === 'mias' || it.tier === 'carrera') grupos[it.tier in grupos ? it.tier : 'resto'].push(it);
                else restoOculto++;
            });
            return { grupos: grupos, restoOculto: restoOculto, q: q };
        }

        function render() {
            var f = filas(search.value);
            list.innerHTML = '';
            var total = 0;
            var gruposConDatos = ['mias', 'carrera', 'resto'].filter(function (k) { return f.grupos[k].length; });
            gruposConDatos.forEach(function (k) {
                if (gruposConDatos.length > 1 || k !== 'resto' || !f.q) list.appendChild(el('div', 'ss-title', TITULOS[k]));
                f.grupos[k].forEach(function (it) {
                    if (total >= MAX_RESULTADOS) return;
                    total++;
                    var row = el('div', 'ss-item');
                    row.setAttribute('role', 'option');
                    row.dataset.valor = it.opt.value;
                    row.appendChild(document.createTextNode(it.texto));
                    if (it.extra) row.appendChild(el('small', null, it.extra));
                    if (it.opt.value === sel.value) { row.classList.add('is-selected'); row.setAttribute('aria-selected', 'true'); }
                    row.addEventListener('mousedown', function (e) { e.preventDefault(); elegir(it.opt.value); });
                    list.appendChild(row);
                });
            });
            if (f.q && !total) list.appendChild(el('div', 'ss-hint', 'No hay coincidencias.'));
            else if (f.q && total >= MAX_RESULTADOS) list.appendChild(el('div', 'ss-hint', 'Hay más resultados: seguir escribiendo para acotar.'));
            else if (!f.q && f.restoOculto) list.appendChild(el('div', 'ss-hint', 'Escribir para buscar entre ' + f.restoOculto + (f.restoOculto === 1 ? ' opción más.' : ' opciones más.')));
            activo = -1;
        }

        function filasDom() { return Array.from(list.querySelectorAll('.ss-item')); }
        function mover(d) {
            var f = filasDom();
            if (!f.length) return;
            activo = (activo + d + f.length) % f.length;
            f.forEach(function (r, i) { r.classList.toggle('is-active', i === activo); });
            f[activo].scrollIntoView({ block: 'nearest' });
        }

        function abrir() {
            if (sel.disabled || !panel.hidden) return;
            leerOpciones();
            search.value = '';
            render();
            panel.hidden = false;
            trigger.setAttribute('aria-expanded', 'true');
            search.focus();
        }
        function cerrar(devolverFoco) {
            if (panel.hidden) return;
            panel.hidden = true;
            trigger.setAttribute('aria-expanded', 'false');
            if (devolverFoco) trigger.focus();
        }
        function elegir(valor) {
            sel.value = valor;                      // setter parcheado más abajo: refresca el botón
            sel.dispatchEvent(new Event('change', { bubbles: true }));
            cerrar(true);
        }

        trigger.addEventListener('click', function () { panel.hidden ? abrir() : cerrar(true); });
        trigger.addEventListener('keydown', function (e) {
            if (e.key === 'ArrowDown' || e.key === 'ArrowUp') { e.preventDefault(); abrir(); }
        });
        search.addEventListener('input', render);
        search.addEventListener('keydown', function (e) {
            if (e.key === 'ArrowDown') { e.preventDefault(); mover(1); }
            else if (e.key === 'ArrowUp') { e.preventDefault(); mover(-1); }
            else if (e.key === 'Enter') {
                e.preventDefault();
                var f = filasDom();
                var fila = activo >= 0 ? f[activo] : (f.length === 1 ? f[0] : null);
                if (fila) elegir(fila.dataset.valor);
            } else if (e.key === 'Escape') { e.preventDefault(); cerrar(true); }
            else if (e.key === 'Tab') { cerrar(false); }
        });
        document.addEventListener('mousedown', function (e) { if (!wrap.contains(e.target)) cerrar(false); });

        // Otros scripts asignan sel.value directamente (precarga desde una plantilla, restaurar un borrador):
        // el botón tiene que enterarse.
        var desc = Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, 'value');
        Object.defineProperty(sel, 'value', {
            configurable: true,
            get: function () { return desc.get.call(sel); },
            set: function (v) { desc.set.call(sel, v); refrescarBoton(); },
        });
        sel.addEventListener('change', refrescarBoton);
        // Y cuando reconstruyen las opciones (por ejemplo al reordenar por carrera).
        new MutationObserver(function () { leerOpciones(); refrescarBoton(); if (!panel.hidden) render(); })
            .observe(sel, { childList: true, subtree: true, attributes: true, attributeFilter: ['disabled', 'data-tier'] });

        leerOpciones();
        refrescarBoton();
        return { trigger: trigger, panel: panel };
    }

    function initAll(root) {
        if (!cfg.enabled) return;
        (root || document).querySelectorAll('select[data-smart-select]').forEach(enhance);
    }

    function boot() { initAll(document); }
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();

    return { enhance: enhance, initAll: initAll };
})();
