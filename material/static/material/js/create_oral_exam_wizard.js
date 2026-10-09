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

    // Embebido en el Asistente completo (<iframe>, ver full_wizard.js): avisos al
    // host por postMessage de mismo origen.
    function postToHost(type, payload) {
        try { window.parent.postMessage(Object.assign({ type: type }, payload || {}), window.location.origin); } catch (e) { /* sin host */ }
    }

    // Pantalla de "guardado": no hay formulario, solo se le avisa al host.
    if (CFG.saved) {
        postToHost('educaapp:oral-saved', {
            name: CFG.saved.name, viewUrl: CFG.saved.view_url, warnings: CFG.saved.warnings || [],
        });
        try { sessionStorage.removeItem('educaapp_oral_wizard_draft_fw'); } catch (e) { /* sin sessionStorage */ }
        return;
    }

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

    // La materia es un <select>, o un <input hidden> con data-label cuando viene fijada
    // desde el Asistente completo.
    function subjectLabel() {
        if (subjectSelect.selectedOptions && subjectSelect.selectedOptions[0]) return subjectSelect.selectedOptions[0].textContent;
        return subjectSelect.dataset.label || 'sin elegir';
    }

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
            return Promise.resolve();
        }
        return fetch(CFG.urls.getTopics + '?subject_id=' + subjectId + '&for_exam=1&include_no_topic=1')
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
                        '<input class="form-check-input" type="checkbox" name="topics" value="' + window.EducaAppEscape(topic.id) + '" id="oral_topic_' + window.EducaAppEscape(topic.id) + '">' +
                        '<label class="form-check-label" for="oral_topic_' + window.EducaAppEscape(topic.id) + '">' + window.EducaAppEscape(topic.name) + '</label>';
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
                // Dos límites DISTINTOS, que antes se mezclaban en un solo
                // mensaje basado solo en sub-temas (implicaba que la creación
                // era directamente inviable, "sin importar cuántos grupos se
                // armen", cuando en realidad generate_oral_exam_questions
                // (views.py) ya degrada reutilizando sub-temas sin bloquear
                // nada — reportado en Modo Testing con 60 preguntas y 3
                // sub-temas, mensaje seguía diciendo "no alcanza"): (1) que
                // ALCANCEN LAS PREGUNTAS para no repetir la pregunta exacta
                // dentro de un mismo grupo (el problema real, el algoritmo SI
                // evita esto mientras haya preguntas sin usar en el grupo) y
                // (2) que alcancen los SUB-TEMAS para que cada alumno no
                // repita sub-tema entre sus propias preguntas (una preferencia
                // de variedad, no algo que impida crear el cuestionario).
                var questionsNeededPerGroup = studentsPerGroup * questionsPerStudent;
                var enoughQuestions = info.total_questions >= questionsNeededPerGroup;
                var enoughSubtopics = info.total_subtopics >= questionsPerStudent;

                if (!enoughQuestions) {
                    renderValidation(warningHtml(
                        'Hay ' + info.total_questions + ' pregunta(s) disponible(s) en total, pero el grupo más numeroso necesita ' +
                        questionsNeededPerGroup + ' (' + studentsPerGroup + ' alumno(s) × ' + questionsPerStudent + ' pregunta(s)) para no repetir ' +
                        'la misma pregunta entre alumnos de ese grupo. Es probable que se repita alguna pregunta exacta. ' +
                        'Para evitarlo: agregar más preguntas, aumentar la cantidad de grupos o reducir las preguntas por alumno.'
                    ));
                } else if (!enoughSubtopics) {
                    renderValidation(warningHtml(
                        'Hay ' + info.total_subtopics + ' sub-tema(s) disponible(s) para ' + questionsPerStudent + ' pregunta(s) por alumno, ' +
                        'así que cada alumno va a repetir sub-tema entre sus propias preguntas. Esto no impide crear el cuestionario: ' +
                        'hay ' + info.total_questions + ' pregunta(s) en total, suficientes para que no se repita la pregunta exacta dentro de un mismo grupo.'
                    ));
                } else {
                    renderValidation(okHtml(
                        'Cada grupo va a tener hasta ' + studentsPerGroup + ' alumno(s), con ' + info.total_subtopics +
                        ' sub-tema(s) y ' + info.total_questions + ' pregunta(s) disponibles — alcanza sin repetir.'
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
                subjectSelect.reportValidity ? subjectSelect.reportValidity() : window.EducaAppToast.show('Falta seleccionar una materia.', { variant: 'warning' });
                return false;
            }
            if (!getSelectedTopicIds().length) {
                window.EducaAppToast.show('Elegir al menos un tópico para continuar.', { variant: 'warning' });
                return false;
            }
        }
        if (n === 2) {
            var totalStudents = parseInt(totalStudentsInput.value, 10) || 0;
            var numGroups = parseInt(numGroupsInput.value, 10) || 0;
            var questionsPerStudent = parseInt(questionsPerStudentInput.value, 10) || 0;
            if (!totalStudents || !numGroups || !questionsPerStudent) {
                window.EducaAppToast.show('Completar alumnos, grupos y preguntas por alumno para continuar.', { variant: 'warning' });
                return false;
            }
            if (numGroups > totalStudents) {
                window.EducaAppToast.show('No puede haber más grupos que alumnos.', { variant: 'warning' });
                return false;
            }
        }
        return true;
    }

    // ── Paso 3: resumen ───────────────────────────────────────────────────
    function renderSummary() {
        var box = document.getElementById('wizSummary');
        if (!box) return;
        var materiaTexto = subjectLabel();
        var topicsCount = getSelectedTopicIds().length;
        box.innerHTML =
            '<dl class="row mb-0">' +
            '<dt class="col-sm-4">Materia</dt><dd class="col-sm-8">' + window.EducaAppEscape(materiaTexto) + '</dd>' +
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
        keepBackOnFirst: !!CFG.isEmbedded,
        onBackFromFirst: function () { postToHost('educaapp:oral-exit'); },
    });

    // ── Backup a sessionStorage (mismo motor que Plantilla de Examen y
    // Generar con IA, ver wizard_draft.js) — antes un F5 a mitad de elegir
    // tópicos/alumnos perdía todo, sin ningún respaldo. ──────────────────
    // Embebido usa su propia clave y NO se borra al enviar: si el servidor rechaza la
    // configuración, el asistente vuelve con el error y tiene que reponer lo ya cargado.
    var draft = window.EducaAppWizardDraft.init(CFG.isEmbedded ? 'educaapp_oral_wizard_draft_fw' : 'educaapp_oral_wizard_draft');
    var oralForm = document.getElementById('oralWizardForm');

    function saveDraft() {
        draft.save({
            subject: subjectSelect.value,
            topicIds: getSelectedTopicIds(),
            totalStudents: totalStudentsInput.value,
            numGroups: numGroupsInput.value,
            questionsPerStudent: questionsPerStudentInput.value,
            name: nameInput.value,
        });
    }
    oralForm.addEventListener('change', saveDraft);
    oralForm.addEventListener('input', saveDraft);

    function restoreDraft() {
        var saved = draft.load();
        if (!saved || !saved.subject) return;
        // Dentro del Asistente completo la materia ya está fijada: un borrador de otra materia no sirve.
        if (CFG.isEmbedded && CFG.fwSubjectId && String(saved.subject) !== String(CFG.fwSubjectId)) { draft.clear(); return; }

        var ask = CFG.isEmbedded
            ? Promise.resolve(true)
            : draft.confirmRestore('Encontramos un cuestionario oral sin terminar de una sesión anterior. ¿Recuperarlo?');
        ask.then(function (quiere) {
            if (!quiere) { draft.clear(); return; }

            subjectSelect.value = saved.subject;
            loadTopicsForSubject(saved.subject).then(function () {
                (saved.topicIds || []).forEach(function (id) {
                    var cb = topicsList.querySelector('input[value="' + id + '"]');
                    if (cb) cb.checked = true;
                });
                totalStudentsInput.value = saved.totalStudents || '';
                numGroupsInput.value = saved.numGroups || '';
                questionsPerStudentInput.value = saved.questionsPerStudent || '';
                nameInput.value = saved.name || '';
                refreshValidation();
                // goToStep(3) no alcanza: el motor solo deja saltar a un paso
                // <= maxStepReached, que sigue en 1 sin haber pasado por
                // goNext() en esta carga (ver wizard_draft.js).
                wizardCtrl.goNext();
                wizardCtrl.goNext();
            });
        });
    }

    document.getElementById('oralWizardForm').addEventListener('submit', function () {
        if (!nameInput.value.trim()) {
            nameInput.value = 'Examen Oral - ' + (subjectLabel() === 'sin elegir' ? '' : subjectLabel());
        }
        if (!CFG.isEmbedded) draft.clear();
    });

    wizardCtrl.goToStep(1);
    if (CFG.isEmbedded && CFG.fwSubjectId) {
        // Materia fijada por el Asistente completo: se cargan sus tópicos de entrada.
        loadTopicsForSubject(CFG.fwSubjectId).then(restoreDraft);
    } else {
        restoreDraft();
    }
});
