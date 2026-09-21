/*
 * Reusable "only what you already use, then search for anything else"
 * checklist helper.
 *
 * Problema que resuelve (reportado en Modo Testing sobre editar/cargar
 * pregunta a mano): un checklist de opciones (materias, en el primer uso)
 * puede tener cientos de entradas. Mostrar siempre un top-N fijo no
 * alcanza si esas N no significan nada para este usuario puntual — la idea
 * (pedida explícitamente, con el dropdown de Institución del asistente
 * como referencia: "Seleccionar institución / Universidad Abierta
 * Interamericana / Otro, buscar o escribir") es mostrar SOLO lo que este
 * usuario ya "intervino" (favorito, o ya tiene contenido cargado ahí) y
 * recién después ofrecer buscar entre el resto — nunca volcar el resto
 * completo a la pantalla, ni siquiera detrás de un botón: el resto solo
 * aparece a medida que el texto tipeado lo va matcheando.
 *
 * La queryset que arma el server YA viene ordenada por relevancia (ver
 * content_visibility.order_subjects_by_relevance) y el server también
 * informa CUÁNTAS de esas opciones son de verdad relevantes
 * (content_visibility.count_relevant_subjects) — este helper no reordena
 * ni decide relevancia, solo separa visualmente según ese número exacto,
 * y se hace cargo también del filtro de texto (reemplaza cualquier
 * listener de filtro previo sobre el mismo input — no dupliques el
 * tuyo, este ya filtra tanto lo destacado como el resto).
 *
 * Pensado para reusarse en cualquier checklist con el mismo problema, no
 * solo materias — por eso no asume nada de dominio, solo la estructura que
 * arma Django para CheckboxSelectMultiple: un <div> contenedor con un
 * <div> por cada checkbox+label adentro.
 *
 * Uso:
 *   window.EducaAppSmartChecklist.init({
 *     checklistSelector: '.subjects-checklist',
 *     filterInputSelector: '#subjectsFilter',
 *     relevantCount: 3,          // viene del server, no es un número fijo
 *     emptyRestLabel: 'Escribí para buscar entre el resto de las materias',
 *     moreLabel: 'Buscar y agregar otra materia',
 *   });
 */
