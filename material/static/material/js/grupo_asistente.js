// grupo_asistente.js
// Asistente para crear un grupo de confianza o ajustar uno existente (material/groups/grupo_asistente.html).
// Un único envío al final: el servidor crea el grupo, manda las invitaciones y sincroniza lo compartido.

function _onDomReady(fn) {
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', fn);
    } else {
        fn();
    }
}

_onDomReady(function () {
    var CFG = window.EducaAppGrupoWizardConfig || { esNuevo: true };
    var form = document.getElementById('grupoWizardForm');
    var nameInput = document.getElementById('id_grupo_name');

    function marcados(nombreCampo) {
        return Array.from(form.querySelectorAll('input[name="' + nombreCampo + '"]:checked'));
    }

    // ── Paso 1: buscar cuentas por nombre de usuario (no se lista a todo el sistema) ──
    var buscar = document.getElementById('buscarInvitado');
    var resultados = document.getElementById('resultadosInvitado');
    var elegidos = document.getElementById('invitadosElegidos');
    var temporizador = null;
    var secuencia = 0;

    function yaElegido(id) { return !!elegidos.querySelector('input[value="' + id + '"]'); }

    function agregarInvitado(u) {
        if (yaElegido(u.id)) return;
        var chip = document.createElement('span');
        chip.className = 'badge text-bg-primary d-inline-flex align-items-center gap-2 py-2 px-3';
        var input = document.createElement('input');
        input.type = 'hidden'; input.name = 'invitar'; input.value = u.id; input.dataset.nombre = u.username;
        var texto = document.createElement('span');
        texto.textContent = u.username;
        var quitar = document.createElement('button');
        quitar.type = 'button'; quitar.className = 'btn-close btn-close-white'; quitar.style.fontSize = '.6rem';
        quitar.setAttribute('aria-label', 'Quitar a ' + u.username);
        quitar.addEventListener('click', function () { chip.remove(); });
        chip.appendChild(input); chip.appendChild(texto); chip.appendChild(quitar);
        elegidos.appendChild(chip);
    }

    function mostrarResultados(lista, mensaje) {
        resultados.innerHTML = '';
        if (mensaje) {
            var p = document.createElement('div');
            p.className = 'list-group-item small text-muted';
            p.textContent = mensaje;
            resultados.appendChild(p);
            return;
        }
        lista.forEach(function (u) {
            var b = document.createElement('button');
            b.type = 'button'; b.className = 'list-group-item list-group-item-action';
            b.textContent = u.username;
            b.disabled = yaElegido(u.id);
            b.addEventListener('click', function () {
                agregarInvitado(u);
                buscar.value = '';
                resultados.innerHTML = '';
                buscar.focus();
            });
            resultados.appendChild(b);
        });
    }

    if (buscar) {
        buscar.addEventListener('input', function () {
            clearTimeout(temporizador);
            var q = buscar.value.trim();
            if (q.length < 3) { resultados.innerHTML = ''; return; }
            temporizador = setTimeout(function () {
                var mia = ++secuencia;
                var url = CFG.urlBuscar + '?q=' + encodeURIComponent(q) + (CFG.grupoId ? '&grupo=' + encodeURIComponent(CFG.grupoId) : '');
                fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
                    .then(function (r) { return r.json(); })
                    .then(function (data) {
                        if (mia !== secuencia) return;
                        mostrarResultados(data.usuarios, data.usuarios.length ? '' : 'No hay cuentas que coincidan.');
                    })
                    .catch(function () { mostrarResultados([], 'No se pudo buscar. Probar de nuevo.'); });
            }, 250);
        });
        // Enter en el buscador no debe enviar el formulario completo.
        buscar.addEventListener('keydown', function (e) { if (e.key === 'Enter') e.preventDefault(); });
    }

    // ── Todo / Ninguno en las materias ────────────────────────────────────
    document.querySelectorAll('[data-marcar]').forEach(function (boton) {
        boton.addEventListener('click', function () {
            var valor = boton.dataset.valor === '1';
            form.querySelectorAll('input[name="' + boton.dataset.marcar + '"]').forEach(function (cb) { cb.checked = valor; });
        });
    });

    function validateStep(n) {
        if (n === 1 && CFG.esNuevo && !nameInput.value.trim()) {
            window.EducaAppToast.show('El grupo necesita un nombre para continuar.', { variant: 'warning' });
            nameInput.focus();
            return false;
        }
        return true;
    }

    // ── Paso 4: resumen ───────────────────────────────────────────────────
    function lista(items, vacio) {
        if (!items.length) return '<span class="text-muted">' + window.EducaAppEscape(vacio) + '</span>';
        return '<ul class="mb-0 ps-3">' + items.map(function (t) { return '<li>' + window.EducaAppEscape(t) + '</li>'; }).join('') + '</ul>';
    }

    function renderSummary() {
        var box = document.getElementById('wizSummary');
        var html = '<dl class="row mb-0">';
        if (CFG.esNuevo) {
            html += '<dt class="col-sm-4">Grupo</dt><dd class="col-sm-8">' + window.EducaAppEscape(nameInput.value.trim() || '-') + '</dd>';
        }
        html += '<dt class="col-sm-4">Se invita a</dt><dd class="col-sm-8">' +
            lista(Array.from(elegidos.querySelectorAll('input[name="invitar"]')).map(function (i) { return i.dataset.nombre; }), 'Nadie por ahora') + '</dd>';
        [['materias', 'Materias'], ['rubricas', 'Rúbricas'], ['plantillas', 'Plantillas de examen'], ['formatos', 'Formatos de impresión']].forEach(function (par) {
            var campo = par[0];
            var todos = Array.from(form.querySelectorAll('input[name="' + campo + '"]'));
            var sel = todos.filter(function (cb) { return cb.checked; }).map(function (cb) { return cb.dataset.nombre; });
            var dejan = todos.filter(function (cb) { return !cb.checked && cb.dataset.inicial === '1'; }).map(function (cb) { return cb.dataset.nombre; });
            html += '<dt class="col-sm-4">' + par[1] + '</dt><dd class="col-sm-8">' + lista(sel, 'Ninguna');
            if (dejan.length) {
                html += '<div class="small text-danger mt-1">Dejan de compartirse: ' + window.EducaAppEscape(dejan.join(', ')) + '</div>';
            }
            html += '</dd>';
        });
        box.innerHTML = html + '</dl>';
    }

    var wizardCtrl = window.EducaAppWizard.init({
        totalSteps: 4,
        onValidateStep: validateStep,
        onEnterFinalStep: renderSummary,
    });
    wizardCtrl.goToStep(1);
});
