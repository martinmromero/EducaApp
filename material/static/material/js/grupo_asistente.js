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

    // ── Paso 1: filtrar la lista de docentes por tipeo ───────────────────
    var filtro = document.getElementById('filtroInvitables');
    if (filtro) {
        filtro.addEventListener('input', function () {
            var q = filtro.value.trim().toLowerCase();
            document.querySelectorAll('#listaInvitables .wiz-item').forEach(function (fila) {
                fila.classList.toggle('is-hidden-by-filter', !!q && fila.dataset.texto.indexOf(q) === -1);
            });
        });
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
            lista(marcados('invitar').map(function (cb) { return cb.dataset.nombre; }), 'Nadie por ahora') + '</dd>';
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
