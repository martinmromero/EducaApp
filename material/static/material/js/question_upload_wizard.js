// question_upload_wizard.js — Asistente "Subir preguntas" (una sola o por lote).
//
// DISEÑO PENSADO PARA EMBEBERSE: más adelante este asistente se integra como
// paso del Asistente completo (/asistente-completo/, paso 7 "Preguntas"). Por
// eso es un módulo autocontenido, no una página:
//   - mount(root, opciones) trabaja SOLO dentro de `root` (data-role /
//     data-uqw-step), sin ids globales ni document.querySelector.
//   - NO usa wizard_engine.js: ese motor busca .wiz-step/.wiz-step-pill con
//     document.querySelectorAll y un asistente anidado le pisaría el estado
//     de sus propios pasos al host. La navegación entre pasos es propia (y
//     chica); el aspecto replica el de wizard_common.css con clases .uqw-*.
//   - Todo endpoint es JSON puro y recibe la materia por parámetro: nada
//     depende de la página que lo hospeda.
//
// Opciones de mount(root, opciones):
//   urls          mapa de endpoints (por defecto window.EducaAppQuestionUploadUrls,
//                 que escribe el partial questions/_upload_wizard.html).
//   subject       {id, name} materia ya elegida. Sin lockSubject arranca en el
//                 paso "Qué cargar" pero se puede cambiar volviendo atrás.
//   lockSubject   true => el paso "Materia" no existe (el host ya la resolvió,
//                 ej. el paso Materia del Asistente completo) y no se puede
//                 cambiar desde acá. Exige `subject`.
//   draftKey      clave de sessionStorage del borrador (una por host, para que
//                 dos asistentes en la misma pestaña no se pisen).
//   finishLabel   texto del botón final del resultado (por defecto "Terminar").
//   onFinished    function(resultado) al apretar el botón final. resultado =
//                 {kind: 'single'|'batch', created, subject}. En el Asistente
//                 completo es el momento de avanzar al paso siguiente.
//   onCreated     function(resultado) apenas se guarda/importa algo (antes de
//                 que la persona toque nada más) — para que el host refresque
//                 su "¿ya hay preguntas?" sin esperar al botón final.
//   navLinksHtml  HTML (del host, no de usuarios) para el centro de la barra
//                 inferior.
//   doneNote      function(resultado) -> Promise<string|null>: texto extra
//                 para la pantalla final (ej. "la materia ya tiene N
//                 preguntas"). Lo arma el host; acá solo se muestra.
//   onExit        function() — si se pasa, "Atrás" también se muestra en el
//                 primer paso y llama a esto (el host vuelve a lo que había
//                 antes de abrir el asistente). Así el host puede ocultar su
//                 propia barra inferior y quedar un solo "Atrás".
//
// Devuelve {goTo(id), getState(), setSubject({id,name})}.
window.EducaAppQuestionUpload = (function () {
    'use strict';

    function getCookie(name) {
        var v = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
        return v ? v.pop() : '';
    }

    function el(tag, className, text) {
        var node = document.createElement(tag);
        if (className) node.className = className;
        if (text !== undefined && text !== null) node.textContent = text;
        return node;
    }

    function debounce(fn, ms) {
        var t;
        return function () {
            var args = arguments, ctx = this;
            clearTimeout(t);
            t = setTimeout(function () { fn.apply(ctx, args); }, ms);
        };
    }

    function mount(root, options) {
        options = options || {};
        var URLS = options.urls || window.EducaAppQuestionUploadUrls || {};
        var DRAFT_KEY = options.draftKey || 'educaapp_question_upload_wizard_draft_v1';
        var lockSubject = !!(options.lockSubject && options.subject);

        function $(name) { return root.querySelector('[data-role="' + name + '"]'); }
        function $$(name) { return Array.prototype.slice.call(root.querySelectorAll('[data-role="' + name + '"]')); }
        function stepEl(id) { return root.querySelector('[data-uqw-step="' + id + '"]'); }

        // ── Estado ──────────────────────────────────────────────────────
        var STATE = {
            subject: options.subject ? { id: options.subject.id, name: options.subject.name } : null,
            mode: null,                 // 'single' | 'batch'
            topic: null,                // {id, name}
            subtopic: null,
            file: null,                 // File (no se guarda en el borrador)
            preview: null,              // respuesta de la vista previa
            result: null,
        };
        var current = null;
        var maxIdx = 0;
        var busy = false;

        // ── Pasos y navegación ──────────────────────────────────────────
        function stepsList() {
            var list = [];
            if (!lockSubject) list.push({ id: 'subject', label: 'Materia' });
            list.push({ id: 'mode', label: 'Qué cargar' });
            if (STATE.mode === 'single') {
                list.push({ id: 'question', label: 'Pregunta' }, { id: 'classify', label: 'Clasificación' }, { id: 'review', label: 'Revisión' });
            } else if (STATE.mode === 'batch') {
                list.push({ id: 'file', label: 'Archivo' }, { id: 'review', label: 'Revisión' });
            } else {
                list.push({ id: null, label: 'Carga' });
            }
            return list;
        }

        function indexOfStep(id) {
            var list = stepsList();
            for (var i = 0; i < list.length; i++) if (list[i].id === id) return i;
            return -1;
        }

        function renderStepper() {
            var nav = $('stepper');
            nav.innerHTML = '';
            var finished = current === 'done';
            stepsList().forEach(function (s, i) {
                var pill = el('div', 'uqw-pill');
                var num = el('span', 'uqw-pill-num');
                var isDone = finished || i < maxIdx;
                if (isDone) num.innerHTML = '<i class="bi bi-check-lg"></i>'; else num.textContent = String(i + 1);
                pill.appendChild(num);
                pill.appendChild(el('span', 'uqw-pill-label', s.label));
                if (s.id === current) pill.classList.add('is-active');
                if (isDone) pill.classList.add('is-done');
                if (!finished && s.id && i <= maxIdx && s.id !== current) {
                    pill.classList.add('is-reachable');
                    pill.addEventListener('click', function () { goTo(s.id); });
                }
                nav.appendChild(pill);
            });
        }

        function renderContext() {
            var box = $('context');
            if (!box) return;
            var show = STATE.subject && current !== 'subject' && current !== 'done';
            box.style.display = show ? '' : 'none';
            if (!show) return;
            box.innerHTML = '';
            box.appendChild(el('i', 'bi bi-journal-bookmark me-1'));
            box.appendChild(document.createTextNode('Materia: '));
            box.appendChild(el('strong', '', STATE.subject.name));
            if (!lockSubject) {
                var change = el('button', 'btn btn-link btn-sm p-0 ms-2', 'cambiar');
                change.type = 'button';
                change.addEventListener('click', function () { goTo('subject'); });
                box.appendChild(change);
            }
        }

        function setMsg(name, msg) {
            var node = $(name);
            if (!node) return;
            node.textContent = msg || '';
            node.style.display = msg ? 'block' : 'none';
        }

        function goTo(id) {
            current = id;
            root.querySelectorAll('[data-uqw-step]').forEach(function (s) {
                s.classList.toggle('is-active', s.getAttribute('data-uqw-step') === id);
            });
            var idx = indexOfStep(id);
            if (idx > maxIdx) maxIdx = idx;
            if (ENTER[id]) ENTER[id]();
            configureNav();
            renderStepper();
            renderContext();
            var rect = root.getBoundingClientRect();
            if (rect.top < 0) root.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }

        function next() {
            var list = stepsList();
            var i = indexOfStep(current);
            if (i >= 0 && i < list.length - 1 && list[i + 1].id) goTo(list[i + 1].id);
        }

        function back() {
            var list = stepsList();
            var i = indexOfStep(current);
            if (i > 0) goTo(list[i - 1].id);
            else if (options.onExit) options.onExit();
        }

        // Barra inferior: un solo botón de acción cuyo texto/estado/handler
        // depende del paso.
        var actionHandler = null;
        function setAction(label, enabled, handler, icon) {
            var btn = $('action');
            // visibility (no display): mantiene el lugar para que "Atrás" y los
            // enlaces del centro no salten de posición entre pasos.
            btn.style.visibility = label ? 'visible' : 'hidden';
            btn.disabled = !enabled || busy;
            btn.innerHTML = '';
            btn.appendChild(document.createTextNode(label || ''));
            if (icon !== false) btn.appendChild(el('i', 'bi ' + (icon || 'bi-arrow-right') + ' ms-1'));
            actionHandler = handler;
        }

        function configureNav() {
            var nav = $('nav');
            nav.classList.toggle('is-hidden', current === 'done');
            $('back').style.visibility = (indexOfStep(current) > 0 || options.onExit) ? 'visible' : 'hidden';
            if (current === 'subject') setAction('Siguiente', !!STATE.subject, next);
            else if (current === 'mode') setAction(STATE.mode ? 'Siguiente' : '', !!STATE.mode, next);
            else if (current === 'question') setAction('Siguiente', true, function () { if (validateQuestion()) next(); });
            else if (current === 'classify') setAction('Siguiente', true, next);
            else if (current === 'file') setAction('Siguiente', !!(STATE.preview && STATE.preview.valid > 0), next);
            else if (current === 'review') {
                if (STATE.mode === 'single') setAction('Guardar pregunta', true, saveSingle, 'bi-check2');
                else setAction('Importar ' + (STATE.preview ? STATE.preview.valid : '') + ' preguntas', !!STATE.preview, importBatch, 'bi-check2');
            }
        }

        function setBusy(value) {
            busy = value;
            $('action').disabled = value || $('action').disabled;
            if (!value) configureNav();
        }

        // ── Red ─────────────────────────────────────────────────────────
        function request(url, init) {
            init = init || {};
            init.headers = Object.assign({ 'X-CSRFToken': getCookie('csrftoken') }, init.headers || {});
            return fetch(url, init).then(function (r) {
                return r.json().catch(function () { return {}; }).then(function (data) {
                    return { status: r.status, ok: r.ok, data: data };
                });
            });
        }
        function postJSON(url, body) {
            return request(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
        }
        function postForm(url, formData) {
            return request(url, { method: 'POST', body: formData });
        }

        // ── Paso: Materia ───────────────────────────────────────────────
        var subjectItems = [];
        function renderSubjectChips() {
            var box = $('subject-chips');
            box.innerHTML = '';
            var items = subjectItems.slice();
            var searching = !!$('subject-search').value.trim();
            if (!searching && STATE.subject && !items.some(function (s) { return s.id === STATE.subject.id; })) {
                items.unshift({ id: STATE.subject.id, name: STATE.subject.name, personal: false });
            }
            $('subject-empty').style.display = items.length ? 'none' : 'block';
            items.forEach(function (s) {
                var chip = el('button', 'uqw-chip');
                chip.type = 'button';
                chip.appendChild(el('span', '', s.name));
                if (s.personal) chip.appendChild(el('span', 'badge bg-secondary-subtle text-secondary-emphasis', 'Personal'));
                if (STATE.subject && STATE.subject.id === s.id) chip.classList.add('is-selected');
                chip.addEventListener('click', function () { chooseSubject({ id: s.id, name: s.name }, true); });
                box.appendChild(chip);
            });
            updateSubjectCreateBtn();
        }

        function updateSubjectCreateBtn() {
            var text = $('subject-search').value.trim().toLowerCase();
            var exists = subjectItems.some(function (s) { return s.name.trim().toLowerCase() === text; });
            $('subject-create').disabled = !text || exists || busy;
        }

        function loadSubjects() {
            var q = $('subject-search').value.trim();
            var url = URLS.subjects + (q ? '?q=' + encodeURIComponent(q) : '');
            return fetch(url)
                .then(function (r) { return r.json(); })
                .then(function (data) { subjectItems = data.subjects || []; renderSubjectChips(); })
                .catch(function () { subjectItems = []; renderSubjectChips(); });
        }

        function chooseSubject(subject, advance) {
            var changed = !STATE.subject || STATE.subject.id !== subject.id;
            if (changed) {
                // Todo lo que depende de la materia (tópicos, contenidos, la
                // vista previa del lote) deja de valer.
                STATE.topic = null; STATE.subtopic = null; STATE.preview = null;
                topicsLoadedFor = null; contenidosLoadedFor = null;
            }
            STATE.subject = subject;
            setMsg('subject-error', '');
            renderSubjectChips();
            renderContext();
            configureNav();
            if (advance) next();
        }

        function createSubject() {
            var name = $('subject-search').value.trim();
            if (!name) return;
            setMsg('subject-error', '');
            busy = true; updateSubjectCreateBtn();
            postJSON(URLS.saveCatalogStep, { step: 'materia', action: 'nueva', new_name: name })
                .then(function (res) {
                    busy = false;
                    if (!res.data.ok) { setMsg('subject-error', res.data.error || 'No se pudo crear la materia.'); updateSubjectCreateBtn(); return; }
                    $('subject-search').value = '';
                    chooseSubject({ id: res.data.id, name: res.data.name }, true);
                    loadSubjects();
                })
                .catch(function () { busy = false; setMsg('subject-error', 'Error de red — reintentar.'); updateSubjectCreateBtn(); });
        }

        // ── Paso: Modo ──────────────────────────────────────────────────
        function setMode(mode) {
            if (STATE.mode !== mode) {
                STATE.mode = mode;
                // Los pasos posteriores al "modo" cambian de nombre y de
                // cantidad: lo ya recorrido de la otra rama deja de valer.
                maxIdx = Math.min(maxIdx, indexOfStep('mode'));
            }
            $$('mode-card').forEach(function (b) { b.classList.toggle('is-selected', b.getAttribute('data-mode') === mode); });
            next();
        }

        // ── Paso (una): Pregunta y respuesta ────────────────────────────
        var TYPE_HINTS = {
            opcion_multiple: 'Redactar la pregunta sin incluir las opciones: se cargan abajo.',
            verdadero_falso: 'Redactar el enunciado como una afirmación que se pueda juzgar como verdadera o falsa.',
            completar_blank: 'Marcar el espacio en blanco del enunciado con ___ (tres guiones bajos).',
            desarrollo: '',
        };

        function getType() {
            var checked = root.querySelector('input[name="uqw_type"]:checked');
            return checked ? checked.value : 'desarrollo';
        }

        function updateTypeUI() {
            var t = getType();
            $('mc-box').style.display = t === 'opcion_multiple' ? '' : 'none';
            $('tf-box').style.display = t === 'verdadero_falso' ? '' : 'none';
            $('answer-box').style.display = (t === 'desarrollo' || t === 'completar_blank') ? '' : 'none';
            $('answer-label').textContent = t === 'completar_blank' ? 'Texto que completa el espacio' : 'Respuesta esperada';
            $('question-hint').textContent = TYPE_HINTS[t] || '';
        }

        function mcOptions() {
            return $$('mc-option').map(function (i) { return i.value.trim(); });
        }
        function mcCorrectIndex() {
            var c = root.querySelector('input[name="uqw_correct"]:checked');
            return c ? parseInt(c.value, 10) : -1;
        }
        function tfValue() {
            var c = root.querySelector('input[name="uqw_tf"]:checked');
            return c ? c.value : '';
        }

        // Lo que se guarda como respuesta/opciones según el tipo — mismo
        // formato que ya produce la carga por lote.
        function computeAnswer() {
            var t = getType();
            if (t === 'opcion_multiple') {
                var opts = mcOptions();
                var idx = mcCorrectIndex();
                return { answer: idx >= 0 ? opts[idx] : '', options: opts.filter(function (o) { return o; }) };
            }
            if (t === 'verdadero_falso') return { answer: tfValue(), options: [] };
            return { answer: $('answer-text').value.trim(), options: [] };
        }

        function validateQuestion() {
            var t = getType();
            if (!$('question-text').value.trim()) return failQuestion('Falta escribir el enunciado de la pregunta.');
            if (t === 'opcion_multiple') {
                var opts = mcOptions();
                var filled = opts.filter(function (o) { return o; }).length;
                if (filled < 2) return failQuestion('Una pregunta de opción múltiple necesita al menos dos opciones.');
                var idx = mcCorrectIndex();
                if (idx < 0 || !opts[idx]) return failQuestion('Falta marcar cuál de las opciones es la correcta (y que no esté vacía).');
            } else if (t === 'verdadero_falso') {
                if (!tfValue()) return failQuestion('Falta indicar si la respuesta correcta es Verdadero o Falso.');
            } else if (!$('answer-text').value.trim()) {
                return failQuestion('Falta escribir la respuesta esperada.');
            }
            setMsg('question-error', '');
            return true;
        }
        function failQuestion(msg) { setMsg('question-error', msg); return false; }

        // ── Paso (una): Clasificación ───────────────────────────────────
        var topicsLoadedFor = null;
        var contenidosLoadedFor = null;
        var topicItems = [];
        var subtopicItems = [];

        function renderTopicChips() {
            var box = $('topic-chips');
            box.innerHTML = '';
            var items = topicItems.slice();
            if (STATE.topic && !items.some(function (t) { return String(t.id) === String(STATE.topic.id); })) items.unshift(STATE.topic);
            if (!items.length) box.appendChild(el('span', 'text-muted small', 'Esta materia todavía no tiene tópicos — agregar uno abajo.'));
            items.forEach(function (t) {
                var chip = el('button', 'uqw-chip', t.name);
                chip.type = 'button';
                if (STATE.topic && String(STATE.topic.id) === String(t.id)) chip.classList.add('is-selected');
                chip.addEventListener('click', function () {
                    // Un segundo clic sobre el elegido lo deselecciona (el
                    // tópico es opcional).
                    var same = STATE.topic && String(STATE.topic.id) === String(t.id);
                    STATE.topic = same ? null : { id: t.id, name: t.name };
                    STATE.subtopic = null;
                    renderTopicChips();
                    loadSubtopics();
                    notifyChange();
                });
                box.appendChild(chip);
            });
        }

        function loadTopics() {
            if (topicsLoadedFor === STATE.subject.id) { renderTopicChips(); loadSubtopics(); return; }
            fetch(URLS.getTopics + '?subject_id=' + encodeURIComponent(STATE.subject.id))
                .then(function (r) { return r.json(); })
                .then(function (data) { topicItems = data || []; topicsLoadedFor = STATE.subject.id; renderTopicChips(); loadSubtopics(); })
                .catch(function () { topicItems = []; renderTopicChips(); });
        }

        function renderSubtopicChips() {
            var box = $('subtopic-chips');
            box.innerHTML = '';
            var items = subtopicItems.slice();
            if (STATE.subtopic && !items.some(function (t) { return String(t.id) === String(STATE.subtopic.id); })) items.unshift(STATE.subtopic);
            if (!items.length) box.appendChild(el('span', 'text-muted small', 'Este tópico todavía no tiene sub-tópicos.'));
            items.forEach(function (t) {
                var chip = el('button', 'uqw-chip', t.name);
                chip.type = 'button';
                if (STATE.subtopic && String(STATE.subtopic.id) === String(t.id)) chip.classList.add('is-selected');
                chip.addEventListener('click', function () {
                    var same = STATE.subtopic && String(STATE.subtopic.id) === String(t.id);
                    STATE.subtopic = same ? null : { id: t.id, name: t.name };
                    renderSubtopicChips();
                    notifyChange();
                });
                box.appendChild(chip);
            });
        }

        function loadSubtopics() {
            var box = $('subtopic-box');
            if (!STATE.topic) { box.style.display = 'none'; subtopicItems = []; return; }
            box.style.display = '';
            fetch(URLS.getSubtopics + '?topic_id=' + encodeURIComponent(STATE.topic.id))
                .then(function (r) { return r.json(); })
                .then(function (data) { subtopicItems = data || []; renderSubtopicChips(); })
                .catch(function () { subtopicItems = []; renderSubtopicChips(); });
        }

        function createTopic() {
            var name = $('topic-new').value.trim();
            if (!name) return;
            setMsg('classify-error', '');
            var fd = new FormData();
            fd.append('name', name);
            fd.append('subject_id', STATE.subject.id);
            postForm(URLS.addTopic, fd).then(function (res) {
                if (!res.data.success) { setMsg('classify-error', res.data.error || 'No se pudo crear el tópico.'); return; }
                var t = res.data.topic;
                topicItems.push({ id: t.id, name: t.name });
                STATE.topic = { id: t.id, name: t.name };
                STATE.subtopic = null;
                $('topic-new').value = '';
                renderTopicChips(); loadSubtopics(); notifyChange();
            }).catch(function () { setMsg('classify-error', 'Error de red — reintentar.'); });
        }

        function createSubtopic() {
            var name = $('subtopic-new').value.trim();
            if (!name || !STATE.topic) return;
            setMsg('classify-error', '');
            postJSON(URLS.addSubtopic, { name: name, topic_id: STATE.topic.id }).then(function (res) {
                if (!res.data.success) { setMsg('classify-error', res.data.error || 'No se pudo crear el sub-tópico.'); return; }
                var t = res.data.subtopic;
                subtopicItems.push({ id: t.id, name: t.name });
                STATE.subtopic = { id: t.id, name: t.name };
                $('subtopic-new').value = '';
                renderSubtopicChips(); notifyChange();
            }).catch(function () { setMsg('classify-error', 'Error de red — reintentar.'); });
        }

        function loadContenidos() {
            if (contenidosLoadedFor === STATE.subject.id) return;
            var select = $('contenido');
            var keep = select.value;
            fetch(URLS.contenidos + '?subject_id=' + encodeURIComponent(STATE.subject.id))
                .then(function (r) { return r.json(); })
                .then(function (data) {
                    contenidosLoadedFor = STATE.subject.id;
                    select.innerHTML = '';
                    select.appendChild(new Option('Ninguno', ''));
                    (data.contenidos || []).forEach(function (c) { select.appendChild(new Option(c.title, c.id)); });
                    if (keep) select.value = keep;
                })
                .catch(function () {});
        }

        function previewImage(input, previewRole) {
            var box = $(previewRole);
            box.innerHTML = '';
            var f = input.files && input.files[0];
            if (!f) return;
            var img = document.createElement('img');
            img.alt = 'Vista previa de la imagen elegida';
            img.src = URL.createObjectURL(f);
            box.appendChild(img);
        }

        // ── Paso (lote): Archivo ────────────────────────────────────────
        function setFile(file) {
            STATE.file = file || null;
            STATE.preview = null;
            var zone = $('dropzone');
            zone.classList.toggle('has-file', !!file);
            $('file-name').textContent = file ? file.name : 'Elegir un archivo .csv o .txt (o arrastrarlo hasta acá)';
            if (!file) { $('file-status').innerHTML = ''; configureNav(); return; }
            runPreview();
        }

        function statusBox(kind, children) {
            var box = el('div', 'alert alert-' + kind + ' mb-0');
            children.forEach(function (c) { box.appendChild(typeof c === 'string' ? document.createTextNode(c) : c); });
            return box;
        }

        function issuesList(items, total) {
            var ul = el('ul', 'uqw-issues');
            items.forEach(function (t) { ul.appendChild(el('li', '', t)); });
            if (total > items.length) ul.appendChild(el('li', '', '… y ' + (total - items.length) + ' más.'));
            return ul;
        }

        function runPreview() {
            var status = $('file-status');
            status.innerHTML = '';
            status.appendChild(el('div', 'text-muted small', 'Revisando el archivo…'));
            configureNav();
            var fd = new FormData();
            fd.append('file', STATE.file);
            fd.append('subject_id', STATE.subject.id);
            var requestedFor = STATE.file;
            postForm(URLS.preview, fd).then(function (res) {
                if (STATE.file !== requestedFor) return; // eligió otro archivo mientras tanto
                status.innerHTML = '';
                if (!res.data.ok) {
                    STATE.preview = null;
                    status.appendChild(statusBox('danger', [res.data.error || 'No se pudo leer el archivo.']));
                    configureNav();
                    return;
                }
                STATE.preview = res.data;
                var p = res.data;
                if (p.valid === 0) {
                    var box = statusBox('danger', ['No se encontró ninguna pregunta válida en el archivo.']);
                    if (p.errors.length) box.appendChild(issuesList(p.errors, p.error_count));
                    status.appendChild(box);
                } else {
                    var kind = p.error_count ? 'warning' : 'success';
                    var b = statusBox(kind, [
                        el('strong', '', p.valid + (p.valid === 1 ? ' pregunta válida' : ' preguntas válidas')),
                        p.error_count ? ' — ' + p.error_count + (p.error_count === 1 ? ' fila no se puede importar.' : ' filas no se pueden importar.') : ' — todo en orden.',
                    ]);
                    if (p.errors.length) b.appendChild(issuesList(p.errors, p.error_count));
                    status.appendChild(b);
                }
                configureNav();
            }).catch(function () {
                status.innerHTML = '';
                status.appendChild(statusBox('danger', ['Error de red al revisar el archivo — reintentar.']));
            });
        }

        // ── Paso: Revisión ──────────────────────────────────────────────
        function addRow(box, label, value) {
            var row = el('div', 'uqw-row');
            row.appendChild(el('span', '', label));
            var v = el('span');
            if (value instanceof Node) v.appendChild(value); else v.textContent = value;
            row.appendChild(v);
            box.appendChild(row);
        }

        function truncate(text, n) { return text.length > n ? text.slice(0, n) + '…' : text; }

        function renderReview() {
            var body = $('review-body');
            body.innerHTML = '';
            setMsg('review-error', '');
            $('skip-dup-box').style.display = 'none';
            if (STATE.mode === 'single') renderReviewSingle(body); else renderReviewBatch(body);
        }

        var TYPE_LABELS = { opcion_multiple: 'Opción múltiple', verdadero_falso: 'Verdadero/Falso', completar_blank: 'Completar el espacio', desarrollo: 'Desarrollo' };

        function renderReviewSingle(body) {
            $('review-title').textContent = 'Revisión';
            $('review-intro').textContent = 'Revisar los datos antes de guardar la pregunta.';
            var t = getType();
            var a = computeAnswer();
            addRow(body, 'Materia', STATE.subject.name);
            addRow(body, 'Tipo', TYPE_LABELS[t]);
            addRow(body, 'Enunciado', truncate($('question-text').value.trim(), 240));
            if (t === 'opcion_multiple') {
                var list = el('div');
                mcOptions().forEach(function (o, i) {
                    if (!o) return;
                    var line = el('div', '', 'ABCD'.charAt(i) + '. ' + o + (i === mcCorrectIndex() ? '  ✓' : ''));
                    if (i === mcCorrectIndex()) line.className = 'fw-semibold';
                    list.appendChild(line);
                });
                addRow(body, 'Opciones', list);
            } else {
                addRow(body, 'Respuesta', truncate(a.answer, 240));
            }
            addRow(body, 'Tópico', STATE.topic ? STATE.topic.name : 'Sin tópico');
            if (STATE.topic) addRow(body, 'Sub-tópico', STATE.subtopic ? STATE.subtopic.name : '—');
            addRow(body, 'Dificultad', $('difficulty').selectedOptions[0].textContent);
            if ($('bloom').value) addRow(body, 'Nivel de Bloom', $('bloom').selectedOptions[0].textContent);
            var images = [];
            if ($('question-image').files.length) images.push('pregunta');
            if ($('answer-image').files.length) images.push('respuesta');
            if (images.length) addRow(body, 'Imágenes', images.join(' y '));
            if ($('contenido').value) addRow(body, 'Contenido de origen', $('contenido').selectedOptions[0].textContent);
            if ($('source-page').value) addRow(body, 'Página', $('source-page').value);
        }

        function renderReviewBatch(body) {
            var p = STATE.preview;
            $('review-title').textContent = 'Revisión del lote';
            $('review-intro').textContent = 'Esto es lo que se va a importar. Todavía no se guardó nada.';
            if (!p) return;
            addRow(body, 'Materia', STATE.subject.name);
            addRow(body, 'Archivo', STATE.file ? STATE.file.name : '—');
            addRow(body, 'Preguntas a importar', String(p.valid));
            if (p.error_count) {
                var errBox = el('div');
                errBox.appendChild(document.createTextNode(p.error_count + ' (no se importan)'));
                errBox.appendChild(issuesList(p.errors, p.error_count));
                addRow(body, 'Filas con problemas', errBox);
            }
            addRow(body, 'Tipos', p.types.map(function (t) { return t.label + ' (' + t.count + ')'; }).join(' · '));

            var topics = el('div');
            p.topics.forEach(function (t) {
                var line = el('div', '', t.name + ' (' + t.count + ')');
                if (t.is_new) line.appendChild(el('span', 'badge bg-info-subtle text-info-emphasis ms-2', 'se crea'));
                topics.appendChild(line);
            });
            addRow(body, 'Tópicos', topics);

            if (p.warning_count) {
                var warn = el('div');
                warn.appendChild(document.createTextNode(p.warning_count + ' (se importan igual; conviene revisarlas después)'));
                warn.appendChild(issuesList(p.warnings, p.warning_count));
                addRow(body, 'Avisos', warn);
            }

            if (p.sample.length) {
                var table = el('table', 'uqw-sample');
                var head = el('tr');
                ['Fila', 'Pregunta', 'Respuesta', 'Tipo', 'Tópico'].forEach(function (h) { head.appendChild(el('th', '', h)); });
                table.appendChild(head);
                p.sample.forEach(function (s) {
                    var tr = el('tr');
                    [s.label, s.question, s.answer, s.type, s.topic].forEach(function (c) { tr.appendChild(el('td', '', c)); });
                    table.appendChild(tr);
                });
                var wrap = el('div', 'mt-3');
                wrap.appendChild(el('div', 'text-muted small mb-1', 'Primeras ' + p.sample.length + ' preguntas del archivo:'));
                wrap.appendChild(table);
                body.appendChild(wrap);
            }

            if (p.duplicates > 0) {
                $('skip-dup-box').style.display = '';
                $('skip-dup-label').textContent = p.duplicates === 1
                    ? 'Omitir la pregunta cuyo enunciado ya existe en esta materia (evita duplicarla).'
                    : 'Omitir las ' + p.duplicates + ' preguntas cuyo enunciado ya existe en esta materia (evita duplicarlas).';
            }
        }

        // ── Guardar / importar ──────────────────────────────────────────
        function saveSingle() {
            setMsg('review-error', '');
            var a = computeAnswer();
            var fd = new FormData();
            fd.append('subjects', STATE.subject.id);
            fd.append('question_type', getType());
            fd.append('question_text', $('question-text').value.trim());
            fd.append('answer_text', a.answer);
            fd.append('options_json', getType() === 'opcion_multiple' ? JSON.stringify(a.options) : '');
            if (STATE.topic) fd.append('topic', STATE.topic.id);
            if (STATE.topic && STATE.subtopic) fd.append('subtopic', STATE.subtopic.id);
            fd.append('difficulty', $('difficulty').value);
            fd.append('bloom_level', $('bloom').value);
            fd.append('source_page', $('source-page').value);
            fd.append('contenido', $('contenido').value);
            var qi = $('question-image').files[0], ai = $('answer-image').files[0];
            if (qi) fd.append('question_image', qi);
            if (ai) fd.append('answer_image', ai);

            setBusy(true);
            postForm(URLS.save, fd).then(function (res) {
                setBusy(false);
                if (!res.data.ok) { setMsg('review-error', res.data.error || 'No se pudo guardar la pregunta.'); return; }
                clearDraft();
                STATE.result = { kind: 'single', created: 1, subject: STATE.subject, id: res.data.id };
                showDone();
            }).catch(function () { setBusy(false); setMsg('review-error', 'Error de red — reintentar.'); });
        }

        function importBatch() {
            setMsg('review-error', '');
            var fd = new FormData();
            fd.append('file', STATE.file);
            fd.append('subject_id', STATE.subject.id);
            if (STATE.preview && STATE.preview.duplicates > 0 && $('skip-dup').checked) fd.append('skip_duplicates', '1');
            setBusy(true);
            postForm(URLS.importBatch, fd).then(function (res) {
                setBusy(false);
                if (!res.data.ok) { setMsg('review-error', res.data.error || 'No se pudo importar el archivo.'); return; }
                STATE.result = { kind: 'batch', created: res.data.created, skipped: res.data.skipped, errors: res.data.errors, error_count: res.data.error_count, subject: STATE.subject };
                showDone();
            }).catch(function () { setBusy(false); setMsg('review-error', 'Error de red — reintentar.'); });
        }

        function showDone() {
            var r = STATE.result;
            if (options.onCreated) options.onCreated(r);
            var title, body;
            if (r.kind === 'single') {
                title = 'Pregunta guardada';
                body = 'La pregunta quedó cargada en "' + r.subject.name + '".';
            } else {
                title = r.created + (r.created === 1 ? ' pregunta importada' : ' preguntas importadas');
                body = 'Quedaron cargadas en "' + r.subject.name + '".';
                if (r.skipped) body += r.skipped === 1 ? ' Se omitió 1 pregunta que ya existía.' : ' Se omitieron ' + r.skipped + ' preguntas que ya existían.';
            }
            $('done-title').textContent = title;
            $('done-body').textContent = body;
            var warn = $('done-warnings');
            warn.innerHTML = '';
            if (r.kind === 'batch' && r.error_count) {
                warn.style.display = '';
                warn.appendChild(el('strong', '', r.error_count + (r.error_count === 1 ? ' fila no se pudo importar:' : ' filas no se pudieron importar:')));
                warn.appendChild(issuesList(r.errors, r.error_count));
            } else {
                warn.style.display = 'none';
            }
            $('done-again').textContent = r.kind === 'single' ? 'Cargar otra pregunta' : 'Cargar otro archivo';
            $('done-finish').textContent = options.finishLabel || 'Terminar';
            var note = $('done-note');
            if (note) {
                note.style.display = 'none';
                note.textContent = '';
                if (options.doneNote) {
                    Promise.resolve(options.doneNote(r)).then(function (text) {
                        if (text && current === 'done') { note.textContent = text; note.style.display = ''; }
                    }).catch(function () {});
                }
            }
            goTo('done');
        }

        function again() {
            if (STATE.mode === 'single') {
                // Se conserva lo que suele repetirse entre preguntas seguidas
                // (materia, tópico, sub-tópico, dificultad); se vacía lo propio
                // de cada pregunta.
                $('question-text').value = '';
                $('answer-text').value = '';
                $$('mc-option').forEach(function (i) { i.value = ''; });
                root.querySelectorAll('input[name="uqw_correct"], input[name="uqw_tf"]').forEach(function (i) { i.checked = false; });
                ['question-image', 'answer-image'].forEach(function (r) { $(r).value = ''; $(r + '-preview').innerHTML = ''; });
                $('source-page').value = '';
                setMsg('question-error', '');
                maxIdx = indexOfStep('question');
                goTo('question');
            } else {
                setFile(null);
                $('file-input').value = '';
                maxIdx = indexOfStep('file');
                goTo('file');
            }
        }

        // ── Borrador (solo "una pregunta": el archivo no se puede guardar) ──
        var draft = window.EducaAppWizardDraft ? window.EducaAppWizardDraft.init(DRAFT_KEY) : null;
        function collectDraft() {
            return {
                subject: STATE.subject, topic: STATE.topic, subtopic: STATE.subtopic,
                type: getType(),
                text: $('question-text').value, answer: $('answer-text').value,
                options: mcOptions(), correct: mcCorrectIndex(), tf: tfValue(),
                difficulty: $('difficulty').value, bloom: $('bloom').value, page: $('source-page').value,
            };
        }
        var saveDraft = debounce(function () {
            if (!draft || STATE.mode !== 'single' || current === 'done') return;
            var d = collectDraft();
            if (d.text.trim()) draft.save(d);
        }, 300);
        function clearDraft() { if (draft) draft.clear(); }
        function notifyChange() { saveDraft(); }

        function applyDraft(d) {
            if (d.subject && !lockSubject) STATE.subject = d.subject;
            STATE.topic = d.topic || null;
            STATE.subtopic = d.subtopic || null;
            STATE.mode = 'single';
            var radio = root.querySelector('input[name="uqw_type"][value="' + d.type + '"]');
            if (radio) radio.checked = true;
            $('question-text').value = d.text || '';
            $('answer-text').value = d.answer || '';
            $$('mc-option').forEach(function (i, idx) { i.value = (d.options && d.options[idx]) || ''; });
            if (d.correct >= 0) { var c = root.querySelector('input[name="uqw_correct"][value="' + d.correct + '"]'); if (c) c.checked = true; }
            if (d.tf) { var tf = root.querySelector('input[name="uqw_tf"][value="' + d.tf + '"]'); if (tf) tf.checked = true; }
            $('difficulty').value = d.difficulty || '1';
            $('bloom').value = d.bloom || '';
            $('source-page').value = d.page || '';
            updateTypeUI();
            maxIdx = indexOfStep('classify');
            goTo('question');
        }

        // ── Entrada a cada paso ─────────────────────────────────────────
        var ENTER = {
            subject: function () { loadSubjects(); },
            mode: function () { $$('mode-card').forEach(function (b) { b.classList.toggle('is-selected', b.getAttribute('data-mode') === STATE.mode); }); },
            question: updateTypeUI,
            classify: function () { loadTopics(); loadContenidos(); },
            file: function () { if (STATE.file && !STATE.preview) runPreview(); },
            review: renderReview,
            done: function () {},
        };

        // ── Cableado de eventos ─────────────────────────────────────────
        $('back').addEventListener('click', back);
        $('action').addEventListener('click', function () { if (actionHandler) actionHandler(); });
        if (options.navLinksHtml) $('nav-links').innerHTML = options.navLinksHtml;

        $('subject-search').addEventListener('input', debounce(function () { loadSubjects(); }, 250));
        $('subject-search').addEventListener('input', updateSubjectCreateBtn);
        $('subject-create').addEventListener('click', createSubject);

        $$('mode-card').forEach(function (b) {
            b.addEventListener('click', function () { setMode(b.getAttribute('data-mode')); });
        });

        root.querySelectorAll('input[name="uqw_type"]').forEach(function (r) { r.addEventListener('change', updateTypeUI); });
        $('topic-create').addEventListener('click', createTopic);
        $('topic-new').addEventListener('keydown', function (e) { if (e.key === 'Enter') { e.preventDefault(); createTopic(); } });
        $('subtopic-create').addEventListener('click', createSubtopic);
        $('subtopic-new').addEventListener('keydown', function (e) { if (e.key === 'Enter') { e.preventDefault(); createSubtopic(); } });
        $('extras-toggle').addEventListener('click', function () {
            var box = $('extras-box');
            box.style.display = box.style.display === 'none' ? '' : 'none';
        });
        $('question-image').addEventListener('change', function () { previewImage(this, 'question-image-preview'); });
        $('answer-image').addEventListener('change', function () { previewImage(this, 'answer-image-preview'); });

        var fileInput = $('file-input');
        fileInput.addEventListener('change', function () { setFile(fileInput.files[0]); });
        var zone = $('dropzone');
        ['dragenter', 'dragover'].forEach(function (ev) {
            zone.addEventListener(ev, function (e) { e.preventDefault(); zone.classList.add('is-over'); });
        });
        ['dragleave', 'drop'].forEach(function (ev) {
            zone.addEventListener(ev, function (e) { e.preventDefault(); zone.classList.remove('is-over'); });
        });
        zone.addEventListener('drop', function (e) {
            var f = e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0];
            if (f) setFile(f);
        });

        $('done-again').addEventListener('click', again);
        $('done-finish').addEventListener('click', function () { if (options.onFinished) options.onFinished(STATE.result); });

        root.addEventListener('input', saveDraft);
        root.addEventListener('change', saveDraft);

        // ── Arranque ────────────────────────────────────────────────────
        function start() {
            var first = lockSubject || STATE.subject ? 'mode' : 'subject';
            goTo(first);
        }

        var saved = draft ? draft.load() : null;
        var draftUsable = saved && saved.text && saved.text.trim() &&
            (!options.subject || !saved.subject || saved.subject.id === options.subject.id);
        if (draftUsable) {
            draft.confirmRestore('Hay una pregunta sin guardar de una visita anterior. ¿Recuperarla?')
                .then(function (yes) {
                    if (yes) applyDraft(saved); else { draft.clear(); start(); }
                });
            // Mientras el diálogo está abierto se muestra el primer paso
            // detrás, para no dejar la pantalla vacía.
            start();
        } else {
            start();
        }

        return {
            goTo: goTo,
            getState: function () { return STATE; },
            setSubject: function (subject) { chooseSubject({ id: subject.id, name: subject.name }, false); },
        };
    }

    return { mount: mount };
})();
