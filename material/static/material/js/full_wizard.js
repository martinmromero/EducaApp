// full_wizard.js — Asistente completo (institución -> facultad -> carrera ->
// materia -> resultados de aprendizaje -> preguntas -> examen). El paso Examen
// monta el asistente "Nuevo examen" en un <iframe> (ver mountExamFrame).
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
        // Paso 6 (Preguntas): true si se avanzó con "Saltear", false si con
        // "Continuar" (había algo cargado) — solo para el ícono de la
        // pastilla, el motor del stepper no distingue hecho de salteado.
        questionsSkipped: false,
        // Último paso visible: permite volver exactamente ahí tras salir a
        // otra pantalla (el generador con IA) y regresar con ?retomar=1.
        currentStep: 1,
        // Plantilla con la que se arrancó (ver setupTemplateBox): viaja al examen
        // embebido para que aplique el resto (docente, sede, formato, rúbricas...).
        templateId: null,
    };

    // Asignados en DOMContentLoaded, leídos por configureBottomAction() —
    // declarados acá arriba porque esa función se define antes del bloque
    // que arma los handlers de cada paso.
    var catalogHandlersRef = [];
    var outcomesHandlerRef = null;

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
                parts.push('<span class="fw-crumb"><i class="bi bi-check-circle-fill text-success me-1"></i>' + window.EducaAppEscape(v.name) + '</span>');
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

    // Marca como "salteada" (ícono skip-forward, gris punteado) a toda pastilla
    // que el motor ya dio por pasada (.is-done) pero donde no se hizo nada.
    // wizard_engine.js solo sabe de "pasado", no de "hecho vs salteado", así
    // que se reaplica después de cada cambio de paso (ver onEnterStep).
    function isPillSkipped(n) {
        if (n >= 1 && n <= 4) {
            var st = STATE[CATALOG_STEPS[n - 1].key];
            return !!(st && st.skipped);
        }
        if (n === 5) return STATE.outcomes.length === 0;
        if (n === 6) return !!STATE.questionsSkipped;
        return false;
    }

    function refreshPills() {
        document.querySelectorAll('.wiz-step-pill').forEach(function (pill) {
            var n = parseInt(pill.dataset.stepPill, 10);
            var skipped = pill.classList.contains('is-done') && isPillSkipped(n);
            var num = pill.querySelector('.wiz-step-num');
            var wasSkipped = pill.classList.contains('is-skipped');
            pill.classList.toggle('is-skipped', skipped);
            if (skipped === wasSkipped) return;
            if (skipped) {
                num.innerHTML = '<i class="bi bi-skip-forward-fill"></i>';
                pill.title = 'Salteado — se puede volver y completarlo';
            } else {
                num.innerHTML = '<span>' + n + '</span>';
                pill.removeAttribute('title');
            }
        });
        // El último paso nunca queda "pasado" para el motor del stepper: con el
        // examen ya guardado se marca hecho a mano.
        var last = document.querySelector('.wiz-step-pill[data-step-pill="7"]');
        if (last) last.classList.toggle('is-done', !!(exam && exam.saved));
    }

    // ---- Pasos 1-4: Institución / Facultad / Carrera / Materia ----------
    // hint: explica, ANTES de elegir, qué efecto tiene saltear este paso en
    // los pasos siguientes — pedido explícito del usuario ("entendiendo cómo
    // se conectan entre sí"), mismo criterio para los 4 niveles + RA.
    var CATALOG_STEPS = [
        {
            n: 1, key: 'institucion', label: 'Institución', parentKey: null, hardParent: false,
            listKey: 'institutions',
            loadUrl: function () { return CFG.urls.listInstituciones; },
            hint: 'Si se saltea este paso, tampoco se puede cargar una Facultad (necesita una Institución elegida acá), así que el asistente salta directo a Carrera.',
        },
        {
            n: 2, key: 'facultad', label: 'Facultad', parentKey: 'institucion', hardParent: true,
            listKey: 'faculties',
            loadUrl: function (parentId) { return CFG.urls.facultadesByInstitucionBase + parentId + '/'; },
            hint: 'Si se saltea este paso, la Carrera del paso siguiente se puede crear igual, pero sin esta Facultad asociada.',
        },
        {
            n: 3, key: 'carrera', label: 'Carrera', parentKey: 'facultad', hardParent: false,
            listKey: 'careers',
            loadUrl: function (parentId) { return CFG.urls.carrerasByFacultadBase + parentId + '/'; },
            hint: 'Si se saltea este paso, la Materia del paso siguiente se puede crear igual, pero sin esta Carrera asociada — y el paso de Resultados de aprendizaje (necesita Carrera y Materia) también se saltea.',
        },
        {
            n: 4, key: 'materia', label: 'Materia', parentKey: 'carrera', hardParent: false,
            listKey: 'subjects',
            loadUrl: function (parentId) { return CFG.urls.materiasByCarreraBase + parentId + '/'; },
            hint: 'Importante: los pasos siguientes (Preguntas y Examen) usan la materia elegida acá. Si se saltea este paso, va a ser necesario elegirla o crearla de nuevo en cada pantalla siguiente. Tampoco se van a poder cargar Resultados de aprendizaje (necesitan una Materia), así que ese paso también se saltea.',
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
        var parentMsgEl = role(panel, 'parent-message');
        var chipListEl = role(panel, 'chip-list');
        var listEmptyEl = role(panel, 'list-empty-msg');
        var searchInput = role(panel, 'search-input');
        var suggestBox = role(panel, 'suggest-box');
        var createBtn = role(panel, 'create-btn');
        var errorEl = role(panel, 'error-msg');
        // El hint de "qué pasa si se saltea este paso" ya no se muestra acá
        // de entrada (pedido explícito del usuario, quedaba como texto
        // siempre visible antes de que la persona hiciera nada) — pasó a
        // ser el mensaje del modal de confirmación de "Saltear", ver
        // requestSkip() más abajo. El botón en sí vive en la barra inferior
        // compartida (#wizNextBtn), no en esta tarjeta.

        titleEl.textContent = cfgStep.label;

        function showError(msg) {
            errorEl.textContent = msg || '';
            errorEl.style.display = msg ? 'block' : 'none';
        }

        function setBusy(busy) {
            createBtn.disabled = busy || !searchInput.value.trim();
            searchInput.disabled = busy;
        }

        // Resultados de aprendizaje (paso 5) necesita Carrera Y Materia reales
        // vinculadas entre sí (ver full_wizard_save_step): si después del paso
        // 4 no se cumple, ese paso no tiene nada que hacer y se lo saltea acá
        // mismo, igual que Facultad cuando se saltea Institución.
        function extraSkipAfter() {
            return cfgStep.n === 4 && !outcomesHandlerRef.elegible() ? 1 : 0;
        }

        function advance() {
            renderBreadcrumb();
            saveDraft();
            wizardCtrl.goNext();
            if (extraSkipAfter()) wizardCtrl.goNext();
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

        // Mientras llega la lista no se deja el espacio vacío: un clic apurado
        // caía sobre lo que aparecía después (y movía el layout).
        function showListLoading() {
            listEmptyEl.style.display = 'none';
            chipListEl.innerHTML = '<span class="text-muted small fw-chip-loading"><span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>Cargando…</span>';
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
                showListLoading();
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
                    parentMsgEl.textContent = 'No se puede cargar ' + cfgStep.label.toLowerCase() + ' sin ' + LABELS[cfgStep.parentKey].toLowerCase() + ' (se salteó en el paso anterior) — continuar sin este paso.';
                    chipListEl.innerHTML = '';
                    listEmptyEl.style.display = 'none';
                    searchInput.disabled = true;
                    return;
                }
                parentMsgEl.textContent = 'No se especificó ' + LABELS[cfgStep.parentKey].toLowerCase() + ' — buscando en todo el catálogo visible en vez de acotar.';
                searchInput.disabled = false;
                renderChips([]);
                return;
            }

            parentMsgEl.textContent = '';
            searchInput.disabled = false;
            showListLoading();
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

        // Un paso con hardParent (Facultad) no tiene nada que hacer si su padre
        // quedó salteado: mostrarlo igual obligaba a un segundo "Saltear" con
        // otro modal sobre una decisión ya tomada. Por eso saltear un nivel
        // cascadea al hijo duro y avanza directo al siguiente paso útil.
        function skipNow() {
            STATE[cfgStep.key] = { id: null, name: null, skipped: true };
        }

        function requestSkip() {
            function doSkip() {
                skipNow();
                var steps = 1;
                CATALOG_STEPS.forEach(function (child) {
                    if (child.hardParent && child.parentKey === cfgStep.key) {
                        STATE[child.key] = { id: null, name: null, skipped: true };
                        steps += 1;
                    }
                });
                steps += extraSkipAfter();
                renderBreadcrumb();
                saveDraft();
                for (var i = 0; i < steps; i++) { wizardCtrl.goNext(); }
            }
            if (!cfgStep.hint) { doSkip(); return; }
            window.EducaAppModal.confirm(cfgStep.hint, {
                title: 'Saltear ' + cfgStep.label,
                variant: 'warning',
                okLabel: 'Saltear',
            }).then(function (ok) { if (ok) doSkip(); });
        }

        // Sin modal: el padre ya se salteó, así que no hay decisión nueva que
        // confirmar (se usa al volver a un paso que quedó salteado en cascada).
        function skipSilently() { skipNow(); advance(); }

        return { onEnter: loadList, requestSkip: requestSkip, advanceOnly: advance, skipSilently: skipSilently };
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
        var errorEl = role(panel, 'error-msg');
        var searchLabel = role(panel, 'search-label');

        titleEl.textContent = 'Resultados de aprendizaje';
        hintEl.textContent = 'Es opcional: no hace falta para cargar preguntas ni armar el examen.';
        hintEl.style.display = 'block';
        searchLabel.textContent = 'Agregar un resultado de aprendizaje nuevo (texto libre)';
        suggestBox.style.display = 'none';

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
                parentMsgEl.textContent = 'Hace falta una Carrera y una Materia vinculadas entre sí para cargar resultados de aprendizaje acá (alguna se salteó en un paso anterior) — continuar sin este paso.';
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

        function continueClick() {
            renderBreadcrumb();
            saveDraft();
            wizardCtrl.goNext();
        }

        return { onEnter: loadExisting, continueClick: continueClick, elegible: elegible };
    }

    // ---- Barra inferior compartida (#wizNextBtn) --------------------------
    // Un solo botón para los 7 pasos: "Saltear" (con confirmación, si el
    // paso tiene algo pendiente de aviso) cuando todavía no se hizo nada en
    // ese nivel, "Continuar" cuando ya hay algo elegido/creado/subido — ver
    // pedido explícito del usuario de unificar el criterio entre pasos, que
    // antes variaba (columna propia en 1-5, fila propia en 6-7).
    var nextBtn = document.getElementById('fwActionBtn');
    var QUESTIONS_HINT = 'Importante: para poder armar un examen en el paso siguiente, la materia elegida necesita tener al menos una pregunta ya aprobada. No saltear este paso si todavía no se cargó ninguna.';

    function setNextButton(label, handler) {
        if (!nextBtn) return;
        nextBtn.classList.remove('d-none');
        nextBtn.innerHTML = label + '<i class="bi bi-arrow-right ms-1"></i>';
        nextBtn.disabled = false;
        nextBtn.onclick = handler;
    }

    // ---- Paso 6: Preguntas -------------------------------------------------
    // Antes eran dos pasos (Contenido y Preguntas) que se pisaban: el
    // generador con IA ya pide el documento por su cuenta, así que subir
    // contenido aparte era un rodeo. Ahora hay UNA pantalla con dos
    // caminos: generar con IA (pestaña nueva) o cargar acá mismo con el
    // asistente "Subir preguntas" embebido (question_upload_wizard.js, ver
    // el contrato de mount() en su encabezado). El embebido trae su propia
    // barra de navegación, así que mientras está abierto se oculta el botón
    // inferior compartido.
    var embed = { root: null, pristine: null, mounted: false, mountedFor: null, active: false };

    function currentSubjectId() {
        return STATE.materia && !STATE.materia.skipped ? STATE.materia.id : null;
    }

    // Solo el DOM (sin tocar la barra inferior): onEnterStep ya llama a
    // configureBottomAction() después, no hay que duplicar el fetch.
    function applyQuestionsView(showEmbed) {
        embed.active = showEmbed;
        var hub = document.getElementById('fwQHub');
        var box = document.getElementById('fwQEmbed');
        if (hub) hub.classList.toggle('d-none', showEmbed);
        if (box) box.classList.toggle('d-none', !showEmbed);
        // El asistente embebido trae su propia barra (Atrás / Siguiente):
        // con la del host a la vista quedaban dos "Atrás" apilados.
        var hostNav = document.querySelector('.wiz-nav');
        if (hostNav) hostNav.classList.toggle('d-none', showEmbed);
    }

    // Cuántas preguntas puede usar Crear examen en la materia elegida
    // (full_wizard_subject_progress): se muestra en el paso Preguntas, en la
    // pantalla final del asistente embebido y en el resumen del paso Examen.
    function fetchProgress(sid) {
        var params = new URLSearchParams({ subject_id: sid });
        return fetch(CFG.urls.subjectProgress + '?' + params.toString()).then(function (r) { return r.json(); });
    }

    function questionCountText(data) {
        var n = data.question_count || 0;
        if (!n) return 'Esta materia todavía no tiene preguntas disponibles para armar un examen.';
        var own = data.own_question_count || 0;
        var txt = 'Esta materia tiene ' + n + (n === 1 ? ' pregunta disponible' : ' preguntas disponibles') + ' para armar un examen';
        if (own !== n) txt += ' (' + own + (own === 1 ? ' propia' : ' propias') + ', el resto compartidas por grupos de confianza)';
        return txt + '.';
    }

    function setQuestionsView(showEmbed) {
        applyQuestionsView(showEmbed);
        configureBottomAction(6);
    }

    function mountQuestionsEmbed() {
        var sid = currentSubjectId();
        if (embed.mounted && embed.mountedFor === sid) return;
        // El asistente embebido ata sus listeners al nodo raíz: para
        // volver a montarlo (la materia cambió volviendo atrás) hace falta
        // un nodo nuevo, no el ya usado.
        if (embed.mounted) {
            var fresh = embed.pristine.cloneNode(true);
            embed.root.parentNode.replaceChild(fresh, embed.root);
            embed.root = fresh;
        }
        window.EducaAppQuestionUpload.mount(embed.root, {
            subject: sid ? { id: sid, name: STATE.materia.name } : undefined,
            lockSubject: !!sid,
            careerId: STATE.carrera && !STATE.carrera.skipped ? STATE.carrera.id : '',
            draftKey: 'full_wizard_uqw_draft_v1',
            finishLabel: 'Continuar con el examen',
            // Pantalla final del asistente embebido: cuántas preguntas quedan
            // disponibles en la materia después de cargar.
            doneNote: function (r) {
                if (!r.subject) return null;
                return fetchProgress(r.subject.id).then(questionCountText);
            },
            // "Atrás" en el primer paso del embebido vuelve a las dos
            // tarjetas; los enlaces de la barra del host viajan con él.
            onExit: function () { setQuestionsView(false); },
            navLinksHtml: hostNavLinksHtml(),
            onCreated: function (r) {
                STATE.questionsSkipped = false;
                // Sin esto la pastilla seguía con el ícono de "salteada" aunque
                // ya se hubiera cargado una pregunta en este mismo paso.
                refreshPills();
                // Si se salteó la Materia, la que se eligió/creó acá pasa a
                // ser la del recorrido (la usa el paso Examen para precargar).
                if (!sid && r.subject) {
                    STATE.materia = { id: r.subject.id, name: r.subject.name, skipped: false };
                    embed.mountedFor = r.subject.id;
                    renderBreadcrumb();
                }
                saveDraft();
            },
            onFinished: function () {
                embed.active = false;
                wizardCtrl.goNext();
            },
        });
        embed.mounted = true;
        embed.mountedFor = sid;
    }

    function hostNavLinksHtml() {
        var links = document.querySelector('.fw-nav-links');
        return links ? '<div class="fw-nav-links">' + links.innerHTML + '</div>' : '';
    }

    function openQuestionsEmbed() {
        mountQuestionsEmbed();
        setQuestionsView(true);
    }

    function requestSkipQuestions() {
        function doSkip() {
            STATE.questionsSkipped = true;
            saveDraft();
            wizardCtrl.goNext();
        }
        window.EducaAppModal.confirm(QUESTIONS_HINT, {
            title: 'Saltear Preguntas',
            variant: 'warning',
            okLabel: 'Saltear',
        }).then(function (ok) { if (ok) doSkip(); });
    }

    function configureQuestionsBottomAction() {
        var status = document.getElementById('fwQStatus');
        if (status) { status.classList.add('d-none'); status.textContent = ''; }
        if (embed.active) {
            if (nextBtn) nextBtn.classList.add('d-none');
            return;
        }
        setNextButton('Saltear', requestSkipQuestions);
        var sid = currentSubjectId();
        if (!sid) return;
        fetchProgress(sid)
            .then(function (data) {
                // La respuesta puede llegar tarde: si en el medio se cambió
                // de paso o se abrió el asistente embebido, no se pisa nada.
                if (embed.active || wizardCtrl.current() !== 6) return;
                var n = data.question_count || 0;
                if (status) {
                    status.textContent = questionCountText(data);
                    status.className = 'alert py-2 ' + (n ? 'alert-success' : 'alert-warning');
                }
                if (!n) return;
                setNextButton('Continuar', function () {
                    STATE.questionsSkipped = false;
                    saveDraft();
                    wizardCtrl.goNext();
                });
            })
            .catch(function () {});
    }

    function configureBottomAction(n) {
        if (n === 7) {
            // El paso final usa #wizSubmitBtn ("Terminar"), ya manejado por
            // wizard_engine.js — este botón propio no aplica ahí.
            if (nextBtn) nextBtn.classList.add('d-none');
            return;
        }
        if (n >= 1 && n <= 4) {
            var cfgStep = CATALOG_STEPS[n - 1];
            var handler = catalogHandlersRef[n - 1];
            var st = STATE[cfgStep.key];
            var parentSt = cfgStep.parentKey ? STATE[cfgStep.parentKey] : null;
            var parentMissing = cfgStep.hardParent && (!parentSt || parentSt.skipped);
            if (st && !st.skipped) setNextButton('Continuar', handler.advanceOnly);
            else if (parentMissing) setNextButton('Continuar', handler.skipSilently);
            else setNextButton('Saltear', handler.requestSkip);
        } else if (n === 5) {
            setNextButton('Continuar', outcomesHandlerRef.continueClick);
        } else if (n === 6) {
            configureQuestionsBottomAction();
        }
    }

    // Estado de la IA antes de ofrecer "Generar con IA": lista, sin cupo o no
    // disponible. "Cargar a mano" no depende de esto y queda siempre a mano.
    function refreshAIStatus() {
        var el = document.getElementById('fwAIStatus');
        if (!el || !CFG.urls.aiStatus) return;
        fetch(CFG.urls.aiStatus)
            .then(function (r) { return r.json(); })
            .then(function (d) {
                var problema = !d.connected || d.quota_exhausted;
                el.className = 'alert py-2 small mt-3 mb-0 ' + (problema ? 'alert-warning' : 'alert-success');
                el.textContent = '';
                var texto = document.createElement('span');
                if (problema) {
                    texto.textContent = d.message || d.error || 'La IA no está disponible ahora mismo.';
                    el.appendChild(texto);
                    el.appendChild(document.createTextNode(' '));
                    var link = document.createElement('a');
                    link.href = CFG.urls.aiConfig;
                    link.className = 'alert-link';
                    link.textContent = 'Abrir Proveedor de IA';
                    el.appendChild(link);
                    el.appendChild(document.createTextNode('. Mientras tanto, "Cargar a mano" sigue disponible.'));
                } else if (d.using_shared_fallback) {
                    var q = d.demo_quota;
                    var cupo = q && q.remaining_requests != null && q.limit_requests
                        ? ' Cupo compartido restante hoy: ' + q.remaining_requests + ' de ' + q.limit_requests + ' solicitudes.'
                        : '';
                    texto.textContent = 'IA pública gratuita lista.' + cupo;
                    el.appendChild(texto);
                } else {
                    texto.textContent = 'IA conectada' + (d.model ? ' (' + d.model + ')' : '') + '.';
                    el.appendChild(texto);
                }
            })
            .catch(function () { el.className = 'd-none'; });
    }

    // ---- Partir de una plantilla -------------------------------------------
    // Una plantilla (ExamTemplate) guarda institución, facultad, carrera, materia
    // y resultados de aprendizaje: elegirla completa los pasos 1 a 5 de una vez
    // y lleva a Preguntas (o directo a Examen si la materia ya tiene preguntas).
    var templatesAvailable = false;

    function toggleTemplateBox(n) {
        var box = document.getElementById('fwTemplateBox');
        if (box) box.classList.toggle('d-none', !(templatesAvailable && n === 1));
    }

    function setupTemplateBox() {
        var select = document.getElementById('fwTemplateSelect');
        var useBtn = document.getElementById('fwTemplateUse');
        var errEl = document.getElementById('fwTemplateError');
        if (!select || !useBtn || !CFG.urls.templates) return;

        function showError(msg) {
            errEl.textContent = msg || '';
            errEl.classList.toggle('d-none', !msg);
        }

        fetch(CFG.urls.templates)
            .then(function (r) { return r.json(); })
            .then(function (data) {
                var list = data.templates || [];
                if (!list.length) return;
                list.forEach(function (t) {
                    var opt = document.createElement('option');
                    opt.value = t.id;
                    opt.textContent = t.name + (t.subject ? ' — ' + t.subject : '') + (t.career ? ' (' + t.career + ')' : '');
                    select.appendChild(opt);
                });
                templatesAvailable = true;
                toggleTemplateBox(wizardCtrl ? wizardCtrl.current() : 1);
            })
            .catch(function () { /* sin plantillas no hay nada que ofrecer */ });

        useBtn.addEventListener('click', function () {
            if (!select.value) return;
            showError('');
            useBtn.disabled = true;
            fetch(CFG.urls.templateContextBase + encodeURIComponent(select.value) + '/')
                .then(function (r) { return r.json().then(function (data) { return { status: r.status, data: data }; }); })
                .then(function (res) {
                    useBtn.disabled = false;
                    var d = res.data;
                    if (!d.ok) { showError(d.error || 'No se pudo usar la plantilla.'); return; }
                    ['institucion', 'facultad', 'carrera', 'materia'].forEach(function (key) {
                        STATE[key] = { id: d.chain[key].id, name: d.chain[key].name, skipped: false };
                    });
                    STATE.outcomes = d.outcomes || [];
                    STATE.templateId = d.template.id;
                    STATE.questionsSkipped = false;
                    exam.saved = false;
                    renderBreadcrumb();
                    saveDraft();
                    // El motor solo deja avanzar de a un paso: se recorren los
                    // intermedios (ya resueltos) hasta Preguntas o Examen.
                    var destino = d.question_count > 0 ? 7 : 6;
                    var pasos = destino - wizardCtrl.current();
                    for (var i = 0; i < pasos; i++) wizardCtrl.goNext();
                })
                .catch(function () { useBtn.disabled = false; showError('Error de red: reintentar.'); });
        });
    }

    function refreshQuestionsLinks() {
        refreshAIStatus();
        var msg = document.getElementById('fwStep6Msg');
        if (msg && !currentSubjectId()) {
            msg.textContent = 'No se eligió ninguna Materia en este recorrido — al cargar o generar preguntas, hay que elegir o crear una materia en esa misma pantalla.';
        }
        // Misma pestaña (no una nueva): el generador con IA es una pantalla
        // completa que vuelve sola al asistente al guardar (?fw=1), y el
        // progreso queda en el borrador de sessionStorage hasta entonces.
        var genLink = document.getElementById('fwQGenLink');
        if (genLink) {
            var sid = currentSubjectId();
            genLink.href = CFG.urls.docProcessor + '?fw=1' + (sid ? '&subject_id=' + encodeURIComponent(sid) : '');
        }
    }

    // ---- Paso 7: Examen ----------------------------------------------------
    // Monta el asistente "Nuevo examen" (create_exam_wizard, modo ?fw=1) en un
    // <iframe> same-origin, para que todo el recorrido — incluida la vista
    // previa y el guardado, que son pantallas aparte — ocurra sin salir de
    // este asistente. Lo ya elegido acá viaja por query string y el asistente
    // de examen lo precarga y saltea los pasos que ya no tienen nada que
    // decidir (ver applyFwPrefill en create_exam_wizard.js). El iframe se
    // llama "educaapp-embed-exam": es lo que activa el modo sin menú
    // (static/js/embed.js) y los avisos por postMessage de abajo.
    var EXAM_DRAFT_KEY = 'educaapp_exam_wizard_draft_fw';
    // kind: lo que se arma en este último paso, 'escrito' (examen) u 'oral' (cuestionario oral).
    var exam = { url: null, saved: false, readySeen: false, kind: 'escrito', contextKey: null };
    var ORAL_DRAFT_KEY = 'educaapp_oral_wizard_draft_fw';

    function examEl(id) { return document.getElementById(id); }

    function clearExamDraft() {
        try { sessionStorage.removeItem(EXAM_DRAFT_KEY); } catch (e) { /* sin sessionStorage */ }
    }
    function clearOralDraft() {
        try { sessionStorage.removeItem(ORAL_DRAFT_KEY); } catch (e) { /* sin sessionStorage */ }
    }

    // 'blocked' | 'stage' | 'done'. Con el asistente de examen abierto
    // ('stage') la barra inferior del host se oculta: el iframe trae la suya
    // (mismo criterio que el asistente de preguntas embebido en el paso 6).
    function showExamPanel(which) {
        examEl('fwExamBlocked').classList.toggle('d-none', which !== 'blocked');
        examEl('fwExamStage').classList.toggle('d-none', which !== 'stage');
        examEl('fwExamDone').classList.toggle('d-none', which !== 'done');
        var hostNav = document.querySelector('.wiz-nav');
        if (hostNav) hostNav.classList.toggle('d-none', which === 'stage');
    }

    function examFrameUrl() {
        var params = new URLSearchParams({ fw: '1' });
        var ctx = contextPayload();
        if (exam.kind === 'oral') {
            // El cuestionario oral solo necesita la materia: tópicos, alumnos y grupos se piden adentro.
            if (ctx.materia_id) params.set('subject_id', ctx.materia_id);
            return CFG.urls.createOralWizard + '?' + params.toString();
        }
        if (ctx.materia_id) params.set('subject_id', ctx.materia_id);
        if (ctx.institucion_id) params.set('institucion_id', ctx.institucion_id);
        if (ctx.facultad_id) params.set('facultad_id', ctx.facultad_id);
        if (ctx.carrera_id) params.set('carrera_id', ctx.carrera_id);
        if (STATE.outcomes.length) params.set('outcome_ids', STATE.outcomes.map(function (o) { return o.id; }).join(','));
        if (STATE.templateId) params.set('plantilla_id', STATE.templateId);
        return CFG.urls.createExamWizard + '?' + params.toString();
    }

    // retry: se reintenta tras una pantalla que no cargó. Conserva el borrador
    // del asistente de examen y arma un <iframe> nuevo (ver replaceExamFrame).
    function mountExamFrame(retry) {
        showExamPanel('stage');
        var url = examFrameUrl();
        // Misma materia/elecciones que la última vez (ej. se salió a Preguntas
        // y se volvió): no se recarga, así no se pierde lo ya armado.
        if (exam.url === url) return;
        // Cambió algo de lo elegido antes (otra materia, otros resultados de
        // aprendizaje, otra plantilla): los borradores de los asistentes de examen
        // y de oral ya no sirven. Cambiar solo de tipo (escrito <-> oral) NO cambia
        // el contexto: cada uno conserva lo ya cargado.
        var contextKey = JSON.stringify([contextPayload(), STATE.outcomes.map(function (o) { return o.id; }), STATE.templateId]);
        if (!retry && exam.contextKey !== contextKey) { clearExamDraft(); clearOralDraft(); }
        exam.contextKey = contextKey;
        exam.url = url;
        exam.readySeen = false;
        examEl('fwExamLoading').classList.remove('d-none');
        var frame = retry ? replaceExamFrame() : examEl('fwExamFrame');
        frame.classList.add('d-none');
        frame.src = url;
    }

    // ---- Examen escrito o cuestionario oral ---------------------------------
    function refreshKindBar() {
        document.querySelectorAll('#fwKindBar [data-kind]').forEach(function (btn) {
            var activo = btn.dataset.kind === exam.kind;
            btn.classList.toggle('active', activo);
            btn.classList.toggle('btn-primary', activo);
            btn.classList.toggle('btn-outline-primary', !activo);
            btn.setAttribute('aria-pressed', activo ? 'true' : 'false');
        });
        var nota = examEl('fwKindNote');
        nota.classList.add('d-none');
        nota.textContent = '';
        if (exam.kind !== 'oral') return;
        var sid = currentSubjectId();
        if (!sid) return;
        // El oral reparte las preguntas por sub-tópico (o por tópico si no hay
        // sub-tópicos): con muy pocas "unidades", los alumnos repiten tema.
        fetchProgress(sid).then(function (data) {
            if (exam.kind !== 'oral' || (data.oral_units || 0) >= 2) return;
            nota.textContent = 'Esta materia tiene ' + (data.oral_units || 0) + ' tópico(s) o sub-tópico(s) con preguntas propias o compartidas. '
                + 'El cuestionario oral reparte las preguntas por sub-tópico: con tan pocos, los alumnos van a repetir tema. '
                + 'Se pueden agregar tópicos y sub-tópicos desde la ficha de la materia.';
            nota.classList.remove('d-none');
        }).catch(function () { /* el aviso es opcional */ });
    }

    function setExamKind(kind) {
        if (kind === exam.kind) return;
        exam.kind = kind;
        refreshKindBar();
        mountExamFrame();
    }

    function enterExamStep() {
        refreshKindBar();
        if (exam.saved) { showExamPanel('done'); return; }
        var sid = currentSubjectId();
        if (!sid) { mountExamFrame(); return; }
        fetchProgress(sid)
            .then(function (data) {
                if (wizardCtrl.current() !== 7) return;
                if (!(data.question_count > 0)) {
                    examEl('fwExamBlockedMsg').textContent = questionCountText(data) + ' Hace falta al menos una: se pueden cargar o generar en el paso anterior.';
                    showExamPanel('blocked');
                    return;
                }
                mountExamFrame();
            })
            .catch(function () { if (wizardCtrl.current() === 7) mountExamFrame(); });
    }

    // Panel de salida del iframe (ver wireExamStep): reemplaza al iframe mientras
    // dura el problema; la barra del host sigue oculta, así que los tres botones
    // del panel son la única salida y por eso no pueden faltar.
    function showExamFallback(show) {
        var panel = examEl('fwExamFallback');
        if (!panel) return;
        panel.classList.toggle('d-none', !show);
        examEl('fwExamFrame').classList.toggle('d-none', !!show);
        if (show) examEl('fwExamLoading').classList.add('d-none');
    }

    function onExamSaved(d) {
        exam.saved = true;
        var oral = exam.kind === 'oral';
        clearExamDraft();
        clearOralDraft();
        // El recorrido terminó: no tiene sentido ofrecer "retomarlo" después.
        if (draft) draft.clear();
        examEl('fwExamDoneTitle').textContent = oral ? 'Cuestionario oral guardado' : 'Examen guardado';
        examEl('fwExamDoneMsg').textContent = d.message || (oral
            ? 'El cuestionario oral se guardó correctamente.' : 'El examen se guardó correctamente.');
        examEl('fwExamDoneViewText').textContent = oral ? 'Ver el cuestionario' : 'Ver el examen';
        examEl('fwExamDoneAnotherText').textContent = oral ? 'Armar otro cuestionario' : 'Armar otro examen';
        var avisos = examEl('fwExamDoneWarnings');
        avisos.innerHTML = '';
        (d.warnings || []).forEach(function (texto) {
            var div = document.createElement('div');
            div.className = 'alert alert-warning py-2 px-3 small';
            div.textContent = texto;
            avisos.appendChild(div);
        });
        avisos.classList.toggle('d-none', !(d.warnings || []).length);
        examEl('fwExamDoneView').href = d.viewUrl || (oral ? CFG.urls.listOrals : CFG.urls.misExamenes);
        showExamPanel('done');
        refreshPills();
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    // Cada carga del iframe (el formulario, y también la vista previa tras
    // enviarlo) lo deja a la vista; el aviso de "cargando" es solo para la
    // primera.
    function onExamFrameLoad() {
        if (!exam.url) return;
        examEl('fwExamLoading').classList.add('d-none');
        examEl('fwExamFrame').classList.remove('d-none');
        // Toda pantalla propia avisa 'educaapp:embed-ready' (embed.js) antes
        // de que dispare 'load'. Si no llegó, lo que cargó es otra cosa (una
        // pantalla no enmarcable, el login por sesión vencida, un error del
        // servidor): se ofrece una salida en vez de dejar el recuadro en blanco.
        var seen = exam.readySeen;
        exam.readySeen = false;
        setTimeout(function () {
            if (!seen && !exam.readySeen) showExamFallback(true);
        }, 800);
    }

    // Tras una pantalla bloqueada el navegador no siempre deja volver a navegar
    // el mismo <iframe> (cambiar su src no hace ninguna petición): para
    // reintentar se lo reemplaza por uno nuevo.
    function replaceExamFrame() {
        var old = examEl('fwExamFrame');
        var fresh = document.createElement('iframe');
        fresh.id = 'fwExamFrame';
        fresh.name = 'educaapp-embed-exam';
        fresh.className = old.className;
        fresh.title = old.title;
        fresh.addEventListener('load', onExamFrameLoad);
        old.parentNode.replaceChild(fresh, old);
        return fresh;
    }

    function wireExamStep() {
        var firstFrame = examEl('fwExamFrame');
        if (!firstFrame) return;
        firstFrame.addEventListener('load', onExamFrameLoad);
        // Una pantalla que el navegador bloquea (X-Frame-Options) no siempre
        // dispara 'load': por eso, además, se vigila que el iframe siga siendo
        // de este origen. Si pasó a ser de otro (la pantalla de error del
        // navegador), no es una pantalla nuestra y se ofrece la salida.
        setInterval(function () {
            if (!exam.url || exam.saved) return;
            if (examEl('fwExamStage').classList.contains('d-none')) return;
            var frame = examEl('fwExamFrame');
            if (frame.classList.contains('d-none')) return;
            try { void frame.contentWindow.location.href; } catch (e) { showExamFallback(true); }
        }, 1500);
        window.addEventListener('message', function (e) {
            if (e.origin !== window.location.origin || e.source !== examEl('fwExamFrame').contentWindow) return;
            var d = e.data || {};
            if (d.type === 'educaapp:embed-ready') { exam.readySeen = true; showExamFallback(false); }
            // "Atrás" en el primer paso del asistente de examen: vuelve al
            // paso Preguntas del host (el progreso del examen queda en el iframe).
            if (d.type === 'educaapp:exam-exit' || d.type === 'educaapp:oral-exit') examEl('wizBackBtn').click();
            else if (d.type === 'educaapp:oral-saved') onExamSaved({ message: '', viewUrl: d.viewUrl, warnings: d.warnings });
            else if (d.type === 'educaapp:exam-saved') onExamSaved(d);
        });
        examEl('fwExamBlockedBtn').addEventListener('click', function () { examEl('wizBackBtn').click(); });
        document.querySelectorAll('#fwKindBar [data-kind]').forEach(function (btn) {
            btn.addEventListener('click', function () { setExamKind(btn.dataset.kind); });
        });
        examEl('fwExamFallbackRetry').addEventListener('click', function () {
            exam.url = null;
            showExamFallback(false);
            mountExamFrame(true);
        });
        examEl('fwExamFallbackReload').addEventListener('click', function () { window.location.reload(); });
        examEl('fwExamFallbackBack').addEventListener('click', function () { examEl('wizBackBtn').click(); });
        examEl('fwExamDoneAnother').addEventListener('click', function () {
            exam.saved = false;
            exam.url = null;
            clearExamDraft();
            clearOralDraft();
            mountExamFrame();
            refreshPills();
        });
        var finish = examEl('wizSubmitBtn');
        if (finish && draft) finish.addEventListener('click', function () { draft.clear(); });
    }

    document.addEventListener('DOMContentLoaded', function () {
        catalogHandlersRef = CATALOG_STEPS.map(setupCatalogStep);
        outcomesHandlerRef = setupOutcomesStep();
        wireExamStep();
        setupTemplateBox();

        var embedRoot = document.querySelector('#fwQEmbed [data-uqw]');
        if (embedRoot) {
            embed.root = embedRoot;
            embed.pristine = embedRoot.cloneNode(true);
        }
        var genLinkEl = document.getElementById('fwQGenLink');
        if (genLinkEl) genLinkEl.addEventListener('click', function () { STATE.currentStep = 6; saveDraft(); });
        var manualBtn = document.getElementById('fwQManualBtn');
        if (manualBtn) manualBtn.addEventListener('click', openQuestionsEmbed);

        wizardCtrl = window.EducaAppWizard.init({
            totalSteps: 7,
            onValidateStep: function () { return true; },
        });

        // Vuelve a cargar la lista de "usar existente" cada vez que se
        // entra a un paso 1-5 (por si el padre cambió, o para refrescar
        // tras volver de una pestaña donde se cargó algo nuevo), y
        // reconfigura el botón inferior compartido para el paso actual.
        var ORIGINAL_NEXT = wizardCtrl.goNext;
        function onEnterStep(n) {
            // Entrar a cualquier paso (también por una pastilla del stepper)
            // cierra el asistente de preguntas embebido y repone la barra del host.
            applyQuestionsView(false);
            STATE.currentStep = n;
            saveDraft();
            // La introducción solo ayuda en el primer paso; desde el Preguntas
            // en adelante, en pantallas angostas, tampoco se muestran las migas
            // (empujaban el contenido útil fuera de la primera pantalla).
            toggleTemplateBox(n);
            var wrap = document.querySelector('.wiz-wrap');
            if (wrap) {
                wrap.classList.toggle('fw-past-first', n > 1);
                wrap.classList.toggle('fw-late', n >= 6);
            }
            if (n >= 1 && n <= 4) catalogHandlersRef[n - 1].onEnter();
            else if (n === 5) outcomesHandlerRef.onEnter();
            else if (n === 6) refreshQuestionsLinks();
            else if (n === 7) enterExamStep();
            configureBottomAction(n);
            refreshPills();
        }
        // wizardCtrl.goNext SÍ se puede envolver así porque este archivo lo
        // llama siempre por la propiedad (advance(), continueClick(),
        // requestSkip(), etc.) — nunca desde un listener nativo del engine.
        wizardCtrl.goNext = function () { ORIGINAL_NEXT(); onEnterStep(wizardCtrl.current()); };
        // goBack y goToStep NO se pueden envolver de la misma forma: el
        // engine ata #wizBackBtn y cada pill del stepper directo sobre sus
        // funciones internas (ver wizard_engine.js), no sobre wizardCtrl.*,
        // así que reasignar wizardCtrl.goBack/goToStep nunca intercepta esos
        // clicks — bug real que quedó invisible mientras el botón de avance
        // no dependía de refrescarse al volver, y que ahora sí importa
        // (Saltear/Continuar tiene que quedar bien al volver a un paso ya
        // resuelto). Se agrega un listener extra sobre los mismos
        // elementos, registrado DESPUÉS del init() de arriba: como el
        // engine ya registró el suyo primero sobre el mismo nodo, el click
        // nativo mueve el paso primero (showStep) y recién después dispara
        // este, que ya lee el paso actual correcto.
        function reactAfterNativeNav() { onEnterStep(wizardCtrl.current()); }
        var backBtnEl = document.getElementById('wizBackBtn');
        if (backBtnEl) backBtnEl.addEventListener('click', reactAfterNativeNav);
        document.querySelectorAll('.wiz-step-pill').forEach(function (pill) {
            pill.addEventListener('click', reactAfterNativeNav);
        });

        // Restaurar borrador (sessionStorage) si lo hay — solo el estado ya
        // resuelto de esta pestaña, no reemplaza lo persistido en la base.
        function restoreFromDraft(saved, extra) {
            Object.assign(STATE, saved);
            // Materia elegida en el generador con IA cuando el asistente no
            // tenía ninguna: se adopta antes de llegar al paso Preguntas.
            if (extra && extra.materia) STATE.materia = extra.materia;
            renderBreadcrumb();
            var lastResolvedStep = 0;
            ['institucion', 'facultad', 'carrera', 'materia'].forEach(function (key, idx) {
                if (STATE[key] !== null) lastResolvedStep = idx + 1;
            });
            var target = Math.min(saved.currentStep || (lastResolvedStep + 1), 7);
            for (var i = 1; i < target; i++) { wizardCtrl.goNext(); }
        }

        // Tras generar preguntas con IA en la otra pestaña, al volver a esta
        // el botón inferior tiene que pasar de "Saltear" a "Continuar".
        window.addEventListener('focus', function () {
            if (wizardCtrl.current() === 6 && !embed.active) configureBottomAction(6);
        });

        // Vuelta desde el generador con IA (?retomar=1): se retoma sin
        // preguntar, justo donde se había salido.
        var urlParams = new URLSearchParams(window.location.search);
        if (draft && urlParams.get('retomar') === '1') {
            var back = draft.load();
            if (back) {
                var mid = urlParams.get('materia_id');
                var extra = null;
                if (mid && /^\d+$/.test(mid) && !(back.materia && !back.materia.skipped)) {
                    extra = { materia: { id: parseInt(mid, 10), name: urlParams.get('materia_nombre') || 'Materia', skipped: false } };
                }
                restoreFromDraft(back, extra);
                saveDraft();
                window.history.replaceState(null, '', window.location.pathname);
                return;
            }
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
