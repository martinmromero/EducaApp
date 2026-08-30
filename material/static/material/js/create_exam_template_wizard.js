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
    var nameInput = document.getElementById('id_name');

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

    institutionSelect.addEventListener('change', function () {
        resetSelect(facultySelect, 'Elegir facultad primero');
        resetSelect(careerSelect, 'Elegir facultad primero');
        resetSelect(campusSelect, 'Sin sede específica');
        var institutionId = this.value;
        if (!institutionId) return;

        fetch(CFG.urls.getFacultiesByInstitutionBase + institutionId + '/')
            .then(function (r) { return r.json(); })
            .then(function (data) { fillSelect(facultySelect, data.faculties || [], 'Seleccionar facultad'); })
            .catch(function () { resetSelect(facultySelect, 'Error al cargar facultades'); });

        fetch(CFG.urls.getCampusesByInstitutionBase + institutionId + '/')
            .then(function (r) { return r.json(); })
            .then(function (data) { fillSelect(campusSelect, data.campuses || [], 'Sin sede específica'); })
            .catch(function () { resetSelect(campusSelect, 'Sin sede específica'); });
    });

    facultySelect.addEventListener('change', function () {
        resetSelect(careerSelect, 'Elegir carrera primero');
        var facultyId = this.value;
        if (!facultyId) return;
        fetch(CFG.urls.getCareersByFacultyBase + facultyId + '/')
            .then(function (r) { return r.json(); })
            .then(function (data) { fillSelect(careerSelect, data.careers || [], 'Seleccionar carrera'); })
            .catch(function () { resetSelect(careerSelect, 'Error al cargar carreras'); });
    });

    subjectSelect.addEventListener('change', function () {
        var subjectId = this.value;
        outcomesList.innerHTML = '';
        if (!subjectId) {
            outcomesList.classList.add('d-none');
            outcomesEmpty.classList.remove('d-none');
            return;
        }
        fetch(CFG.urls.getLearningOutcomes + '?subject_id=' + subjectId)
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
                    row.innerHTML =
                        '<input class="form-check-input outcome-checkbox" type="checkbox" value="' + outcome.id + '" id="outcome_' + outcome.id + '">' +
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
    });

    function validateStep(n) {
        if (n === 1) {
            if (!institutionSelect.value || !facultySelect.value || !careerSelect.value) {
                alert('Elegí institución, facultad y carrera para continuar.');
                return false;
            }
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
                window.location.href = CFG.urls.listExamTemplates;
            })
            .catch(function (err) {
                alert(err.message);
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalText;
            });
    });

    wizardCtrl.goToStep(1);
});
