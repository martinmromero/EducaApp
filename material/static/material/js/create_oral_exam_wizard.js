// create_oral_exam_wizard.js
// Asistente paso a paso para "Cuestionario Oral" (material/oral_exams/create_oral_exam_wizard.html).
// Postea al mismo create_oral_exam de siempre — toda la validación real
// (num_groups <= total_students, subtemas suficientes) vive ahí (OralExamForm),
// acá solo se anticipa la misma regla en vivo para que el aviso aparezca
// ANTES de enviar, no después.

// document.addEventListener('DOMContentLoaded', fn) a secas no alcanza: si
// el evento ya disparó para cuando este script corre, el callback nunca se
// ejecuta sin ningún error visible (encontrado y confirmado en
// create_exam_template_wizard.js, mismo patrón acá por las dudas).
function _onDomReady(fn) {
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', fn);
    } else {
        fn();
    }
}

_onDomReady(function () {
    var CFG = window.EducaAppOralWizardConfig || { urls: {} };

    var subjectSelect = document.getElementById('id_subject');
    var topicsEmpty = document.getElementById('wizOralTopicsEmpty');
    var topicsWrap = document.getElementById('wizOralTopicsWrap');
    var topicsList = document.getElementById('wizOralTopicsList');
    var totalStudentsInput = document.getElementById('id_total_students');
    var numGroupsInput = document.getElementById('id_num_groups');
    var questionsPerStudentInput = document.getElementById('id_questions_per_student');
    var studentsPerGroupHidden = document.getElementById('id_students_per_group');
    var validationBox = document.getElementById('wizOralValidation');
    var nameInput = document.getElementById('id_name');

    function debounce(fn, wait) {
        var t;
        return function () {
            var args = arguments;
            clearTimeout(t);
            t = setTimeout(function () { fn.apply(null, args); }, wait);
        };
    }

    function getSelectedTopicIds() {
        return Array.from(topicsList.querySelectorAll('input[type="checkbox"]:checked')).map(function (cb) {
            return cb.value;
        });
    }

    // ── Paso 1: tópicos según materia ────────────────────────────────────
    function loadTopicsForSubject(subjectId) {
        if (!subjectId) {
            topicsWrap.classList.add('d-none');
            topicsEmpty.classList.remove('d-none');
            topicsList.innerHTML = '';
            return;
        }
        fetch(CFG.urls.getTopics + '?subject_id=' + subjectId + '&for_exam=1')
            .then(function (r) { return r.json(); })
            .then(function (topics) {
                topicsList.innerHTML = '';
                if (!topics.length) {
                    topicsWrap.classList.add('d-none');
                    topicsEmpty.classList.remove('d-none');
                    topicsEmpty.textContent = 'Esta materia todavía no tiene preguntas propias cargadas.';
                    return;
                }
                topics.forEach(function (topic) {
                    var row = document.createElement('div');
                    row.className = 'form-check';
                    row.innerHTML =
                        '<input class="form-check-input" type="checkbox" name="topics" value="' + topic.id + '" id="oral_topic_' + topic.id + '">' +
                        '<label class="form-check-label" for="oral_topic_' + topic.id + '">' + topic.name + '</label>';
                    topicsList.appendChild(row);
                });
                topicsEmpty.classList.add('d-none');
                topicsWrap.classList.remove('d-none');
            })
            .catch(function () {
                topicsList.innerHTML = '<p class="text-danger small mb-0">Error al cargar tópicos.</p>';
            });
    }

    subjectSelect.addEventListener('change', function () {
        loadTopicsForSubject(this.value);
        validationBox.innerHTML = '';
    });
    document.getElementById('oralTopicsSelectAll').addEventListener('click', function () {
        topicsList.querySelectorAll('input[type="checkbox"]').forEach(function (cb) { cb.checked = true; });
        refreshValidation();
    });
    document.getElementById('oralTopicsSelectNone').addEventListener('click', function () {
        topicsList.querySelectorAll('input[type="checkbox"]').forEach(function (cb) { cb.checked = false; });
        refreshValidation();
    });

    // ── Paso 2: alumnos/grupos/preguntas, con aviso en vivo ──────────────
    function syncStudentsPerGroup() {
        var totalStudents = parseInt(totalStudentsInput.value, 10) || 0;
        var numGroups = parseInt(numGroupsInput.value, 10) || 0;
        studentsPerGroupHidden.value = numGroups > 0 ? Math.ceil(totalStudents / numGroups) : '';
    }

    function renderValidation(html) {
        validationBox.innerHTML = html;
    }

    var warningHtml = function (msg) {
        return '<div class="alert alert-warning py-2 px-3 mb-0 small"><i class="bi bi-exclamation-triangle-fill me-1"></i>' + msg + '</div>';
    };
    var okHtml = function (msg) {
        return '<div class="alert alert-success py-2 px-3 mb-0 small"><i class="bi bi-check-circle-fill me-1"></i>' + msg + '</div>';
    };

    var fetchValidation = debounce(function () {
        var subjectId = subjectSelect.value;
        var topicIds = getSelectedTopicIds();
        var totalStudents = parseInt(totalStudentsInput.value, 10) || 0;
        var numGroups = parseInt(numGroupsInput.value, 10) || 0;
        var questionsPerStudent = parseInt(questionsPerStudentInput.value, 10) || 0;

        if (!subjectId || !topicIds.length || !totalStudents || !numGroups || !questionsPerStudent) {
            renderValidation('');
            return;
        }

        // Regla que ya aplica el servidor al enviar (OralExamForm.clean):
        // no puede haber más grupos que alumnos. Se anticipa acá sin
        // esperar la respuesta del servidor.
        if (numGroups > totalStudents) {
            renderValidation(warningHtml(
                'No puede haber más grupos (' + numGroups + ') que alumnos (' + totalStudents + ') — cada grupo necesita al menos uno.'
            ));
            return;
        }

        fetch(CFG.urls.validateOralExam, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
            },
            body: JSON.stringify({
                subject_id: subjectId,
                topic_ids: topicIds,
                total_students: totalStudents,
                questions_per_student: questionsPerStudent
            })
        })
            .then(function (r) { return r.json(); })
            .then(function (data) {
                if (!data.success) {
                    renderValidation(warningHtml(data.error || 'No se pudo validar la configuración.'));
                    return;
                }
                var studentsPerGroup = Math.ceil(totalStudents / numGroups);
                var info = data.info;
                if (studentsPerGroup > info.max_students_per_group) {
                    renderValidation(warningHtml(
                        'Con ' + info.total_subtopics + ' sub-tema(s) disponible(s) y ' + questionsPerStudent + ' pregunta(s) por alumno, ' +
                        'el máximo recomendado es ' + info.max_students_per_group + ' alumno(s) por grupo — esta configuración da ' +
                        studentsPerGroup + '. Aumentá los grupos o bajá las preguntas por alumno para evitar repeticiones.'
                    ));
                } else {
                    renderValidation(okHtml(
                        'Cada grupo va a tener hasta ' + studentsPerGroup + ' alumno(s), con ' + info.total_subtopics +
                        ' sub-tema(s) disponible(s) — alcanza sin repetir.'
                    ));
                }
            })
            .catch(function () {
                renderValidation('');
            });
    }, 300);

    function refreshValidation() {
        syncStudentsPerGroup();
        fetchValidation();
    }

    [totalStudentsInput, numGroupsInput, questionsPerStudentInput].forEach(function (input) {
        input.addEventListener('input', refreshValidation);
    });

    // ── Validación por paso (bloquea "Siguiente") ────────────────────────
    function validateStep(n) {
        if (n === 1) {
            if (!subjectSelect.value) {
                subjectSelect.reportValidity ? subjectSelect.reportValidity() : alert('Falta seleccionar una materia.');
                return false;
            }
            if (!getSelectedTopicIds().length) {
                alert('Elegí al menos un tópico para continuar.');
                return false;
            }
        }
        if (n === 2) {
            var totalStudents = parseInt(totalStudentsInput.value, 10) || 0;
            var numGroups = parseInt(numGroupsInput.value, 10) || 0;
            var questionsPerStudent = parseInt(questionsPerStudentInput.value, 10) || 0;
            if (!totalStudents || !numGroups || !questionsPerStudent) {
                alert('Completá alumnos, grupos y preguntas por alumno para continuar.');
                return false;
            }
            if (numGroups > totalStudents) {
                alert('No puede haber más grupos que alumnos.');
                return false;
            }
        }
        return true;
    }

    // ── Paso 3: resumen ───────────────────────────────────────────────────
    function renderSummary() {
        var box = document.getElementById('wizSummary');
        if (!box) return;
        var subjectLabel = subjectSelect.selectedOptions[0] ? subjectSelect.selectedOptions[0].textContent : 'sin elegir';
        var topicsCount = getSelectedTopicIds().length;
        box.innerHTML =
            '<dl class="row mb-0">' +
            '<dt class="col-sm-4">Materia</dt><dd class="col-sm-8">' + subjectLabel + '</dd>' +
            '<dt class="col-sm-4">Tópicos</dt><dd class="col-sm-8">' + topicsCount + ' seleccionado(s)</dd>' +
            '<dt class="col-sm-4">Alumnos</dt><dd class="col-sm-8">' + (totalStudentsInput.value || '-') + '</dd>' +
            '<dt class="col-sm-4">Grupos</dt><dd class="col-sm-8">' + (numGroupsInput.value || '-') + ' (hasta ' + (studentsPerGroupHidden.value || '-') + ' alumno(s) c/u)</dd>' +
            '<dt class="col-sm-4">Preguntas por alumno</dt><dd class="col-sm-8">' + (questionsPerStudentInput.value || '-') + '</dd>' +
            '</dl>';
    }

    var wizardCtrl = window.EducaAppWizard.init({
        totalSteps: 3,
        onValidateStep: validateStep,
        onEnterFinalStep: renderSummary,
    });

    document.getElementById('oralWizardForm').addEventListener('submit', function () {
        if (!nameInput.value.trim()) {
            nameInput.value = 'Examen Oral - ' + (subjectSelect.selectedOptions[0] ? subjectSelect.selectedOptions[0].textContent : '');
        }
    });

    wizardCtrl.goToStep(1);
});
