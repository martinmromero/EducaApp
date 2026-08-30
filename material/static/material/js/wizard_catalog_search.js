// wizard_catalog_search.js — Buscador con autocompletado contra el catálogo
// (institución/facultad/carrera/materia — mismo motor que Solicitar Alta:
// check_catalog_duplicate) para usar dentro de cualquier asistente paso a
// paso. Extraído de create_exam_wizard.js el día que se armó el segundo
// wizard (Cuestionario Oral, que no lo necesita hoy pero deja esto listo
// para Plantilla de Examen / Institución más adelante).
//
// Espera que la página ya haya definido window.EducaAppWizardConfig.urls
// con al menos checkCatalogDuplicate (y opcionalmente
// catalogRequestCreateBase) — misma convención que ya usa create_exam_wizard.html.
window.EducaAppWizardCatalogSearch = (function () {
    function debounce(fn, wait) {
        var t;
        return function () {
            var args = arguments;
            clearTimeout(t);
            t = setTimeout(function () { fn.apply(null, args); }, wait);
        };
    }

    function badgeFor(item) {
        return item.es_catalogo_institucional === false ? 'Personal' : 'Catálogo';
    }

    /**
     * Cablea un buscador de catálogo. Devuelve un objeto con setValue(id, name)
     * para prefill programático.
     * opts: { searchInput, suggestBox, hiddenInput, nivel, getScopeParams, requiresScope, onClear }
     */
    function wireCatalogSearch(opts) {
        var CFG = window.EducaAppWizardConfig || { urls: {} };
        var lastPickedName = '';

        function hideSuggest() {
            opts.suggestBox.classList.add('d-none');
            opts.suggestBox.innerHTML = '';
        }

        function pick(item) {
            opts.hiddenInput.value = String(item.id);
            opts.searchInput.value = item.name;
            lastPickedName = item.name;
            hideSuggest();
            opts.hiddenInput.dispatchEvent(new Event('change'));
        }

        function renderResults(items) {
            opts.suggestBox.innerHTML = '';
            if (!items.length) {
                var empty = document.createElement('div');
                empty.className = 'wiz-catalog-suggest-empty';
                empty.textContent = 'Sin coincidencias — se usa el texto tipeado tal cual. ';
                // No se crea catálogo desde acá (eso queda para Solicitar
                // Alta, con su flujo de aprobación) — solo se enlaza. Abre
                // en pestaña nueva para no perder lo que se esté armando.
                if (opts.nivel && CFG.urls.catalogRequestCreateBase) {
                    var link = document.createElement('a');
                    link.href = CFG.urls.catalogRequestCreateBase + '?tipo=' + encodeURIComponent(opts.nivel);
                    link.target = '_blank';
                    link.rel = 'noopener';
                    link.textContent = 'Solicitar alta al catálogo';
                    empty.appendChild(link);
                }
                opts.suggestBox.appendChild(empty);
            } else {
                items.forEach(function (item) {
                    var row = document.createElement('div');
                    row.className = 'wiz-catalog-suggest-item';
                    var name = document.createElement('span');
                    name.textContent = item.name;
                    var badge = document.createElement('span');
                    badge.className = 'badge bg-secondary-subtle text-secondary-emphasis wiz-catalog-suggest-badge';
                    badge.textContent = badgeFor(item);
                    row.appendChild(name);
                    row.appendChild(badge);
                    row.addEventListener('mousedown', function (e) {
                        e.preventDefault(); // evita perder el foco antes del click
                        pick(item);
                    });
                    opts.suggestBox.appendChild(row);
                });
            }
            opts.suggestBox.classList.remove('d-none');
        }

        var search = debounce(function (q) {
            var scope = (opts.getScopeParams && opts.getScopeParams()) || {};
            if (opts.requiresScope && Object.keys(scope).length === 0) {
                hideSuggest();
                return;
            }
            var params = new URLSearchParams(Object.assign({ nivel: opts.nivel, q: q }, scope));
            fetch(CFG.urls.checkCatalogDuplicate + '?' + params.toString())
                .then(function (r) { return r.json(); })
                .then(renderResults)
                .catch(function () { hideSuggest(); });
        }, 250);

        opts.searchInput.addEventListener('input', function () {
            var q = this.value.trim();
            // Cualquier tipeo invalida la elección previa hasta que se
            // confirme una nueva (con click o dejando el texto libre al salir).
            if (opts.hiddenInput.value && this.value !== lastPickedName) {
                opts.hiddenInput.value = '';
                if (opts.onClear) opts.onClear();
            }
            if (q.length < 2) { hideSuggest(); return; }
            search(q);
        });

        opts.searchInput.addEventListener('blur', function () {
            // Un pequeño delay para que el mousedown de una sugerencia
            // llegue a dispararse antes de que el blur la oculte.
            setTimeout(function () {
                hideSuggest();
                var typed = opts.searchInput.value.trim();
                if (!opts.hiddenInput.value && typed) {
                    // No se eligió ninguna sugerencia: se usa el texto tal
                    // cual (ver _resolve_name en views.py, que ya acepta
                    // cualquier string que no sea un ID numérico).
                    opts.hiddenInput.value = typed;
                    opts.hiddenInput.dispatchEvent(new Event('change'));
                }
            }, 150);
        });

        return {
            setValue: function (id, name) {
                opts.hiddenInput.value = String(id);
                opts.searchInput.value = name;
                lastPickedName = name;
            },
        };
    }

    function clearCatalogField(searchInput, hiddenInput) {
        searchInput.value = '';
        hiddenInput.value = '';
    }

    return {
        debounce: debounce,
        badgeFor: badgeFor,
        wireCatalogSearch: wireCatalogSearch,
        clearCatalogField: clearCatalogField,
    };
})();
