// create_exam_template_wizard.js
// Asistente paso a paso para "Plantilla de Examen" (material/exams/create_exam_template_wizard.html).
// Postea al mismo create_exam_template de siempre — toda la validación real
// (institution/faculty/career/subject obligatorias, resto opcional) vive en
// ExamTemplateForm, acá solo se arma la cascada institución→facultad→carrera→sede
// y el listado de resultados de aprendizaje según la materia elegida.

// No alcanza con document.addEventListener('DOMContentLoaded', fn) a secas:
// si el evento ya disparó para cuando este script corre (script al final del
// body, carga lenta, bfcache, o navegación programática), el callback nunca
// se ejecuta — sin ningún error visible, silenciosamente no pasa nada. Se
// detectó así: el asistente completo funcionaba (stepper, cascadas) pero el
// botón final "Crear plantilla" no hacía nada, sin excepción en consola.
function _onDomReady(fn) {
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', fn);
    } else {
        fn();
    }
}

_onDomReady(function () {
    var CFG = window.EducaAppTemplateWizardConfig || { urls: {} };

    var institutionSelect = document.getElementById('id_institution');
    var facultySelect = document.getElementById('id_faculty');
    var careerSelect = document.getElementById('id_career');
    var campusSelect = document.getElementById('id_campus');
    var subjectSelect = document.getElementById('id_subject');
    var outcomesEmpty = document.getElementById('wizOutcomesEmpty');
    var outcomesList = document.getElementById('wizOutcomesList');
    var outcomesCreateLink = document.getElementById('wizOutcomesCreateLink');
    var nameInput = document.getElementById('id_name');
    var addCampusToggle = document.getElementById('wizAddCampusToggle');

    function resetSelect(select, placeholder) {
        select.innerHTML = '<option value="">' + placeholder + '</option>';
        select.disabled = true;
    }

    function fillSelect(select, items, placeholder) {
        select.innerHTML = '<option value="">' + placeholder + '</option>';
        items.forEach(function (item) {
            var opt = document.createElement('option');
            opt.value = item.id;
            opt.textContent = item.name;
            select.appendChild(opt);
        });
        select.disabled = false;
    }

    // Nombradas (no solo listeners inline) para que restoreDraft() más abajo
    // pueda encadenarlas con await en vez de adivinar cuándo terminó el fetch.
    function loadFacultiesAndCampuses(institutionId) {
        resetSelect(facultySelect, 'Elegir facultad primero');
        resetSelect(careerSelect, 'Elegir facultad primero');
        resetSelect(campusSelect, 'Sin sede específica');
        addCampusToggle.classList.add('d-none');
        if (!institutionId) return Promise.resolve();

        var p1 = fetch(CFG.urls.getFacultiesByInstitutionBase + institutionId + '/')
            .then(function (r) { return r.json(); })
            .then(function (data) { fillSelect(facultySelect, data.faculties || [], 'Seleccionar facultad'); })
            .catch(function () { resetSelect(facultySelect, 'Error al cargar facultades'); });

        var p2 = fetch(CFG.urls.getCampusesByInstitutionBase + institutionId + '/')
            .then(function (r) { return r.json(); })
            .then(function (data) { fillSelect(campusSelect, data.campuses || [], 'Sin sede específica'); })
            .catch(function () { resetSelect(campusSelect, 'Sin sede específica'); });

        // Recién con institución elegida tiene sentido "+ Agregar sede" (la
        // crea directo ahí, sin mandar al usuario a otra pantalla y perder
        // el asistente — ver wireCampusQuickAdd más abajo).
        addCampusToggle.classList.remove('d-none');
        return Promise.all([p1, p2]);
    }
    institutionSelect.addEventListener('change', function () { loadFacultiesAndCampuses(this.value); });

    function loadCareers(facultyId) {
        resetSelect(careerSelect, 'Elegir carrera primero');
        if (!facultyId) return Promise.resolve();
        return fetch(CFG.urls.getCareersByFacultyBase + facultyId + '/')
            .then(function (r) { return r.json(); })
            .then(function (data) { fillSelect(careerSelect, data.careers || [], 'Seleccionar carrera'); })
            .catch(function () { resetSelect(careerSelect, 'Error al cargar carreras'); });
    }
    facultySelect.addEventListener('change', function () { loadCareers(this.value); });

    // ── "+ Agregar sede" sin salir del asistente ─────────────────────────
    // Mismo endpoint que ya usa el formulario clásico (create_exam_template.js)
    // para altas rápidas de institución/facultad/carrera/materia/sede — acá
    // solo se cablea para sede, que es el único de los 4 selects del paso 1
    // que puede quedar vacío con la institución ya bien elegida (facultad y
    // carrera, si están vacías, es la institución la que no tiene catálogo
    // cargado — caso distinto, no resuelto acá).
    (function wireCampusQuickAdd() {
        var toggle = document.getElementById('wizAddCampusToggle');
        var row = document.getElementById('wizAddCampusRow');
        var input = document.getElementById('wizAddCampusInput');
        var saveBtn = document.getElementById('wizAddCampusSave');
        var cancelBtn = document.getElementById('wizAddCampusCancel');

        toggle.addEventListener('click', function () {
            row.classList.remove('d-none');
            input.focus();
        });
        cancelBtn.addEventListener('click', function () {
            input.value = '';
            row.classList.add('d-none');
        });
        saveBtn.addEventListener('click', function () {
            var name = input.value.trim();
            if (!name) { input.focus(); return; }
            if (!institutionSelect.value) { alert('Elegí una institución primero.'); return; }
            saveBtn.disabled = true;
            fetch(CFG.urls.createRelatedElement, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                },
                body: JSON.stringify({ type: 'campus', name: name, institution_id: institutionSelect.value })
            })
                .then(function (r) { return r.json().then(function (data) { return { ok: r.ok, data: data }; }); })
                .then(function (result) {
                    if (!result.ok || !result.data.success) {
                        throw new Error(result.data.error || 'No se pudo crear la sede.');
                    }
                    var opt = document.createElement('option');
                    opt.value = result.data.id;
                    opt.textContent = result.data.name;
                    campusSelect.appendChild(opt);
                    campusSelect.value = result.data.id;
                    campusSelect.disabled = false;
                    input.value = '';
                    row.classList.add('d-none');
                })
                .catch(function (err) { alert(err.message); })
                .finally(function () { saveBtn.disabled = false; });
        });
    })();

    // "Crear una" para Resultados de Aprendizaje cuando la materia elegida
    // no tiene ninguno — no hay (todavía) un alta rápida de RA sin salir del
    // asistente: la creación real vive en learningoutcome_add, que exige un
    // career_subject_id YA EXISTENTE (ver material/urls.py) y ese vínculo
    // Carrera↔Materia puede no existir para la combinación recién elegida.
    // El link va a la ficha de la materia (subject_detail), que sí lista
    // todas sus asociaciones Carrera↔Materia reales con su propio botón de
    // alta de RA por cada una — más confiable que adivinar/crear el vínculo
    // acá. Igual que con rúbricas, abre en pestaña nueva.
    function refreshOutcomesCreateLink(subjectId) {
        outcomesCreateLink.innerHTML = subjectId
            ? ' <a href="' + CFG.urls.subjectDetailBase + subjectId + '/" target="_blank" rel="noopener">Crear uno</a>'
            : '';
    }

    function loadOutcomesForSubject(subjectId, checkedIds) {
        outcomesList.innerHTML = '';
        refreshOutcomesCreateLink(subjectId);
        if (!subjectId) {
            outcomesList.classList.add('d-none');
            outcomesEmpty.classList.remove('d-none');
            return Promise.resolve();
        }
        return fetch(CFG.urls.getLearningOutcomes + '?subject_id=' + subjectId)
            .then(function (r) { return r.json(); })
            .then(function (outcomes) {
                if (!outcomes.length) {
                    outcomesList.classList.add('d-none');
                    outcomesEmpty.classList.remove('d-none');
                    return;
                }
                outcomes.forEach(function (outcome) {
                    var row = document.createElement('div');
                    row.className = 'form-check';
                    var checked = (checkedIds || []).includes(String(outcome.id));
                    row.innerHTML =
                        '<input class="form-check-input outcome-checkbox" type="checkbox" value="' + outcome.id + '" id="outcome_' + outcome.id + '"' + (checked ? ' checked' : '') + '>' +
                        '<label class="form-check-label" for="outcome_' + outcome.id + '">' + outcome.description + '</label>';
                    outcomesList.appendChild(row);
                });
                outcomesEmpty.classList.add('d-none');
                outcomesList.classList.remove('d-none');
            })
            .catch(function () {
                outcomesList.classList.add('d-none');
                outcomesEmpty.classList.remove('d-none');
            });
    }
    subjectSelect.addEventListener('change', function () { loadOutcomesForSubject(this.value); });

    // ── Rúbricas: mismo refresco que Resultados de aprendizaje, más el caso
    // "recién creé una en la pestaña nueva y volví" (ver window focus más
    // abajo) — antes esto quedaba invisible en el asistente hasta un F5, y
    // F5 no tenía backup: perdía todo el progreso (ver sessionStorage abajo). ──
    var rubricsEmpty = document.getElementById('wizRubricsEmpty');
    var rubricsList = document.getElementById('wizRubricsList');
    function loadRubrics(checkedIds) {
        return fetch(CFG.urls.getVisibleRubricsJson)
            .then(function (r) { return r.json(); })
            .then(function (data) {
                var rubrics = data.rubrics || [];
                rubricsList.innerHTML = '';
                rubrics.forEach(function (r) {
                    var row = document.createElement('div');
                    row.className = 'form-check';
                    var checked = (checkedIds || []).includes(String(r.id));
                    row.innerHTML =
                        '<input class="form-check-input rubric-checkbox" type="checkbox" value="' + r.id + '" id="rubric_cb_' + r.id + '"' + (checked ? ' checked' : '') + '>' +
                        '<label class="form-check-label" for="rubric_cb_' + r.id + '">' + r.title + '</label>';
                    rubricsList.appendChild(row);
                });
                rubricsEmpty.classList.toggle('d-none', rubrics.length > 0);
                rubricsList.classList.toggle('d-none', rubrics.length === 0);
            })
            .catch(function () { /* deja la lista servida por el servidor tal cual */ });
    }

    // Al volver a esta pestaña (creaste una rúbrica o un RA en una pestaña
    // nueva y volviste) se refresca lo que puede haber cambiado, sin
    // recargar la página ni perder el resto del progreso del asistente.
    window.addEventListener('focus', function () {
        var checkedOutcomes = Array.from(outcomesList.querySelectorAll('.outcome-checkbox:checked')).map(function (cb) { return cb.value; });
        var checkedRubrics = Array.from(rubricsList.querySelectorAll('.rubric-checkbox:checked')).map(function (cb) { return cb.value; });
        if (subjectSelect.value) loadOutcomesForSubject(subjectSelect.value, checkedOutcomes);
        loadRubrics(checkedRubrics);
    });

    // ── Reordenar Materia según la carrera elegida en el paso 1 ──────────
    // Orden pedido: primero las materias con preguntas propias (van a dar un
    // examen mejor armado), después las de la carrera ya elegida, después
    // el resto — cada grupo en su propio <optgroup> (más claro que una
    // línea de separación suelta, y es HTML nativo de <select>). Se cachea
    // por career_id para no repetir el fetch si el usuario va y vuelve
    // entre pasos sin cambiar de carrera.
    var reorderedForCareerId = null;
    function reorderSubjectsByCareer(careerId) {
        if (!careerId || careerId === reorderedForCareerId) return Promise.resolve();
        var ownIds = (CFG.ownSubjectIds || []).map(String);
        var previousValue = subjectSelect.value;
        var allOptions = Array.from(subjectSelect.querySelectorAll('option[value]')).filter(function (o) { return o.value; });

        return fetch(CFG.urls.getSubjectsByCareerBase + careerId + '/')
            .then(function (r) { return r.json(); })
            .then(function (data) {
                var careerIds = (data.subjects || []).map(function (s) { return String(s.id); });
                var groupOwn = [], groupCareer = [], groupRest = [];
                allOptions.forEach(function (opt) {
                    if (ownIds.includes(opt.value)) groupOwn.push(opt);
                    else if (careerIds.includes(opt.value)) groupCareer.push(opt);
                    else groupRest.push(opt);
                });

                subjectSelect.innerHTML = '';
                var placeholder = document.createElement('option');
                placeholder.value = '';
                placeholder.textContent = 'Seleccionar materia';
                subjectSelect.appendChild(placeholder);

                function appendGroup(label, opts) {
                    if (!opts.length) return;
                    var group = document.createElement('optgroup');
                    group.label = label;
                    opts.forEach(function (o) { group.appendChild(o); });
                    subjectSelect.appendChild(group);
                }
                appendGroup('Con contenido propio (preguntas ya cargadas)', groupOwn);
                appendGroup('De esta carrera', groupCareer);
                appendGroup('Todas las demás', groupRest);

                subjectSelect.value = previousValue;
                reorderedForCareerId = careerId;
            })
            .catch(function () { /* deja el <select> plano tal cual venía del servidor */ });
    }

    function validateStep(n) {
        if (n === 1) {
            if (!institutionSelect.value || !facultySelect.value || !careerSelect.value) {
                alert('Elegí institución, facultad y carrera para continuar.');
                return false;
            }
            reorderSubjectsByCareer(careerSelect.value);
        }
        if (n === 2) {
            if (!subjectSelect.value) {
                subjectSelect.reportValidity ? subjectSelect.reportValidity() : alert('Falta seleccionar una materia.');
                return false;
            }
        }
        return true;
    }

    function renderSummary() {
        var box = document.getElementById('wizSummary');
        if (!box) return;
        var label = function (select) {
            return select.selectedOptions[0] && select.value ? select.selectedOptions[0].textContent : '-';
        };
        var outcomesCount = outcomesList.querySelectorAll('.outcome-checkbox:checked').length;
        var rubricsCount = document.querySelectorAll('.rubric-checkbox:checked').length;
        box.innerHTML =
            '<dl class="row mb-0">' +
            '<dt class="col-sm-4">Institución</dt><dd class="col-sm-8">' + label(institutionSelect) + '</dd>' +
            '<dt class="col-sm-4">Facultad / Carrera</dt><dd class="col-sm-8">' + label(facultySelect) + ' / ' + label(careerSelect) + '</dd>' +
            '<dt class="col-sm-4">Materia</dt><dd class="col-sm-8">' + label(subjectSelect) + '</dd>' +
            '<dt class="col-sm-4">Profesor</dt><dd class="col-sm-8">' + label(document.getElementById('id_professor')) + '</dd>' +
            '<dt class="col-sm-4">Resultados de aprendizaje</dt><dd class="col-sm-8">' + outcomesCount + ' seleccionado(s)</dd>' +
            '<dt class="col-sm-4">Rúbricas</dt><dd class="col-sm-8">' + rubricsCount + ' seleccionada(s)</dd>' +
            '</dl>';
    }

    var wizardCtrl = window.EducaAppWizard.init({
        totalSteps: 4,
        onValidateStep: validateStep,
        onEnterFinalStep: renderSummary,
    });

    // El guardado real NO pasa por ExamTemplateForm/create_exam_template —
    // ese endpoint tiene faculty/campus con queryset forzado a .none() (ver
    // ExamTemplateForm.__init__, forms.py), así que cualquier POST ahí
    // rechaza siempre esos dos campos. El formulario clásico en los hechos
    // guarda vía fetch() a save_exam_template (arma el objeto a mano desde
    // POST, sin pasar por el ModelForm) — este wizard reusa el mismo
    // endpoint y el mismo armado de FormData, no el <form> nativo.
    var submitBtn = document.getElementById('wizSubmitBtn');
    submitBtn.addEventListener('click', function () {
        if (!nameInput.value.trim()) {
            var subjectLabel = subjectSelect.selectedOptions[0] ? subjectSelect.selectedOptions[0].textContent : '';
            nameInput.value = 'Plantilla - ' + subjectLabel;
        }

        var form = document.getElementById('templateWizardForm');
        var formData = new FormData(form);
        // campus/professor/print_format vacíos deben viajar AUSENTES, no
        // como string vacío: save_exam_template hace request.POST.get(...)
        // sin default útil para "" (professor_id='' rompería el guardado,
        // a diferencia de la clave ausente que sí dispara su fallback a
        // request.user.id — ver esa vista).
        ['campus', 'professor', 'print_format'].forEach(function (field) {
            if (!formData.get(field)) formData.delete(field);
        });
        formData.set('save_mode', 'copy');
        formData.append('exam_mode', '');
        formData.append(
            'learning_outcomes',
            Array.from(outcomesList.querySelectorAll('.outcome-checkbox:checked')).map(function (cb) { return cb.value; }).join(',')
        );
        formData.append(
            'rubrics',
            Array.from(document.querySelectorAll('.rubric-checkbox:checked')).map(function (cb) { return cb.value; }).join(',')
        );

        var originalText = submitBtn.innerHTML;
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="bi bi-hourglass-split"></i> Creando...';

        fetch(CFG.urls.saveExamTemplate, {
            method: 'POST',
            body: formData,
            headers: { 'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value },
        })
            .then(function (r) { return r.json().then(function (data) { return { ok: r.ok, data: data }; }); })
            .then(function (result) {
                if (!result.ok || !result.data.success) {
                    throw new Error(result.data.error || 'No se pudo crear la plantilla.');
                }
                draft.clear();
                window.location.href = CFG.urls.listExamTemplates;
            })
            .catch(function (err) {
                alert(err.message);
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalText;
            });
    });

    // ── Backup a sessionStorage: red de contención ante F5 accidental,
    // cierre de pestaña, o volver de crear algo en una pestaña nueva y no
    // encontrar cómo seguir. Antes CUALQUIER recarga de esta pantalla
    // perdía absolutamente todo el progreso del asistente. Motor genérico
    // en wizard_draft.js (mismo patrón que ya usa Generar con IA) — acá
    // solo se define QUÉ guardar y CÓMO restaurarlo (la cascada de fetches
    // es específica de este wizard). ──────────────────────────────────────
    var draft = window.EducaAppWizardDraft.init('educaapp_template_wizard_draft');
    var form = document.getElementById('templateWizardForm');
    var professorSelect = document.getElementById('id_professor');
    var catedraInput = document.getElementById('id_catedra');
    var printFormatSelect = document.getElementById('id_print_format');
    var notesInput = document.getElementById('id_notes');

    function saveDraft() {
        draft.save({
            institution: institutionSelect.value,
            faculty: facultySelect.value,
            career: careerSelect.value,
            campus: campusSelect.value,
            subject: subjectSelect.value,
            professor: professorSelect.value,
            catedra: catedraInput.value,
            printFormat: printFormatSelect.value,
            name: nameInput.value,
            notes: notesInput.value,
            outcomeIds: Array.from(outcomesList.querySelectorAll('.outcome-checkbox:checked')).map(function (cb) { return cb.value; }),
            rubricIds: Array.from(rubricsList.querySelectorAll('.rubric-checkbox:checked')).map(function (cb) { return cb.value; }),
        });
    }
    form.addEventListener('change', saveDraft);
    form.addEventListener('input', saveDraft);

    function restoreDraft() {
        var saved = draft.load();
        if (!saved || !saved.institution) return;

        draft.confirmRestore('Encontramos una plantilla sin terminar de una sesión anterior. ¿Querés recuperarla?').then(function (quiere) {
            if (!quiere) { draft.clear(); return; }

            institutionSelect.value = saved.institution;
            loadFacultiesAndCampuses(saved.institution).then(function () {
                facultySelect.value = saved.faculty || '';
                if (saved.campus) campusSelect.value = saved.campus;
                return loadCareers(saved.faculty);
            }).then(function () {
                careerSelect.value = saved.career || '';
                return reorderSubjectsByCareer(saved.career);
            }).then(function () {
                subjectSelect.value = saved.subject || '';
                professorSelect.value = saved.professor || '';
                catedraInput.value = saved.catedra || '';
                printFormatSelect.value = saved.printFormat || '';
                nameInput.value = saved.name || '';
                notesInput.value = saved.notes || '';
                return Promise.all([
                    loadOutcomesForSubject(saved.subject, saved.outcomeIds),
                    loadRubrics(saved.rubricIds),
                ]);
            }).then(function () {
                // goToStep(4) no alcanza acá: el motor solo deja saltar a un
                // paso <= maxStepReached, y ese contador sigue en 1 porque
                // nunca se pasó por goNext() en esta carga — hay que
                // "caminar" los 3 pasos para que se actualice como
                // corresponde (los datos ya restaurados hacen que
                // onValidateStep pase limpio en cada uno).
                wizardCtrl.goNext();
                wizardCtrl.goNext();
                wizardCtrl.goNext();
            });
        });
    }

    form.addEventListener('submit', function (e) { e.preventDefault(); });
    wizardCtrl.goToStep(1);
    restoreDraft();
});
