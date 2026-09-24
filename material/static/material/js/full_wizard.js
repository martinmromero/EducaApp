// full_wizard.js — Asistente completo (institución -> facultad -> carrera ->
// materia -> resultados de aprendizaje -> contenidos -> preguntas -> examen).
// A diferencia de los otros 4 wizards (Examen/Oral/Plantilla/Institución),
// cada paso persiste de inmediato contra el servidor (full_wizard_save_step,
// mismo motor que Solicitar Alta) en vez de juntar todo para un submit final
// — ver el porqué en el plan de [[project_combined_onboarding_wizard_design]].
// Por eso NO usa wizard_engine.js para decidir CUÁNDO avanzar (su
// onValidateStep es síncrono, acá cada avance depende de una respuesta de
// red) — sí lo usa para el look & feel del stepper (pills, mostrar/ocultar
// paneles), llamando wizardCtrl.goNext()/goBack() a mano una vez que el
// POST del paso ya resolvió.
(function () {
    var CFG = window.EducaAppFullWizardConfig || { urls: {} };
    var DRAFT_KEY = 'full_wizard_draft_v1';

    var LABELS = { institucion: 'Institución', facultad: 'Facultad', carrera: 'Carrera', materia: 'Materia' };

    var STATE = {
        institucion: null, // {id, name, skipped}
        facultad: null,
        carrera: null,
        materia: null,
        outcomes: [], // [{id, description}]
    };

    function getCookie(name) {
        var v = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
        return v ? v.pop() : '';
    }

    function postStep(payload) {
        return fetch(CFG.urls.saveStep, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
            body: JSON.stringify(payload),
        }).then(function (r) {
            return r.json().then(function (data) { return { status: r.status, data: data }; });
        });
    }

    function contextPayload() {
        return {
            institucion_id: STATE.institucion && !STATE.institucion.skipped ? STATE.institucion.id : null,
            facultad_id: STATE.facultad && !STATE.facultad.skipped ? STATE.facultad.id : null,
            carrera_id: STATE.carrera && !STATE.carrera.skipped ? STATE.carrera.id : null,
            materia_id: STATE.materia && !STATE.materia.skipped ? STATE.materia.id : null,
        };
    }

    function panelFor(n) {
        return document.querySelector('.wiz-step[data-step="' + n + '"]');
    }
    function role(panel, name) {
        return panel.querySelector('[data-role="' + name + '"]');
    }

    function renderBreadcrumb() {
        var el = document.getElementById('fwBreadcrumb');
        if (!el) return;
        var parts = [];
        ['institucion', 'facultad', 'carrera', 'materia'].forEach(function (key) {
            var v = STATE[key];
            if (v === null) return;
            if (v.skipped) {
                parts.push('<span class="fw-crumb fw-crumb-skip">' + LABELS[key] + ': salteado</span>');
            } else {
                parts.push('<span class="fw-crumb"><i class="bi bi-check-circle-fill text-success me-1"></i>' + v.name + '</span>');
            }
        });
        if (STATE.outcomes.length) {
            parts.push('<span class="fw-crumb"><i class="bi bi-check-circle-fill text-success me-1"></i>' + STATE.outcomes.length + ' resultado(s) de aprendizaje</span>');
        }
        el.innerHTML = parts.join(' <span class="text-muted">›</span> ');
    }

    var draft = window.EducaAppWizardDraft ? window.EducaAppWizardDraft.init(DRAFT_KEY) : null;
    function saveDraft() {
        if (draft) draft.save(STATE);
    }

    var wizardCtrl = null;

    // ---- Pasos 1-4: Institución / Facultad / Carrera / Materia ----------
    // hint: explica, ANTES de elegir, qué efecto tiene saltear este paso en
    // los pasos siguientes — pedido explícito del usuario ("entendiendo cómo
    // se conectan entre sí"), mismo criterio para los 4 niveles + RA.
    var CATALOG_STEPS = [
        {
            n: 1, key: 'institucion', label: 'Institución', parentKey: null, hardParent: false,
            listKey: 'institutions',
            loadUrl: function () { return CFG.urls.listInstituciones; },
            hint: 'Si salteás este paso, tampoco vas a poder cargar una Facultad nueva en el paso siguiente (necesita una Institución elegida acá) — ese paso también quedaría salteado.',
        },
        {
            n: 2, key: 'facultad', label: 'Facultad', parentKey: 'institucion', hardParent: true,
            listKey: 'faculties',
            loadUrl: function (parentId) { return CFG.urls.facultadesByInstitucionBase + parentId + '/'; },
            hint: 'Si salteás este paso, la Carrera del paso siguiente se puede crear igual, pero sin esta Facultad asociada.',
        },
        {
            n: 3, key: 'carrera', label: 'Carrera', parentKey: 'facultad', hardParent: false,
            listKey: 'careers',
            loadUrl: function (parentId) { return CFG.urls.carrerasByFacultadBase + parentId + '/'; },
            hint: 'Si salteás este paso, la Materia del paso siguiente se puede crear igual, pero sin esta Carrera asociada.',
        },
        {
            n: 4, key: 'materia', label: 'Materia', parentKey: 'carrera', hardParent: false,
            listKey: 'subjects',
            loadUrl: function (parentId) { return CFG.urls.materiasByCarreraBase + parentId + '/'; },
            hint: 'Importante: los pasos siguientes (Contenido, Preguntas y Examen) usan la materia elegida acá. Si salteás este paso, vas a tener que elegirla o crearla de nuevo en cada pantalla siguiente.',
        },
    ];

    function scopeParamsFor(key) {
        var params = {};
        if (key === 'facultad' && STATE.institucion && !STATE.institucion.skipped) params.institucion_id = STATE.institucion.id;
        if (key === 'carrera' && STATE.facultad && !STATE.facultad.skipped) params.facultad_id = STATE.facultad.id;
        if (key === 'materia' && STATE.carrera && !STATE.carrera.skipped) params.carrera_id = STATE.carrera.id;
        return params;
    }

    function setupCatalogStep(cfgStep) {
        var panel = panelFor(cfgStep.n);
        var titleEl = role(panel, 'title');
        var hintEl = role(panel, 'step-hint');
        var parentMsgEl = role(panel, 'parent-message');
        var chipListEl = role(panel, 'chip-list');
        var listEmptyEl = role(panel, 'list-empty-msg');
        var searchInput = role(panel, 'search-input');
        var suggestBox = role(panel, 'suggest-box');
        var createBtn = role(panel, 'create-btn');
        var skipBtn = role(panel, 'skip-btn');
        var errorEl = role(panel, 'error-msg');

        titleEl.textContent = cfgStep.label;
        if (cfgStep.hint) {
            hintEl.textContent = cfgStep.hint;
            hintEl.style.display = 'block';
        }

        function showError(msg) {
            errorEl.textContent = msg || '';
            errorEl.style.display = msg ? 'block' : 'none';
        }

        function setBusy(busy) {
            createBtn.disabled = busy || !searchInput.value.trim();
            skipBtn.disabled = busy;
            searchInput.disabled = busy;
        }

        function advance() {
            renderBreadcrumb();
            saveDraft();
            wizardCtrl.goNext();
        }

        function confirmExisting(id, name) {
            showError('');
            setBusy(true);
            postStep(Object.assign({ step: cfgStep.key, action: 'existente', existing_id: id }, contextPayload()))
                .then(function (res) {
                    setBusy(false);
                    if (!res.data.ok) { showError(res.data.error || 'No se pudo guardar.'); return; }
                    STATE[cfgStep.key] = { id: res.data.id, name: res.data.name, skipped: false };
                    advance();
                })
                .catch(function () { setBusy(false); showError('Error de red — reintentar.'); });
        }

        function renderChips(items) {
            chipListEl.innerHTML = '';
            if (!items.length) {
                listEmptyEl.style.display = 'block';
                return;
            }
            listEmptyEl.style.display = 'none';
            items.forEach(function (item) {
                var chip = document.createElement('button');
                chip.type = 'button';
                chip.className = 'fw-chip';
                var esPersonal = item.es_catalogo_institucional === false;
                var badgeTxt = esPersonal ? 'Personal' : 'Catálogo';
                var nameSpan = document.createElement('span');
                nameSpan.textContent = item.name;
                var badgeSpan = document.createElement('span');
                badgeSpan.className = 'badge bg-secondary-subtle text-secondary-emphasis';
                badgeSpan.textContent = badgeTxt;
                chip.appendChild(nameSpan);
                chip.appendChild(badgeSpan);
                chip.addEventListener('click', function () { confirmExisting(item.id, item.name); });
                chipListEl.appendChild(chip);
            });
        }

        function loadList() {
            showError('');
            suggestBox.classList.add('d-none');
            suggestBox.innerHTML = '';
            searchInput.value = '';
            createBtn.disabled = true;

            if (!cfgStep.parentKey) {
                parentMsgEl.textContent = '';
                searchInput.disabled = false;
                fetch(cfgStep.loadUrl())
                    .then(function (r) { return r.json(); })
                    .then(function (data) { renderChips(data[cfgStep.listKey] || []); })
                    .catch(function () { renderChips([]); });
                return;
            }

            var parentState = STATE[cfgStep.parentKey];
            var parentId = parentState && !parentState.skipped ? parentState.id : null;

            if (!parentId) {
                if (cfgStep.hardParent) {
                    parentMsgEl.textContent = 'No se puede cargar ' + cfgStep.label.toLowerCase() + ' sin ' + LABELS[cfgStep.parentKey].toLowerCase() + ' — salteá este paso.';
                    chipListEl.innerHTML = '';
                    listEmptyEl.style.display = 'none';
                    searchInput.disabled = true;
                    return;
                }
                parentMsgEl.textContent = 'No se especificó ' + LABELS[cfgStep.parentKey].toLowerCase() + ' — buscando en todo tu catálogo visible en vez de acotar.';
                searchInput.disabled = false;
                renderChips([]);
                return;
            }

            parentMsgEl.textContent = '';
            searchInput.disabled = false;
            fetch(cfgStep.loadUrl(parentId))
                .then(function (r) { return r.json(); })
                .then(function (data) { renderChips(data[cfgStep.listKey] || []); })
                .catch(function () { renderChips([]); });
        }

        var searchDebounce;
        searchInput.addEventListener('input', function () {
            createBtn.disabled = !searchInput.value.trim();
            var q = searchInput.value.trim();
            clearTimeout(searchDebounce);
            if (q.length < 2) { suggestBox.classList.add('d-none'); suggestBox.innerHTML = ''; return; }
            searchDebounce = setTimeout(function () {
                var params = Object.assign({ nivel: cfgStep.key, q: q }, scopeParamsFor(cfgStep.key));
                fetch(CFG.urls.checkCatalogDuplicate + '?' + new URLSearchParams(params).toString())
                    .then(function (r) { return r.json(); })
                    .then(function (items) {
                        suggestBox.innerHTML = '';
                        if (!items.length) { suggestBox.classList.add('d-none'); return; }
                        items.forEach(function (item) {
                            var row = document.createElement('div');
                            row.className = 'fw-suggest-item';
                            var span = document.createElement('span');
                            span.textContent = item.name;
                            row.appendChild(span);
                            row.addEventListener('mousedown', function (e) {
                                e.preventDefault();
                                searchInput.value = item.name;
                                suggestBox.classList.add('d-none');
                                confirmExisting(item.id, item.name);
                            });
                            suggestBox.appendChild(row);
                        });
                        suggestBox.classList.remove('d-none');
                    })
                    .catch(function () {});
            }, 300);
        });
        searchInput.addEventListener('blur', function () {
            setTimeout(function () { suggestBox.classList.add('d-none'); }, 150);
        });

        createBtn.addEventListener('click', function () {
            var nombre = searchInput.value.trim();
            if (!nombre) return;
            showError('');
            setBusy(true);
            postStep(Object.assign({ step: cfgStep.key, action: 'nueva', new_name: nombre }, contextPayload()))
                .then(function (res) {
                    setBusy(false);
                    if (!res.data.ok) { showError(res.data.error || 'No se pudo crear.'); return; }
                    STATE[cfgStep.key] = { id: res.data.id, name: res.data.name, skipped: false };
                    advance();
                })
                .catch(function () { setBusy(false); showError('Error de red — reintentar.'); });
        });

        skipBtn.addEventListener('click', function () {
            STATE[cfgStep.key] = { id: null, name: null, skipped: true };
            advance();
        });

        return { onEnter: loadList };
    }

    // ---- Paso 5: Resultados de aprendizaje -------------------------------
    function setupOutcomesStep() {
        var panel = panelFor(5);
        var titleEl = role(panel, 'title');
        var hintEl = role(panel, 'step-hint');
        var parentMsgEl = role(panel, 'parent-message');
        var chipListEl = role(panel, 'chip-list');
        var listEmptyEl = role(panel, 'list-empty-msg');
        var searchInput = role(panel, 'search-input');
        var suggestBox = role(panel, 'suggest-box');
        var createBtn = role(panel, 'create-btn');
        var skipBtn = role(panel, 'skip-btn');
        var errorEl = role(panel, 'error-msg');
        var searchLabel = role(panel, 'search-label');

        titleEl.textContent = 'Resultados de aprendizaje';
        hintEl.textContent = 'Es opcional: no hace falta para subir contenido, generar preguntas ni armar el examen.';
        hintEl.style.display = 'block';
        searchLabel.textContent = 'Agregar un resultado de aprendizaje nuevo (texto libre)';
        suggestBox.style.display = 'none';
        skipBtn.textContent = 'Continuar';

        function showError(msg) {
            errorEl.textContent = msg || '';
            errorEl.style.display = msg ? 'block' : 'none';
        }

        function renderChips() {
            chipListEl.innerHTML = '';
            listEmptyEl.style.display = STATE.outcomes.length ? 'none' : 'block';
            STATE.outcomes.forEach(function (o) {
                var chip = document.createElement('span');
                chip.className = 'fw-chip is-selected';
                chip.textContent = o.description;
                chipListEl.appendChild(chip);
            });
        }

        function elegible() {
            return STATE.carrera && !STATE.carrera.skipped && STATE.materia && !STATE.materia.skipped;
        }

        function loadExisting() {
            renderChips();
            searchInput.value = '';
            createBtn.disabled = true;
            if (!elegible()) {
                parentMsgEl.textContent = 'Hace falta una Carrera y una Materia vinculadas entre sí para cargar resultados de aprendizaje acá — se puede saltear este paso.';
                searchInput.disabled = true;
                return;
            }
            parentMsgEl.textContent = '';
            searchInput.disabled = false;
            var params = new URLSearchParams({ career_id: STATE.carrera.id, subject_id: STATE.materia.id });
            fetch(CFG.urls.outcomesByCareerSubject + '?' + params.toString())
                .then(function (r) { return r.json(); })
                .then(function (data) {
                    var yaIds = STATE.outcomes.map(function (o) { return o.id; });
                    (data.outcomes || []).forEach(function (o) {
                        if (yaIds.indexOf(o.id) === -1) STATE.outcomes.push(o);
                    });
                    renderChips();
                })
                .catch(function () {});
        }

        searchInput.addEventListener('input', function () {
            createBtn.disabled = !searchInput.value.trim();
        });

        createBtn.addEventListener('click', function () {
            var texto = searchInput.value.trim();
            if (!texto) return;
            showError('');
            createBtn.disabled = true;
            postStep(Object.assign({ step: 'resultado_aprendizaje', action: 'nueva', new_name: texto }, contextPayload()))
                .then(function (res) {
                    createBtn.disabled = false;
                    if (!res.data.ok) { showError(res.data.error || 'No se pudo crear.'); return; }
                    STATE.outcomes.push({ id: res.data.id, description: res.data.name });
                    searchInput.value = '';
                    renderChips();
                    renderBreadcrumb();
                    saveDraft();
                })
                .catch(function () { createBtn.disabled = false; showError('Error de red — reintentar.'); });
        });

        skipBtn.addEventListener('click', function () {
            renderBreadcrumb();
            saveDraft();
            wizardCtrl.goNext();
        });

        return { onEnter: loadExisting };
    }

    // ---- Pasos 6-8: Contenido / Preguntas / Examen -----------------------
    function setupHandoffStep(n) {
        var panel = panelFor(n);
        var skipBtn = panel.querySelector('[data-role="step-skip"]');
        var continueBtn = panel.querySelector('[data-role="step-continue"]');
        if (skipBtn) skipBtn.addEventListener('click', function () { wizardCtrl.goNext(); });
        if (continueBtn) continueBtn.addEventListener('click', function () { wizardCtrl.goNext(); });
    }

    function refreshHandoffLinks() {
        var subjectOk = STATE.materia && !STATE.materia.skipped;
        var msg = document.getElementById('fwStep6Msg');
        if (msg && !subjectOk) {
            msg.textContent = 'No se eligió ninguna Materia en este recorrido — al subir el contenido, elegí o creá una materia en esa misma pantalla.';
        }
        var step6Link = document.getElementById('fwStep6Link');
        if (step6Link) step6Link.href = CFG.urls.uploadContenido;
        var genLink = document.getElementById('fwStep7GenLink');
        if (genLink) genLink.href = CFG.urls.docProcessor;
        var manualLink = document.getElementById('fwStep7ManualLink');
        if (manualLink) manualLink.href = CFG.urls.uploadQuestions;
    }

    // Precarga institución/facultad/carrera/materia/RA ya resueltos en el
    // wizard antes de abrir Crear Examen (ver full_wizard_prefill_exam) —
    // sin esto, "Crear examen" abría un formulario en blanco que obligaba a
    // repetir todo lo ya elegido acá (pedido explícito del usuario).
    var examBtnWired = false;
    function wireExamButton() {
        var btn = document.getElementById('fwStep8Btn');
        if (!btn || examBtnWired) return;
        examBtnWired = true;
        btn.addEventListener('click', function () {
            btn.disabled = true;
            var payload = Object.assign(
                { outcome_ids: STATE.outcomes.map(function (o) { return o.id; }) },
                contextPayload()
            );
            fetch(CFG.urls.prefillExam, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
                body: JSON.stringify(payload),
            })
                .then(function () { window.location.href = CFG.urls.createExam; })
                .catch(function () { window.location.href = CFG.urls.createExam; });
        });
    }

    function renderSummary() {
        var el = document.getElementById('wizSummary');
        if (!el) return;
        var rows = [];
        ['institucion', 'facultad', 'carrera', 'materia'].forEach(function (key) {
            var v = STATE[key];
            var valor = v === null ? '—' : (v.skipped ? 'salteado' : v.name);
            rows.push('<div class="d-flex justify-content-between border-bottom py-1"><span class="text-muted">' + LABELS[key] + '</span><span>' + valor + '</span></div>');
        });
        rows.push('<div class="d-flex justify-content-between border-bottom py-1"><span class="text-muted">Resultados de aprendizaje</span><span>' + STATE.outcomes.length + '</span></div>');
        el.innerHTML = rows.join('');
    }

    document.addEventListener('DOMContentLoaded', function () {
        var catalogHandlers = CATALOG_STEPS.map(setupCatalogStep);
        var outcomesHandler = setupOutcomesStep();
        [6, 7, 8].forEach(setupHandoffStep);
        wireExamButton();

        wizardCtrl = window.EducaAppWizard.init({
            totalSteps: 8,
            onValidateStep: function () { return true; },
            onEnterFinalStep: function () { refreshHandoffLinks(); renderSummary(); },
        });

        // Vuelve a cargar la lista de "usar existente" cada vez que se
        // entra a un paso 1-5 (por si el padre cambió, o para refrescar
        // tras volver de una pestaña donde se cargó algo nuevo).
        var ORIGINAL = { goNext: wizardCtrl.goNext, goBack: wizardCtrl.goBack, goToStep: wizardCtrl.goToStep };
        function onEnterStep(n) {
            if (n >= 1 && n <= 4) catalogHandlers[n - 1].onEnter();
            else if (n === 5) outcomesHandler.onEnter();
            else if (n === 6 || n === 7 || n === 8) refreshHandoffLinks();
        }
        wizardCtrl.goNext = function () { ORIGINAL.goNext(); onEnterStep(wizardCtrl.current()); };
        wizardCtrl.goBack = function () { ORIGINAL.goBack(); onEnterStep(wizardCtrl.current()); };
        wizardCtrl.goToStep = function (n) { ORIGINAL.goToStep(n); onEnterStep(wizardCtrl.current()); };

        // Restaurar borrador (sessionStorage) si lo hay — solo el estado ya
        // resuelto de esta pestaña, no reemplaza lo persistido en la base.
        function restoreFromDraft(saved) {
            Object.assign(STATE, saved);
            renderBreadcrumb();
            var lastResolvedStep = 0;
            ['institucion', 'facultad', 'carrera', 'materia'].forEach(function (key, idx) {
                if (STATE[key] !== null) lastResolvedStep = idx + 1;
            });
            var target = Math.min(lastResolvedStep + 1, 8);
            for (var i = 1; i < target; i++) { wizardCtrl.goNext(); }
        }

        if (draft) {
            var saved = draft.load();
            if (saved && (saved.institucion || saved.facultad || saved.carrera || saved.materia || (saved.outcomes && saved.outcomes.length))) {
                draft.confirmRestore('Hay un progreso sin terminar de una visita anterior a este asistente — ¿retomarlo donde quedó?')
                    .then(function (ok) {
                        if (ok) { restoreFromDraft(saved); }
                        else { draft.clear(); onEnterStep(1); }
                    });
                return;
            }
        }
        onEnterStep(1);
    });
})();
