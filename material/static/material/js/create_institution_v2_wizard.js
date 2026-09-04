// create_institution_v2_wizard.js
// Asistente paso a paso para "Nueva Institución" (material/institutions_v2/create_wizard.html).
// Postea nativo (method="post", sin fetch) al mismo create_institution_v2 de
// siempre — toda la validación real (nombre duplicado, logo, formsets de
// sedes/facultades) vive ahí, esta pantalla solo arma el mismo formset
// dinámico que ya usa institutions_v2/create.html (clonar fila + reindexar).

// document.addEventListener('DOMContentLoaded', fn) a secas no alcanza: si
// el evento ya disparó para cuando este script corre, el callback nunca se
// ejecuta sin ningún error visible (encontrado en create_exam_template_wizard.js).
function _onDomReady(fn) {
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', fn);
    } else {
        fn();
    }
}

_onDomReady(function () {
    var nameInput = document.getElementById('id_name');
    var siglaInput = document.getElementById('id_sigla');
    var logoInput = document.getElementById('id_logo');
    var logoErrorBox = document.getElementById('wizLogoError');

    // ── Logo: mismo criterio de validación client-side que institutions_v2/create.html ──
    if (logoInput) {
        logoInput.addEventListener('change', function () {
            logoErrorBox.innerHTML = '';
            logoInput.classList.remove('is-invalid');
            var file = logoInput.files[0];
            if (!file) return;
            var validTypes = ['image/jpeg', 'image/png', 'image/svg+xml'];
            if (!validTypes.includes(file.type)) {
                showLogoError('Formato no válido (solo JPG, PNG, SVG).');
            } else if (file.size > 2 * 1024 * 1024) {
                showLogoError('El tamaño máximo es 2MB.');
            }
        });
    }
    function showLogoError(message) {
        logoErrorBox.innerHTML = '<div class="alert alert-danger py-2 px-3 mb-0 small mt-2">' + message + '</div>';
        logoInput.classList.add('is-invalid');
    }

    // ── Formsets dinámicos: clonar fila + reindexar (mismo patrón que
    // institutions_v2/create.html::setupFormset, adaptado a las clases de acá) ──
    function setupFormset(prefix, containerId, addButtonId, rowClass, removeClass) {
        var container = document.getElementById(containerId);
        var addButton = document.getElementById(addButtonId);
        var totalForms = document.getElementById('id_' + prefix + '-TOTAL_FORMS');

        function updateIndices() {
            var rows = container.querySelectorAll('.' + rowClass);
            rows.forEach(function (row, index) {
                row.querySelectorAll('input').forEach(function (input) {
                    input.name = input.name.replace(new RegExp(prefix + '-\\d+-'), prefix + '-' + index + '-');
                    input.id = input.id.replace(new RegExp(prefix + '-\\d+-'), prefix + '-' + index + '-');
                });
            });
            totalForms.value = rows.length;
        }

        container.addEventListener('click', async function (e) {
            var removeBtn = e.target.closest('.' + removeClass);
            if (!removeBtn) return;
            var row = removeBtn.closest('.' + rowClass);
            var isEmpty = !row.querySelector('input[type="text"]').value.trim();
            if (isEmpty || await window.EducaAppModal.confirm('¿Eliminar esta entrada?', { title: 'Eliminar entrada', variant: 'warning', okLabel: 'Eliminar' })) {
                row.remove();
                updateIndices();
            }
        });

        addButton.addEventListener('click', function () {
            var count = parseInt(totalForms.value, 10);
            var template = container.querySelector('.' + rowClass);
            var newRow = template.cloneNode(true);
            newRow.innerHTML = newRow.innerHTML.replace(new RegExp(prefix + '-\\d+-', 'g'), prefix + '-' + count + '-');
            newRow.querySelector('input[type="text"]').value = '';
            container.appendChild(newRow);
            totalForms.value = count + 1;
        });
    }

    setupFormset('campus', 'wizCampusContainer', 'wizAddCampus', 'campus-entry', 'wiz-remove-campus');
    setupFormset('faculty', 'wizFacultyContainer', 'wizAddFaculty', 'faculty-entry', 'wiz-remove-faculty');

    // ── Validación por paso ────────────────────────────────────────────
    function validateStep(n) {
        if (n === 1) {
            if (!nameInput.value.trim() || nameInput.value.trim().length < 2) {
                nameInput.reportValidity ? nameInput.reportValidity() : alert('El nombre debe tener al menos 2 caracteres.');
                return false;
            }
            if (logoInput.classList.contains('is-invalid')) {
                alert('Corregí el logo antes de continuar, o quitalo.');
                return false;
            }
        }
        return true;
    }

    function nonEmptyValues(containerId) {
        return Array.from(document.getElementById(containerId).querySelectorAll('input[type="text"]'))
            .map(function (i) { return i.value.trim(); })
            .filter(function (v) { return v; });
    }

    function renderSummary() {
        var box = document.getElementById('wizSummary');
        if (!box) return;
        var campuses = nonEmptyValues('wizCampusContainer');
        var faculties = nonEmptyValues('wizFacultyContainer');
        box.innerHTML =
            '<dl class="row mb-0">' +
            '<dt class="col-sm-4">Nombre</dt><dd class="col-sm-8">' + (nameInput.value.trim() || '-') + '</dd>' +
            '<dt class="col-sm-4">Sigla</dt><dd class="col-sm-8">' + (siglaInput.value.trim() || '-') + '</dd>' +
            '<dt class="col-sm-4">Logo</dt><dd class="col-sm-8">' + (logoInput.files[0] ? logoInput.files[0].name : 'sin logo') + '</dd>' +
            '<dt class="col-sm-4">Sedes</dt><dd class="col-sm-8">' + (campuses.length ? campuses.join(', ') : 'ninguna') + '</dd>' +
            '<dt class="col-sm-4">Facultades</dt><dd class="col-sm-8">' + (faculties.length ? faculties.join(', ') : 'ninguna') + '</dd>' +
            '</dl>';
    }

    var wizardCtrl = window.EducaAppWizard.init({
        totalSteps: 4,
        onValidateStep: validateStep,
        onEnterFinalStep: renderSummary,
    });

    // ── Backup a sessionStorage (mismo motor que los otros 3 wizards, ver
    // wizard_draft.js). El logo (input type="file") NO se puede guardar en
    // sessionStorage — se pierde si hay que recuperar un borrador, el resto
    // de los campos sí. ───────────────────────────────────────────────────
    var draft = window.EducaAppWizardDraft.init('educaapp_institution_wizard_draft');
    var institutionForm = document.getElementById('institutionWizardForm');

    function saveDraft() {
        draft.save({
            name: nameInput.value,
            sigla: siglaInput.value,
            campuses: nonEmptyValues('wizCampusContainer'),
            faculties: nonEmptyValues('wizFacultyContainer'),
        });
    }
    institutionForm.addEventListener('change', saveDraft);
    institutionForm.addEventListener('input', saveDraft);

    // Agrega filas hasta tener `count` en el formset (usa el botón "Agregar"
    // real para que TOTAL_FORMS y el reindexado queden consistentes) y
    // devuelve las filas ya presentes, en orden.
    function ensureFormsetRows(containerId, addButtonId, rowClass, count) {
        var container = document.getElementById(containerId);
        var addButton = document.getElementById(addButtonId);
        while (container.querySelectorAll('.' + rowClass).length < count) {
            addButton.click();
        }
        return Array.from(container.querySelectorAll('.' + rowClass));
    }

    function restoreDraft() {
        var saved = draft.load();
        if (!saved || !saved.name) return;

        draft.confirmRestore('Encontramos una institución sin terminar de una sesión anterior. ¿Querés recuperarla? (El logo, si habías elegido uno, se pierde igual — hay que volver a elegirlo.)').then(function (quiere) {
            if (!quiere) { draft.clear(); return; }

            nameInput.value = saved.name || '';
            siglaInput.value = saved.sigla || '';

            var campusRows = ensureFormsetRows('wizCampusContainer', 'wizAddCampus', 'campus-entry', (saved.campuses || []).length || 1);
            (saved.campuses || []).forEach(function (name, i) {
                if (campusRows[i]) campusRows[i].querySelector('input[type="text"]').value = name;
            });

            var facultyRows = ensureFormsetRows('wizFacultyContainer', 'wizAddFaculty', 'faculty-entry', (saved.faculties || []).length || 1);
            (saved.faculties || []).forEach(function (name, i) {
                if (facultyRows[i]) facultyRows[i].querySelector('input[type="text"]').value = name;
            });

            // goToStep(4) no alcanza: el motor solo deja saltar a un paso
            // <= maxStepReached, que sigue en 1 sin haber pasado por
            // goNext() en esta carga (ver wizard_draft.js).
            wizardCtrl.goNext();
            wizardCtrl.goNext();
            wizardCtrl.goNext();
        });
    }

    institutionForm.addEventListener('submit', function () { draft.clear(); });

    wizardCtrl.goToStep(1);
    restoreDraft();
});
