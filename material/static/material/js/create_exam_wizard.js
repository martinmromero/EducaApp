// create_exam_wizard.js
// Asistente paso a paso para "Crear Examen" (material/exams/create_exam_wizard.html).
// Página nueva e independiente de create_exam.js: mismos endpoints, DOM distinto
// (un paso visible a la vez + selector de tópicos/preguntas coloreado por tópico).

// document.addEventListener('DOMContentLoaded', fn) a secas no alcanza: si
// el evento ya disparó para cuando este script corre, el callback nunca se
// ejecuta sin ningún error visible (encontrado en create_exam_template_wizard.js,
// mismo patrón acá por las dudas).
function _onDomReady(fn) {
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', fn);
    } else {
        fn();
    }
}

_onDomReady(function () {
    var CFG = window.EducaAppWizardConfig || { urls: {} };
    var wireCatalogSearch = window.EducaAppWizardCatalogSearch.wireCatalogSearch;
    var clearCatalogField = window.EducaAppWizardCatalogSearch.clearCatalogField;

    // ── Navegación entre pasos: motor genérico, ver wizard_engine.js ────
    function validateStep(n) {
        if (n === 2) {
            var subject = document.getElementById('id_subject');
            if (subject && !subject.value) {
                subject.reportValidity ? subject.reportValidity() : alert('Falta seleccionar una materia para continuar.');
                return false;
            }
        }
        return true;
    }

    var wizardCtrl = window.EducaAppWizard.init({
        totalSteps: 6,
        onValidateStep: validateStep,
        onEnterFinalStep: function () { renderSummary(); },
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
        if (willShow) loadCatalogTree();
    });
    function openInstitucionBlock() {
        institucionBlock.classList.remove('d-none');
        institucionToggleBtn.textContent = '– Ocultar institución, facultad, carrera y sede';
        loadCatalogTree();
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
        var institutionSearchInput = document.getElementById('institucion_search');
        var institutionLabel = (institutionSearchInput && institutionSearchInput.value.trim()) || 'sin institucion';
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
            wrap.innerHTML = '<div class="wiz-questions-empty">Seleccionar al menos un tópico arriba para ver sus preguntas acá.</div>';
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

            // La plantilla (get-exam-template) no expone qué tópicos usaba,
            // solo qué preguntas — se derivan los tópicos a partir del
            // topic_id de esas preguntas (ya viene en allQuestionsCache) en
            // vez de depender de un preselectTopics que nunca llega con
            // datos. Sin esto, elegir una plantilla dejaba el paso 3 sin
            // ningún tópico tildado y perdía en silencio las preguntas de
            // la plantilla.
            var topicsToCheck = (preselectTopics && preselectTopics.length) ? preselectTopics.map(String) : [];
            if (!topicsToCheck.length && preselectQuestions && preselectQuestions.length) {
                var preselectQuestionIdSet = preselectQuestions.map(String);
                var derivedTopicIds = allQuestionsCache
                    .filter(function (q) { return preselectQuestionIdSet.includes(String(q.id)); })
                    .map(function (q) { return String(q.topic_id); });
                topicsToCheck = Array.from(new Set(derivedTopicIds));
            }
            if (topicsToCheck.length) {
                document.querySelectorAll('#wizTopicsList input[type="checkbox"]').forEach(function (cb) {
                    cb.checked = topicsToCheck.includes(cb.dataset.topicValue);
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
        loadCatalogTree();
    });

    // ── Institución/facultad/carrera: buscador contra el catálogo ────────
    // Mismo motor que Solicitar Alta y el buscador de materias de /upload/
    // (check_catalog_duplicate — catálogo institucional + espacio personal
    // propio, nunca el de otro usuario). Si lo tipeado no matchea nada, se
    // usa tal cual como texto libre para el encabezado impreso — acá no se
    // crea ninguna fila nueva de catálogo, a diferencia de Solicitar Alta.
    var sedeSelect = document.getElementById('sede_dropdown');
    var institucionHidden = document.getElementById('institucion_dropdown');
    var facultadHidden = document.getElementById('facultad_dropdown');
    var carreraHidden = document.getElementById('carrera_dropdown');

    var institucionSearch = wireCatalogSearch({
        searchInput: document.getElementById('institucion_search'),
        suggestBox: document.getElementById('institucion_suggest'),
        hiddenInput: institucionHidden,
        nivel: 'institucion',
    });
    var facultadSearch = wireCatalogSearch({
        searchInput: document.getElementById('facultad_search'),
        suggestBox: document.getElementById('facultad_suggest'),
        hiddenInput: facultadHidden,
        nivel: 'facultad',
        getScopeParams: function () {
            return /^\d+$/.test(institucionHidden.value) ? { institucion_id: institucionHidden.value } : {};
        },
    });
    var carreraSearch = wireCatalogSearch({
        searchInput: document.getElementById('carrera_search'),
        suggestBox: document.getElementById('carrera_suggest'),
        hiddenInput: carreraHidden,
        nivel: 'carrera',
        getScopeParams: function () {
            return /^\d+$/.test(facultadHidden.value) ? { facultad_id: facultadHidden.value } : {};
        },
    });

    // ── Institución/facultad/carrera sugeridas a partir de la materia ────
    // La materia ya se eligió en el paso 2 — en vez de arrancar los 3
    // buscadores en blanco acá en el paso 4, se ofrece un <select> por
    // nivel con las instituciones/facultades/carreras donde esa materia ya
    // aparece (vía sus carreras), en cascada (facultad según la institución
    // elegida, carrera según la facultad elegida). Sin sugerencias en un
    // nivel (materia personal sin carrera asociada, o "Otro" elegido) ese
    // nivel cae directo al buscador libre de catálogo de siempre.
    var institucionSelect = document.getElementById('institucion_select');
    var facultadSelect = document.getElementById('facultad_select');
    var carreraSelect = document.getElementById('carrera_select');
    var institucionSearchWrap = document.getElementById('institucion_search_wrap');
    var facultadSearchWrap = document.getElementById('facultad_search_wrap');
    var carreraSearchWrap = document.getElementById('carrera_search_wrap');
    var catalogTree = [];

    function findInTree(institucionId) {
        return catalogTree.find(function (i) { return String(i.id) === String(institucionId); });
    }

    // Puebla un <select> de sugeridos; si no hay ninguna, lo oculta entero y
    // deja visible directo el buscador libre (mismo comportamiento que
    // siempre hubo cuando no había sugerencias).
    function populateSuggestSelect(selectEl, wrapEl, items, placeholder) {
        selectEl.innerHTML = '';
        var opt0 = document.createElement('option');
        opt0.value = '';
        opt0.textContent = placeholder;
        selectEl.appendChild(opt0);
        items.forEach(function (item) {
            var opt = document.createElement('option');
            opt.value = item.id;
            opt.textContent = item.name;
            selectEl.appendChild(opt);
        });
        var optOtro = document.createElement('option');
        optOtro.value = '__otro__';
        optOtro.textContent = 'Otro (buscar o escribir)';
        selectEl.appendChild(optOtro);

        if (items.length) {
            selectEl.classList.remove('d-none');
            wrapEl.classList.add('d-none');
        } else {
            selectEl.classList.add('d-none');
            wrapEl.classList.remove('d-none');
        }
    }

    function loadCatalogTree() {
        var subjectId = document.getElementById('id_subject').value;
        if (!subjectId || !/^\d+$/.test(subjectId) || !CFG.urls.getCatalogTreeForSubjectBase) {
            catalogTree = [];
            populateSuggestSelect(institucionSelect, institucionSearchWrap, [], 'Seleccionar institución');
            populateSuggestSelect(facultadSelect, facultadSearchWrap, [], 'Seleccionar facultad');
            populateSuggestSelect(carreraSelect, carreraSearchWrap, [], 'Seleccionar carrera');
            return Promise.resolve();
        }
        return fetch(CFG.urls.getCatalogTreeForSubjectBase + subjectId + '/')
            .then(function (r) { return r.json(); })
            .catch(function () { return { institutions: [] }; })
            .then(function (data) {
                catalogTree = data.institutions || [];
                populateSuggestSelect(institucionSelect, institucionSearchWrap, catalogTree, 'Seleccionar institución');
                populateSuggestSelect(facultadSelect, facultadSearchWrap, [], 'Seleccionar facultad');
                populateSuggestSelect(carreraSelect, carreraSearchWrap, [], 'Seleccionar carrera');
            });
    }

    institucionSelect.addEventListener('change', function () {
        var val = this.value;
        if (val === '__otro__') {
            institucionSearchWrap.classList.remove('d-none');
            document.getElementById('institucion_search').value = '';
            document.getElementById('institucion_search').focus();
            institucionHidden.value = '';
            institucionHidden.dispatchEvent(new Event('change'));
            return;
        }
        institucionSearchWrap.classList.add('d-none');
        if (val) {
            var entry = findInTree(val);
            institucionSearch.setValue(val, entry ? entry.name : this.options[this.selectedIndex].textContent);
        }
        institucionHidden.value = val;
        institucionHidden.dispatchEvent(new Event('change'));
    });

    facultadSelect.addEventListener('change', function () {
        var val = this.value;
        if (val === '__otro__') {
            facultadSearchWrap.classList.remove('d-none');
            document.getElementById('facultad_search').value = '';
            document.getElementById('facultad_search').focus();
            facultadHidden.value = '';
            facultadHidden.dispatchEvent(new Event('change'));
            return;
        }
        facultadSearchWrap.classList.add('d-none');
        if (val) {
            var instEntry = findInTree(institucionHidden.value);
            var facEntry = instEntry && instEntry.faculties.find(function (f) { return String(f.id) === String(val); });
            facultadSearch.setValue(val, facEntry ? facEntry.name : this.options[this.selectedIndex].textContent);
        }
        facultadHidden.value = val;
        facultadHidden.dispatchEvent(new Event('change'));
    });

    carreraSelect.addEventListener('change', function () {
        var val = this.value;
        if (val === '__otro__') {
            carreraSearchWrap.classList.remove('d-none');
            document.getElementById('carrera_search').value = '';
            document.getElementById('carrera_search').focus();
            carreraHidden.value = '';
            carreraHidden.dispatchEvent(new Event('change'));
            return;
        }
        carreraSearchWrap.classList.add('d-none');
        if (val) {
            var instEntry = findInTree(institucionHidden.value);
            var facEntry = instEntry && instEntry.faculties.find(function (f) { return String(f.id) === String(facultadHidden.value); });
            var carEntry = facEntry && facEntry.careers.find(function (c) { return String(c.id) === String(val); });
            carreraSearch.setValue(val, carEntry ? carEntry.name : this.options[this.selectedIndex].textContent);
        }
        carreraHidden.value = val;
        carreraHidden.dispatchEvent(new Event('change'));
    });

    // Cambiar la institución invalida facultad/carrera elegidas (dependen del
    // contexto de arriba), repuebla el dropdown de facultad sugerida acorde
    // y recarga las sedes disponibles, igual que antes. Extraída como función
    // (devuelve la promise del fetch de sedes) para poder reutilizarla desde
    // el restore de borrador (ver wizard_draft.js más abajo), que necesita
    // esperar a que las sedes terminen de cargar antes de elegir una.
    function applyInstitucionChange(institucionId) {
        clearCatalogField(document.getElementById('facultad_search'), facultadHidden);
        clearCatalogField(document.getElementById('carrera_search'), carreraHidden);
        var instEntry = findInTree(institucionId);
        populateSuggestSelect(facultadSelect, facultadSearchWrap, (instEntry && instEntry.faculties) || [], 'Seleccionar facultad');
        populateSuggestSelect(carreraSelect, carreraSearchWrap, [], 'Seleccionar carrera');
        sedeSelect.innerHTML = '<option value="">Seleccionar sede</option><option value="otro">Otro</option>';
        updateSuggestedBatchName();
        if (/^\d+$/.test(institucionId)) {
            return fetch(CFG.urls.getCampusesByInstitutionBase + institucionId + '/')
                .then(function (r) { return r.json(); })
                .then(function (data) {
                    sedeSelect.innerHTML = '<option value="">Seleccionar sede</option><option value="otro">Otro</option>';
                    (data.campuses || []).forEach(function (c) {
                        var opt = document.createElement('option');
                        opt.value = c.id; opt.textContent = c.name;
                        sedeSelect.appendChild(opt);
                    });
                });
        }
        return Promise.resolve();
    }
    institucionHidden.addEventListener('change', function () { applyInstitucionChange(this.value); });

    function applyFacultadChange(facultadId) {
        clearCatalogField(document.getElementById('carrera_search'), carreraHidden);
        var instEntry = findInTree(institucionHidden.value);
        var facEntry = instEntry && instEntry.faculties.find(function (f) { return String(f.id) === String(facultadId); });
        populateSuggestSelect(carreraSelect, carreraSearchWrap, (facEntry && facEntry.careers) || [], 'Seleccionar carrera');
    }
    facultadHidden.addEventListener('change', function () { applyFacultadChange(this.value); });

    // ── Aplicar institución/facultad/carrera desde una fuente externa
    // (plantilla elegida o borrador recuperado) ─────────────────────────
    // Mismo criterio en los 3 niveles: si el id está entre las sugeridas
    // por la materia actual (catalogTree) se usa el <select> con ese id;
    // si no, cae a "Otro" con el buscador libre mostrando el nombre tal
    // cual vino. Factorizado acá porque plantilla y borrador necesitan
    // exactamente la misma lógica (antes vivía duplicada solo en el
    // handler de "plantilla").
    function applyInstitucionSelection(institutionId, institutionName) {
        var instEntry = findInTree(institutionId);
        if (instEntry) {
            institucionSelect.value = String(institutionId);
            institucionSearchWrap.classList.add('d-none');
        } else {
            institucionSelect.value = '__otro__';
            institucionSearchWrap.classList.remove('d-none');
        }
        institucionSearch.setValue(institutionId, institutionName || (instEntry && instEntry.name) || '');
        institucionHidden.value = institutionId;
        return applyInstitucionChange(institutionId);
    }
    function applyFacultadSelection(facultyId, facultyName) {
        var instEntry = findInTree(institucionHidden.value);
        var facEntry = instEntry && instEntry.faculties.find(function (f) { return String(f.id) === String(facultyId); });
        if (facEntry) {
            facultadSelect.value = String(facultyId);
            facultadSearchWrap.classList.add('d-none');
        } else {
            facultadSelect.value = '__otro__';
            facultadSearchWrap.classList.remove('d-none');
        }
        facultadSearch.setValue(facultyId, facultyName || (facEntry && facEntry.name) || '');
        facultadHidden.value = facultyId;
        applyFacultadChange(facultyId);
    }
    function applyCarreraSelection(careerId, careerName) {
        var instEntry = findInTree(institucionHidden.value);
        var facEntry = instEntry && instEntry.faculties.find(function (f) { return String(f.id) === String(facultadHidden.value); });
        var carEntry = facEntry && facEntry.careers.find(function (c) { return String(c.id) === String(careerId); });
        if (carEntry) {
            carreraSelect.value = String(careerId);
            carreraSearchWrap.classList.add('d-none');
        } else {
            carreraSelect.value = '__otro__';
            carreraSearchWrap.classList.remove('d-none');
        }
        carreraSearch.setValue(careerId, careerName || (carEntry && carEntry.name) || '');
        carreraHidden.value = careerId;
    }

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

        // Refleja la materia recién aplicada (si la hubo) antes de decidir
        // si institución/facultad/carrera de la plantilla están entre las
        // sugeridas por esa materia o si caen al buscador libre ("Otro").
        await loadCatalogTree();

        if (data.institution_id) {
            await applyInstitucionSelection(data.institution_id, data.institution_name);
            markFromTemplate('institucion_select');
            openInstitucionBlock();
        }
        if (data.faculty_id) {
            applyFacultadSelection(data.faculty_id, data.faculty_name);
            markFromTemplate('facultad_select');
        }
        if (data.career_id) {
            // A diferencia de institución/facultad, una carrera puede no
            // estar asociada a la facultad de la plantilla (ver comentario
            // histórico de esta pantalla) — no hace falta resolverlo acá:
            // el nombre ya viene en la respuesta de get_exam_template.
            applyCarreraSelection(data.career_id, data.career_name);
            markFromTemplate('carrera_select');
        }
        if (data.campus_id) {
            // Recién acá, después de esperar applyInstitucionSelection (que
            // ahora sí se espera con await), sedeSelect ya tiene las sedes
            // de la institución cargadas — antes esto se ejecutaba en
            // paralelo con el fetch de sedes y podía perder la selección.
            sedeSelect.value = data.campus_id;
            markFromTemplate('sede_dropdown');
        }
        if (data.professor_id) {
            document.getElementById('profesor_dropdown').value = data.professor_id;
            markFromTemplate('profesor_dropdown');
        }
        if (data.catedra) {
            document.getElementById('catedra').value = data.catedra;
            markFromTemplate('catedra');
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

    // ── Backup a sessionStorage (mismo motor que los otros 3 wizards, ver
    // wizard_draft.js) — este es el más largo de los 4 (6 pasos, catálogo
    // institución/facultad/carrera/sede, selector de preguntas coloreado),
    // así que es el que más se perdía con un F5 accidental. No se guarda
    // la plantilla elegida en sí (paso 1): se guarda el resultado ya
    // aplicado en los pasos siguientes, así el restore no depende de
    // volver a resolver la plantilla contra el servidor. ─────────────────
    var draft = window.EducaAppWizardDraft.init('educaapp_exam_wizard_draft');

    function checkedValues(containerId, selector) {
        var container = document.getElementById(containerId);
        if (!container) return [];
        return Array.from(container.querySelectorAll(selector || 'input[type="checkbox"]:checked')).map(function (cb) { return cb.value; });
    }

    function saveDraft() {
        draft.save({
            subject: subjectSelect.value,
            topicIds: getSelectedTopicIds(),
            questionIds: selectedQuestionIds,
            learningOutcomeIds: checkedValues('learning_outcomes_container'),
            profesorDropdown: document.getElementById('profesor_dropdown').value,
            profesorText: document.getElementById('profesor_text').value,
            fecha: document.getElementById('fecha').value,
            duration: durationInput.value,
            durationUnit: durationUnit.value,
            year: yearInput.value,
            periodoNumero: periodoNumero.value,
            periodoTipo: periodoTipo.value,
            institucionBlockOpen: !institucionBlock.classList.contains('d-none'),
            institucion: institucionHidden.value,
            institucionLabel: document.getElementById('institucion_search').value,
            facultad: facultadHidden.value,
            facultadLabel: document.getElementById('facultad_search').value,
            carrera: carreraHidden.value,
            carreraLabel: document.getElementById('carrera_search').value,
            sede: sedeSelect.value,
            sedeText: document.getElementById('sede_text').value,
            curso: document.getElementById('curso').value,
            catedra: document.getElementById('catedra').value,
            turno: document.getElementById('turno_dropdown').value,
            turnoText: document.getElementById('turno_text').value,
            tipoExamen: document.getElementById('tipo_examen_select').value,
            modalidad: (document.querySelector('input[name="tipo_modalidad"]:checked') || {}).value || '',
            modalidadResolucion: Array.from(document.querySelectorAll('input[name="modalidad_resolucion"]:checked')).map(function (cb) { return cb.value; }),
            batchName: batchNameInput.value,
            batchNameUserEdited: batchNameInput.dataset.userEdited === '1',
            instructions: document.getElementById('id_instructions').value,
            numVersions: document.getElementById('num_versions').value,
            questionsPerVersion: document.getElementById('questions_per_version').value,
            balanceByTopic: document.getElementById('balance_by_topic').checked,
            rubricIds: checkedValues('rubrics_checkbox_container', 'input[name="rubric_ids"]:checked'),
        });
    }
    wizForm.addEventListener('change', saveDraft);
    wizForm.addEventListener('input', saveDraft);

    function restoreDraft() {
        var saved = draft.load();
        if (!saved || !saved.subject) return;

        draft.confirmRestore('Encontramos un examen sin terminar de una sesión anterior. ¿Querés recuperarlo?').then(function (quiere) {
            if (!quiere) { draft.clear(); return; }

            subjectSelect.value = saved.subject;
            loadSubjectDependents(saved.subject, saved.topicIds, saved.questionIds).then(function () {
                (saved.learningOutcomeIds || []).forEach(function (id) {
                    var cb = document.getElementById('wiz_outcome_' + id);
                    if (cb) cb.checked = true;
                });

                document.getElementById('profesor_dropdown').value = saved.profesorDropdown || '';
                document.getElementById('profesor_text').value = saved.profesorText || '';
                document.getElementById('fecha').value = saved.fecha || '';
                durationInput.value = saved.duration || '';
                durationUnit.value = saved.durationUnit || 'minutos';
                yearInput.value = saved.year || '';
                periodoNumero.value = saved.periodoNumero || '';
                periodoTipo.value = saved.periodoTipo || 'Cuatrimestre';
                syncPeriodo();

                document.getElementById('curso').value = saved.curso || '';
                document.getElementById('catedra').value = saved.catedra || '';
                document.getElementById('turno_dropdown').value = saved.turno || '';
                document.getElementById('turno_text').value = saved.turnoText || '';
                toggleTextboxGlobal('turno_dropdown', 'turno_text');
                document.getElementById('tipo_examen_select').value = saved.tipoExamen || '';
                if (saved.modalidad) {
                    var modalidadRadio = document.querySelector('input[name="tipo_modalidad"][value="' + saved.modalidad + '"]');
                    if (modalidadRadio) modalidadRadio.checked = true;
                }
                (saved.modalidadResolucion || []).forEach(function (val) {
                    var cb = document.querySelector('input[name="modalidad_resolucion"][value="' + val + '"]');
                    if (cb) cb.checked = true;
                });
                batchNameInput.value = saved.batchName || '';
                batchNameInput.dataset.userEdited = saved.batchNameUserEdited ? '1' : '0';
                document.getElementById('id_instructions').value = saved.instructions || '';
                document.getElementById('num_versions').value = saved.numVersions || '1';
                document.getElementById('questions_per_version').value = saved.questionsPerVersion || '';
                document.getElementById('balance_by_topic').checked = saved.balanceByTopic !== false;
                (saved.rubricIds || []).forEach(function (id) {
                    var cb = document.querySelector('#rubrics_checkbox_container input[name="rubric_ids"][value="' + id + '"]');
                    if (cb) cb.checked = true;
                });

                return loadCatalogTree();
            }).then(function () {
                if (saved.institucion) {
                    if (saved.institucionBlockOpen) openInstitucionBlock();
                    return applyInstitucionSelection(saved.institucion, saved.institucionLabel).then(function () {
                        if (saved.facultad) applyFacultadSelection(saved.facultad, saved.facultadLabel);
                        if (saved.carrera) applyCarreraSelection(saved.carrera, saved.carreraLabel);
                        if (saved.sede) sedeSelect.value = saved.sede;
                        document.getElementById('sede_text').value = saved.sedeText || '';
                        toggleTextboxGlobal('sede_dropdown', 'sede_text');
                    });
                }
                return Promise.resolve();
            }).then(function () {
                wizardCtrl.goNext();
                wizardCtrl.goNext();
                wizardCtrl.goNext();
                wizardCtrl.goNext();
                wizardCtrl.goNext();
            });
        });
    }

    wizForm.addEventListener('submit', function () { draft.clear(); });
    var startOverLink = document.querySelector('a[href*="limpiar=1"]');
    if (startOverLink) startOverLink.addEventListener('click', function () { draft.clear(); });

    wizardCtrl.goToStep(1);
    restoreDraft();
});
