// create_exam_wizard.js
// Asistente paso a paso para "Crear Examen" (material/exams/create_exam_wizard.html).
// Página nueva e independiente de create_exam.js: mismos endpoints, DOM distinto
// (un paso visible a la vez + selector de tópicos/preguntas coloreado por tópico).

document.addEventListener('DOMContentLoaded', function () {
    var CFG = window.EducaAppWizardConfig || { urls: {} };
    var TOTAL_STEPS = 6;
    var currentStep = 1;
    var maxStepReached = 1;

    // ── Navegación entre pasos ─────────────────────────────────────────
    function showStep(n) {
        document.querySelectorAll('.wiz-step').forEach(function (el) {
            el.classList.toggle('is-active', parseInt(el.dataset.step, 10) === n);
        });
        document.querySelectorAll('.wiz-step-pill').forEach(function (pill) {
            var pn = parseInt(pill.dataset.stepPill, 10);
            pill.classList.toggle('is-active', pn === n);
            pill.classList.toggle('is-done', pn < maxStepReached);
            pill.classList.toggle('is-reachable', pn <= maxStepReached && pn !== n);
        });
        document.getElementById('wizBackBtn').classList.toggle('d-none', n === 1);
        document.getElementById('wizNextBtn').classList.toggle('d-none', n === TOTAL_STEPS);
        document.getElementById('wizSubmitBtn').classList.toggle('d-none', n !== TOTAL_STEPS);
        currentStep = n;
        if (n === TOTAL_STEPS) renderSummary();
        window.scrollTo({ top: document.getElementById('wizStepper').offsetTop - 20, behavior: 'smooth' });
    }

    function validateStep(n) {
        if (n === 2) {
            var subject = document.getElementById('id_subject');
            if (subject && !subject.value) {
                subject.reportValidity ? subject.reportValidity() : alert('Elegí una materia para continuar.');
                return false;
            }
        }
        return true;
    }

    document.getElementById('wizNextBtn').addEventListener('click', function () {
        if (!validateStep(currentStep)) return;
        var next = Math.min(currentStep + 1, TOTAL_STEPS);
        maxStepReached = Math.max(maxStepReached, next);
        showStep(next);
    });
    document.getElementById('wizBackBtn').addEventListener('click', function () {
        showStep(Math.max(currentStep - 1, 1));
    });
    document.querySelectorAll('.wiz-step-pill').forEach(function (pill) {
        pill.addEventListener('click', function () {
            var n = parseInt(pill.dataset.stepPill, 10);
            if (n <= maxStepReached) showStep(n);
        });
    });

    function renderSummary() {
        var box = document.getElementById('wizSummary');
        if (!box) return;
        var subject = document.getElementById('id_subject');
        var subjectLabel = subject && subject.selectedOptions[0] ? subject.selectedOptions[0].textContent : 'sin elegir';
        var topicsCount = document.querySelectorAll('#wizTopicsList input[type="checkbox"]:checked').length;
        var questionsCount = document.querySelectorAll('#wizQuestionsGroups input[type="checkbox"]:checked').length;
        var fecha = document.getElementById('fecha').value || 'sin definir';
        var versions = document.getElementById('num_versions').value || '1';
        box.innerHTML =
            '<dl class="row mb-0">' +
            '<dt class="col-sm-4">Materia</dt><dd class="col-sm-8">' + subjectLabel + '</dd>' +
            '<dt class="col-sm-4">Tópicos elegidos</dt><dd class="col-sm-8">' + topicsCount + '</dd>' +
            '<dt class="col-sm-4">Preguntas elegidas</dt><dd class="col-sm-8">' + questionsCount + '</dd>' +
            '<dt class="col-sm-4">Fecha</dt><dd class="col-sm-8">' + fecha + '</dd>' +
            '<dt class="col-sm-4">Temas a generar</dt><dd class="col-sm-8">' + versions + '</dd>' +
            '</dl>';
    }

    // ── Duración: convierte a minutos justo antes de enviar ─────────────
    var wizForm = document.getElementById('examWizardForm');
    var durationInput = document.getElementById('id_duration_minutes');
    var durationUnit = document.getElementById('duration_unit');
    var MINUTES_PER_UNIT = { minutos: 1, horas: 60, dias: 1440, semanas: 10080 };
    wizForm.addEventListener('submit', function () {
        var raw = parseFloat(durationInput.value);
        if (!isNaN(raw)) {
            var factor = MINUTES_PER_UNIT[durationUnit.value] || 1;
            durationInput.value = Math.round(raw * factor);
        }
    });

    var yearInput = document.getElementById('year');
    if (yearInput && !yearInput.value) yearInput.value = new Date().getFullYear();

    // ── Período → campo oculto batch_semester ────────────────────────────
    var periodoNumero = document.getElementById('periodo_numero');
    var periodoTipo = document.getElementById('periodo_tipo');
    var batchSemesterHidden = document.getElementById('batch_semester');
    function syncPeriodo() {
        var numero = periodoNumero.value.trim();
        var tipo = periodoTipo.value;
        batchSemesterHidden.value = numero ? (numero + ' ' + tipo) : '';
        updateSuggestedBatchName();
    }
    [periodoNumero, periodoTipo].forEach(function (el) {
        el.addEventListener('change', syncPeriodo);
        el.addEventListener('input', syncPeriodo);
    });

    // ── Toggle institución/facultad/carrera/sede ────────────────────────
    var institucionToggleBtn = document.getElementById('wizToggleInstitucion');
    var institucionBlock = document.getElementById('wizInstitucionBlock');
    institucionToggleBtn.addEventListener('click', function () {
        var willShow = institucionBlock.classList.contains('d-none');
        institucionBlock.classList.toggle('d-none', !willShow);
        institucionToggleBtn.textContent = willShow
            ? '– Ocultar institución, facultad, carrera y sede'
            : '+ Agregar institución, facultad, carrera y sede';
    });
    function openInstitucionBlock() {
        institucionBlock.classList.remove('d-none');
        institucionToggleBtn.textContent = '– Ocultar institución, facultad, carrera y sede';
    }

    // ── Nombre sugerido del examen ───────────────────────────────────────
    var batchNameInput = document.getElementById('batch_name');
    batchNameInput.addEventListener('input', function () {
        this.dataset.userEdited = this.value.trim() ? '1' : '0';
    });
    function updateSuggestedBatchName() {
        if (batchNameInput.dataset.userEdited === '1') return;
        var tipoMap = {
            '1er_parcial': '1er parcial', '2do_parcial': '2do parcial', '3er_parcial': '3er parcial',
            'final': 'final', 'recuperatorio': 'recuperatorio', 'practico': 'practico'
        };
        var tipo = tipoMap[document.getElementById('tipo_examen_select').value] || 'examen';
        var subject = document.getElementById('id_subject');
        var subjectLabel = subject && subject.selectedOptions[0] ? subject.selectedOptions[0].textContent : 'sin materia';
        var institution = document.getElementById('institucion_dropdown');
        var institutionLabel = institution && institution.selectedOptions[0] ? institution.selectedOptions[0].textContent : 'sin institucion';
        var semester = batchSemesterHidden.value || 'sin periodo';
        var curso = document.getElementById('curso').value.trim();
        var versions = document.getElementById('num_versions').value || '1';
        var fecha = document.getElementById('fecha').value;
        var year = yearInput.value || (fecha ? fecha.split('-')[0] : 'sin anio');
        var parts = [tipo, subjectLabel, institutionLabel, semester];
        if (curso) parts.push(curso);
        parts.push(year, versions + ' opciones');
        batchNameInput.value = parts.join(' - ');
    }
    ['change', 'input'].forEach(function (evt) {
        document.getElementById('id_subject').addEventListener(evt, updateSuggestedBatchName);
        document.getElementById('institucion_dropdown').addEventListener(evt, updateSuggestedBatchName);
        document.getElementById('curso').addEventListener(evt, updateSuggestedBatchName);
        document.getElementById('num_versions').addEventListener(evt, updateSuggestedBatchName);
        document.getElementById('fecha').addEventListener(evt, updateSuggestedBatchName);
        document.getElementById('year').addEventListener(evt, updateSuggestedBatchName);
        document.getElementById('tipo_examen_select').addEventListener(evt, updateSuggestedBatchName);
    });

    // ── Tópicos y preguntas, coloreados por tópico ───────────────────────
    var TOPIC_COLOR_VARS = ['--wiz-topic-1', '--wiz-topic-2', '--wiz-topic-3', '--wiz-topic-4',
        '--wiz-topic-5', '--wiz-topic-6', '--wiz-topic-7', '--wiz-topic-8'];
    var topicColorMap = {};
    var topicNameMap = {};
    var allQuestionsCache = []; // {id, text, topic_id} — TODAS las elegibles de la materia actual
    var selectedQuestionIds = []; // conserva la selección al re-renderizar

    function topicColor(topicId) {
        return topicColorMap[topicId] || 'var(--wiz-topic-other)';
    }

    function assignTopicColors(topics) {
        topicColorMap = {};
        topicNameMap = {};
        topics.forEach(function (t, i) {
            topicColorMap[t.id] = i < TOPIC_COLOR_VARS.length ? 'var(' + TOPIC_COLOR_VARS[i] + ')' : 'var(--wiz-topic-other)';
            topicNameMap[t.id] = t.name;
        });
    }

    function getSelectedTopicIds() {
        return Array.from(document.querySelectorAll('#wizTopicsList input[type="checkbox"]:checked'))
            .map(function (cb) { return parseInt(cb.dataset.topicValue, 10); });
    }

    function syncHiddenSelect(selectEl, ids) {
        selectEl.innerHTML = '';
        ids.forEach(function (id) {
            var opt = document.createElement('option');
            opt.value = id;
            opt.selected = true;
            selectEl.appendChild(opt);
        });
    }

    function renderTopicsList(topics) {
        var list = document.getElementById('wizTopicsList');
        list.innerHTML = '';
        var counts = {};
        allQuestionsCache.forEach(function (q) { counts[q.topic_id] = (counts[q.topic_id] || 0) + 1; });

        topics.forEach(function (t) {
            var row = document.createElement('div');
            row.className = 'wiz-topic-row';

            var dot = document.createElement('span');
            dot.className = 'wiz-topic-dot';
            dot.style.background = topicColor(t.id);

            var cb = document.createElement('input');
            cb.type = 'checkbox';
            cb.className = 'form-check-input';
            cb.id = 'wiz_topic_cb_' + t.id;
            cb.dataset.topicValue = t.id;
            cb.addEventListener('change', onTopicSelectionChange);

            var label = document.createElement('label');
            label.htmlFor = cb.id;
            label.textContent = t.name;

            var count = document.createElement('span');
            count.className = 'wiz-topic-count';
            var n = counts[t.id] || 0;
            count.textContent = n + (n === 1 ? ' pregunta' : ' preguntas');

            row.appendChild(dot);
            row.appendChild(cb);
            row.appendChild(label);
            row.appendChild(count);
            list.appendChild(row);
        });
    }

    function onTopicSelectionChange() {
        var selectedTopics = getSelectedTopicIds();
        syncHiddenSelect(document.getElementById('id_topics'), selectedTopics);
        renderQuestionGroups(selectedTopics);
    }

    function renderQuestionGroups(selectedTopicIds) {
        var wrap = document.getElementById('wizQuestionsGroups');
        var previouslyChecked = Array.from(document.querySelectorAll('#wizQuestionsGroups input[type="checkbox"]:checked'))
            .map(function (cb) { return String(cb.dataset.questionValue); });
        // Conserva selección previa aunque el grupo desaparezca momentáneamente
        // (p.ej. se destilda y retilda el mismo tópico).
        selectedQuestionIds = Array.from(new Set(selectedQuestionIds.concat(previouslyChecked)));

        wrap.innerHTML = '';
        if (!selectedTopicIds.length) {
            wrap.innerHTML = '<div class="wiz-questions-empty">Elegí al menos un tópico arriba para ver sus preguntas acá.</div>';
            syncHiddenSelect(document.getElementById('id_questions'), []);
            return;
        }

        selectedTopicIds.forEach(function (topicId) {
            var questions = allQuestionsCache.filter(function (q) { return q.topic_id === topicId; });
            var group = document.createElement('div');
            group.className = 'wiz-question-group';
            group.style.borderLeftColor = topicColor(topicId);

            var header = document.createElement('div');
            header.className = 'wiz-question-group-header';
            var title = document.createElement('div');
            title.className = 'wiz-question-group-title';
            var dot = document.createElement('span');
            dot.className = 'wiz-topic-dot';
            dot.style.background = topicColor(topicId);
            title.appendChild(dot);
            var titleText = document.createElement('span');
            titleText.textContent = topicNameMap[topicId] || 'Tópico';
            title.appendChild(titleText);
            var countSpan = document.createElement('span');
            countSpan.className = 'wiz-question-group-count';
            title.appendChild(countSpan);
            header.appendChild(title);

            var actions = document.createElement('div');
            actions.className = 'wiz-question-group-actions btn-group btn-group-sm';
            var allBtn = document.createElement('button');
            allBtn.type = 'button';
            allBtn.className = 'btn btn-outline-secondary';
            allBtn.textContent = 'Todo';
            var noneBtn = document.createElement('button');
            noneBtn.type = 'button';
            noneBtn.className = 'btn btn-outline-secondary';
            noneBtn.textContent = 'Ninguno';
            actions.appendChild(allBtn);
            actions.appendChild(noneBtn);
            header.appendChild(actions);

            group.appendChild(header);

            if (!questions.length) {
                var empty = document.createElement('div');
                empty.className = 'wiz-question-row text-muted';
                empty.textContent = 'Sin preguntas disponibles para este tópico todavía.';
                group.appendChild(empty);
            }

            questions.forEach(function (q) {
                var row = document.createElement('div');
                row.className = 'wiz-question-row';
                var cb = document.createElement('input');
                cb.type = 'checkbox';
                cb.className = 'form-check-input';
                cb.id = 'wiz_question_cb_' + q.id;
                cb.dataset.questionValue = q.id;
                cb.checked = selectedQuestionIds.includes(String(q.id));
                cb.addEventListener('change', onQuestionSelectionChange);
                var label = document.createElement('label');
                label.htmlFor = cb.id;
                label.textContent = q.text;
                row.appendChild(cb);
                row.appendChild(label);
                group.appendChild(row);
            });

            function updateGroupCount() {
                var checked = group.querySelectorAll('input[type="checkbox"]:checked').length;
                countSpan.textContent = checked + '/' + questions.length + ' seleccionadas';
            }
            updateGroupCount();
            group.addEventListener('change', updateGroupCount);

            allBtn.addEventListener('click', function () {
                group.querySelectorAll('input[type="checkbox"]').forEach(function (cb) { cb.checked = true; });
                updateGroupCount();
                onQuestionSelectionChange();
            });
            noneBtn.addEventListener('click', function () {
                group.querySelectorAll('input[type="checkbox"]').forEach(function (cb) { cb.checked = false; });
                updateGroupCount();
                onQuestionSelectionChange();
            });

            wrap.appendChild(group);
        });

        onQuestionSelectionChange();
    }

    function onQuestionSelectionChange() {
        var ids = Array.from(document.querySelectorAll('#wizQuestionsGroups input[type="checkbox"]:checked'))
            .map(function (cb) { return cb.dataset.questionValue; });
        selectedQuestionIds = ids;
        syncHiddenSelect(document.getElementById('id_questions'), ids);
    }

    document.getElementById('topics_select_all').addEventListener('click', function () {
        document.querySelectorAll('#wizTopicsList input[type="checkbox"]').forEach(function (cb) { cb.checked = true; });
        onTopicSelectionChange();
    });
    document.getElementById('topics_select_none').addEventListener('click', function () {
        document.querySelectorAll('#wizTopicsList input[type="checkbox"]').forEach(function (cb) { cb.checked = false; });
        onTopicSelectionChange();
    });

    // ── Carga de tópicos + pool completo de preguntas + resultados de aprendizaje ──
    var subjectSelect = document.getElementById('id_subject');
    var topicsToPreselect = [];
    var questionsToPreselect = [];

    function loadSubjectDependents(subjectId, preselectTopics, preselectQuestions) {
        var topicsEmpty = document.getElementById('wizTopicsEmpty');
        var topicsWrap = document.getElementById('wizTopicsWrap');
        if (!subjectId) {
            topicsEmpty.classList.remove('d-none');
            topicsWrap.classList.add('d-none');
            return Promise.resolve();
        }
        topicsEmpty.classList.add('d-none');
        topicsWrap.classList.remove('d-none');

        var topicsPromise = fetch(CFG.urls.getTopics + '?subject_id=' + subjectId + '&for_exam=1')
            .then(function (r) { return r.json(); });
        var questionsPromise = fetch(CFG.urls.getQuestionsByTopics + '?subject_id=' + subjectId + '&all=true')
            .then(function (r) { return r.json(); });
        var outcomesPromise = fetch(CFG.urls.getLearningOutcomes + '?subject_id=' + subjectId)
            .then(function (r) { return r.json(); });

        return Promise.all([topicsPromise, questionsPromise, outcomesPromise]).then(function (results) {
            var topics = results[0];
            allQuestionsCache = results[1];
            var outcomes = results[2];

            assignTopicColors(topics);
            renderTopicsList(topics);

            if (preselectTopics && preselectTopics.length) {
                document.querySelectorAll('#wizTopicsList input[type="checkbox"]').forEach(function (cb) {
                    cb.checked = preselectTopics.map(String).includes(cb.dataset.topicValue);
                });
            }
            if (preselectQuestions && preselectQuestions.length) {
                selectedQuestionIds = preselectQuestions.map(String);
            }
            onTopicSelectionChange();

            var outcomesSection = document.getElementById('learning_outcomes_section');
            var outcomesContainer = document.getElementById('learning_outcomes_container');
            outcomesContainer.innerHTML = '';
            outcomes.forEach(function (o) {
                var div = document.createElement('div');
                div.className = 'form-check';
                var cb = document.createElement('input');
                cb.type = 'checkbox';
                cb.className = 'form-check-input';
                cb.name = 'learning_outcomes';
                cb.value = o.id;
                cb.id = 'wiz_outcome_' + o.id;
                var label = document.createElement('label');
                label.className = 'form-check-label';
                label.htmlFor = cb.id;
                label.textContent = o.description;
                div.appendChild(cb);
                div.appendChild(label);
                outcomesContainer.appendChild(div);
            });
            outcomesSection.classList.toggle('d-none', outcomes.length === 0);
        });
    }

    subjectSelect.addEventListener('change', function () {
        loadSubjectDependents(this.value, topicsToPreselect, questionsToPreselect);
        topicsToPreselect = [];
        questionsToPreselect = [];
        updateSuggestedBatchName();
    });

    // ── Cascada institución → facultad/sede, facultad → carrera ──────────
    var institucionSelect = document.getElementById('institucion_dropdown');
    var facultadSelect = document.getElementById('facultad_dropdown');
    var carreraSelect = document.getElementById('carrera_dropdown');
    var sedeSelect = document.getElementById('sede_dropdown');
    var institucionDependentsPromise = Promise.resolve();
    var facultadDependentsPromise = Promise.resolve();

    institucionSelect.addEventListener('change', function () {
        var institucionId = this.value;
        facultadSelect.innerHTML = '<option value="">Seleccionar facultad</option><option value="otro">Otro</option>';
        carreraSelect.innerHTML = '<option value="">Seleccionar carrera</option><option value="otro">Otro</option>';
        sedeSelect.innerHTML = '<option value="">Seleccionar sede</option><option value="otro">Otro</option>';
        if (!institucionId || !/^\d+$/.test(institucionId)) {
            institucionDependentsPromise = Promise.resolve();
            return;
        }
        var facultiesPromise = fetch(CFG.urls.getFacultiesByInstitutionBase + institucionId + '/')
            .then(function (r) { return r.json(); })
            .then(function (data) {
                facultadSelect.innerHTML = '<option value="">Seleccionar facultad</option><option value="otro">Otro</option>';
                (data.faculties || []).forEach(function (f) {
                    var opt = document.createElement('option');
                    opt.value = f.id; opt.textContent = f.name;
                    facultadSelect.appendChild(opt);
                });
            });
        var campusesPromise = fetch(CFG.urls.getCampusesByInstitutionBase + institucionId + '/')
            .then(function (r) { return r.json(); })
            .then(function (data) {
                sedeSelect.innerHTML = '<option value="">Seleccionar sede</option><option value="otro">Otro</option>';
                (data.campuses || []).forEach(function (c) {
                    var opt = document.createElement('option');
                    opt.value = c.id; opt.textContent = c.name;
                    sedeSelect.appendChild(opt);
                });
            });
        institucionDependentsPromise = Promise.all([facultiesPromise, campusesPromise]);
        updateSuggestedBatchName();
    });

    facultadSelect.addEventListener('change', function () {
        var facultadId = this.value;
        if (!facultadId || !/^\d+$/.test(facultadId)) {
            carreraSelect.innerHTML = '<option value="">Seleccionar carrera</option><option value="otro">Otro</option>';
            facultadDependentsPromise = Promise.resolve();
            return;
        }
        facultadDependentsPromise = fetch(CFG.urls.getCareersByFacultyBase + facultadId + '/')
            .then(function (r) { return r.json(); })
            .then(function (data) {
                carreraSelect.innerHTML = '<option value="">Seleccionar carrera</option><option value="otro">Otro</option>';
                (data.careers || []).forEach(function (c) {
                    var opt = document.createElement('option');
                    opt.value = c.id; opt.textContent = c.name;
                    carreraSelect.appendChild(opt);
                });
            });
    });

    // ── Autocompletar desde plantilla elegida ────────────────────────────
    function markFromTemplate(inputId) {
        var el = document.getElementById(inputId);
        if (!el) return;
        el.classList.add('wiz-from-template');
        var label = document.querySelector('label[for="' + inputId + '"]');
        if (label && !label.querySelector('.wiz-badge-template')) {
            var badge = document.createElement('span');
            badge.className = 'badge bg-success ms-1 wiz-badge-template';
            badge.textContent = 'De la plantilla';
            label.appendChild(badge);
        }
    }

    document.getElementById('plantilla').addEventListener('change', async function () {
        var plantillaId = this.value;
        if (!plantillaId) return;

        var response = await fetch(CFG.urls.getExamTemplateBase + plantillaId + '/');
        if (!response.ok) return;
        var data = await response.json();

        if (data.instructions) {
            document.getElementById('id_instructions').value = data.instructions;
            markFromTemplate('id_instructions');
        }
        if (data.duration_minutes) {
            durationInput.value = data.duration_minutes;
            markFromTemplate('id_duration_minutes');
        }

        if (data.subject_id) {
            subjectSelect.value = data.subject_id;
            topicsToPreselect = [];
            questionsToPreselect = Array.isArray(data.questions) ? data.questions : [];
            markFromTemplate('id_subject');
            await loadSubjectDependents(data.subject_id, [], questionsToPreselect);
        }

        if (Array.isArray(data.learning_outcomes) && data.learning_outcomes.length) {
            document.querySelectorAll('#learning_outcomes_container input[type="checkbox"]').forEach(function (cb) {
                cb.checked = data.learning_outcomes.includes(parseInt(cb.value, 10));
            });
        }

        var rubricsContainer = document.getElementById('rubrics_checkbox_container');
        if (rubricsContainer && Array.isArray(data.rubric_ids) && data.rubric_ids.length) {
            var templateRubricIds = data.rubric_ids.map(String);
            rubricsContainer.querySelectorAll('input[name="rubric_ids"]').forEach(function (cb) {
                cb.checked = templateRubricIds.includes(cb.value);
            });
            markFromTemplate('rubrics_checkbox_container');
        }

        if (data.institution_id) {
            institucionSelect.value = data.institution_id;
            institucionSelect.dispatchEvent(new Event('change'));
            markFromTemplate('institucion_dropdown');
            openInstitucionBlock();
            await institucionDependentsPromise;
        }
        if (data.faculty_id) {
            facultadSelect.value = data.faculty_id;
            facultadSelect.dispatchEvent(new Event('change'));
            markFromTemplate('facultad_dropdown');
            await facultadDependentsPromise;
        }
        if (data.career_id) {
            var found = Array.from(carreraSelect.options).some(function (o) { return o.value == data.career_id; });
            if (found) {
                carreraSelect.value = data.career_id;
            } else {
                try {
                    var careerResp = await fetch(CFG.urls.getCareerNameBase + data.career_id + '/');
                    var careerData = await careerResp.json();
                    var opt = document.createElement('option');
                    opt.value = data.career_id;
                    opt.textContent = careerData.name + ' (no asociada)';
                    opt.selected = true;
                    carreraSelect.appendChild(opt);
                } catch (e) { /* no-op: la carrera queda sin preseleccionar */ }
            }
            markFromTemplate('carrera_dropdown');
        }
        if (data.campus_id) {
            sedeSelect.value = data.campus_id;
            markFromTemplate('sede_dropdown');
        }
        if (data.professor_id) {
            document.getElementById('profesor_dropdown').value = data.professor_id;
            markFromTemplate('profesor_dropdown');
        }
        if (data.exam_type) {
            document.getElementById('tipo_examen_select').value = data.exam_type;
            markFromTemplate('tipo_examen_select');
        }
        if (data.exam_mode) {
            var radio = document.querySelector('input[name="tipo_modalidad"][value="' + data.exam_mode + '"]');
            if (radio) radio.checked = true;
        }
        if (data.shift) {
            document.getElementById('turno_dropdown').value = data.shift;
        }

        updateSuggestedBatchName();
    });

    function toggleTextboxGlobal(selectId, textboxId) {
        var select = document.getElementById(selectId);
        var textbox = document.getElementById(textboxId);
        textbox.classList.toggle('d-none', select.value !== 'otro');
    }
    window.toggleTextbox = toggleTextboxGlobal;

    showStep(1);
});