window.EducaAppSmartChecklist = (function () {
    // Sin esto "algebra" no matcheaba "Álgebra" — antes el usuario podía
    // igual encontrarla scrolleando aunque la búsqueda fallara por el
    // acento; ahora que buscar es la ÚNICA forma de llegar a lo no
    // destacado, ese fallback ya no existe y el acento se vuelve bloqueante.
    function normalize(str) {
        return str.normalize('NFD').replace(/[̀-ͯ]/g, '');
    }
    function itemLabel(item) {
        return normalize(item.textContent.trim().toLowerCase());
    }

    function init(opts) {
        var checklist = document.querySelector(opts.checklistSelector);
        if (!checklist) return null;
        var itemsWrap = checklist.querySelector(':scope > div');
        if (!itemsWrap) return null;
        var filterInput = opts.filterInputSelector && document.querySelector(opts.filterInputSelector);

        var items = Array.prototype.slice.call(itemsWrap.children);
        var relevantCount = opts.relevantCount || 0;
        var featured = items.slice(0, relevantCount);
        var rest = items.slice(relevantCount);

        // Filtro externo opcional (ej. Institución/Facultad/Carrera en
        // upload_questions.html) — null significa "sin restricción". Se
        // combina en AND con el texto tipeado, nunca lo reemplaza.
        var allowedIds = null;
        function isAllowed(item) {
            if (!allowedIds) return true;
            var cb = item.querySelector('input[type=checkbox]');
            return !!(cb && allowedIds.has(cb.value));
        }

        function applyQuery(q) {
            q = normalize((q || '').trim().toLowerCase());
            featured.forEach(function (item) {
                var matches = isAllowed(item) && (q.length === 0 || itemLabel(item).indexOf(q) !== -1);
                item.classList.toggle('subject-filtered-out', !matches);
            });
            var anyRestVisible = false;
            rest.forEach(function (item) {
                var cb = item.querySelector('input[type=checkbox]');
                // Sin texto tipeado, el resto solo se muestra si hay un
                // filtro externo activo (allowedIds) que ya lo acotó —
                // nunca por default, para no volver a volcar todo.
                var textOk = q.length > 0 ? itemLabel(item).indexOf(q) !== -1 : !!allowedIds;
                var keep = (cb && cb.checked) || (isAllowed(item) && textOk);
                item.classList.toggle('subject-filtered-out', !keep);
                if (keep) anyRestVisible = true;
            });
            return anyRestVisible;
        }

        if (!rest.length) {
            // Todo (o casi todo) es relevante — no hace falta separar nada,
            // solo dejar que el buscador filtre el conjunto entero como
            // siempre lo hizo.
            if (filterInput) filterInput.addEventListener('input', function () { applyQuery(filterInput.value); });
            return {
                setAllowedIds: function (ids) { allowedIds = ids; applyQuery(filterInput ? filterInput.value : ''); },
            };
        }

        var moreWrap = document.createElement('div');
        rest.forEach(function (item) { moreWrap.appendChild(item); });

        var emptyHint = document.createElement('p');
        emptyHint.className = 'text-muted small mb-0 mt-2 subjects-checklist-hint';
        emptyHint.textContent = opts.emptyRestLabel || 'Escribí para buscar entre el resto de las opciones.';

        var toggleBtn = document.createElement('button');
        toggleBtn.type = 'button';
        toggleBtn.className = 'btn btn-link btn-sm p-0 mt-2 subjects-checklist-toggle';
        toggleBtn.textContent = opts.moreLabel || 'Buscar y agregar otra';

        var expanded = false;
        function refresh() {
            var q = filterInput ? filterInput.value : '';
            var anyRestVisible = applyQuery(q);
            // Un filtro externo activo (institución/facultad/carrera) hace
            // el mismo papel que tipear algo: no tiene sentido dejar el
            // resto colapsado si ya se restringió por otro lado.
            var showRestArea = expanded || !!q.trim() || !!allowedIds;
            moreWrap.style.display = showRestArea ? '' : 'none';
            toggleBtn.style.display = (showRestArea || !featured.length) ? 'none' : '';
            emptyHint.style.display = showRestArea && !anyRestVisible ? '' : 'none';
        }

        toggleBtn.addEventListener('click', function () {
            expanded = true;
            refresh();
            if (filterInput) filterInput.focus();
        });
        if (filterInput) filterInput.addEventListener('input', refresh);

        // moreWrap tiene que quedar DENTRO de .subjects-checklist (hermano
        // de itemsWrap) para heredar el grid y el escondido por CSS
        // (.subjects-checklist > div > div.subject-filtered-out) — afuera,
        // esas reglas no aplican y el resto se ve como lista sin estilo y
        // sin esconderse. El botón y el hint sí van afuera, debajo del box.
        checklist.appendChild(moreWrap);
        var afterChecklist = checklist.nextSibling;
        if (featured.length) {
            checklist.parentNode.insertBefore(toggleBtn, afterChecklist);
            checklist.parentNode.insertBefore(emptyHint, afterChecklist);
        } else {
            // No hay nada "propio" todavía (usuario nuevo, o ninguna
            // favorita/con contenido cargado) — no tiene sentido un botón
            // "ver lo propio" vacío: se arranca directo en modo búsqueda.
            itemsWrap.style.display = 'none';
            expanded = true;
            checklist.parentNode.insertBefore(emptyHint, afterChecklist);
        }
        refresh();

        return {
            moreWrap: moreWrap, toggleBtn: toggleBtn, refresh: refresh,
            setAllowedIds: function (ids) { allowedIds = ids; refresh(); },
        };
    }

    return { init: init };
})();
