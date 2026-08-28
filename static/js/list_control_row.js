/*
 * Selección contextual para la fila de control de listados (ver
 * mis_examenes_new.html como implementación de referencia, y
 * static/css/styles.css para las clases .list-control-row / .list-toolbar-btn
 * / .list-filter-badge que la acompañan).
 *
 * Convención que debe respetar la página que lo usa:
 * - Un formulario con los checkboxes de selección (id configurable, default
 *   "deleteForm").
 * - #listControlDefault: contenedor con los accesos normales (Filtros,
 *   Favoritos) — se oculta mientras hay algo seleccionado.
 * - #listSelectionBar: contenedor con la cantidad seleccionada y las
 *   acciones (Eliminar, Cancelar) — se muestra mientras hay algo
 *   seleccionado, oculto el resto del tiempo.
 * - #listSelectionCount: texto de "N seleccionados", lo completa este script.
 * - #selectAll (opcional): checkbox de "seleccionar todo".
 * - #listSelectionCancelBtn (opcional): limpia la selección.
 *
 * Uso: initListControlSelection({ checkboxName: 'item_ids' }).
 */
function initListControlSelection(options) {
    options = options || {};
    const form = document.getElementById(options.formId || 'deleteForm');
    const defaultBar = document.getElementById('listControlDefault');
    const selectionBar = document.getElementById('listSelectionBar');
    const countEl = document.getElementById('listSelectionCount');
    if (!form || !defaultBar || !selectionBar || !countEl || !options.checkboxName) return null;

    const checkboxSelector = 'input[type="checkbox"][name="' + options.checkboxName + '"]';

    function update() {
        const checked = form.querySelectorAll(checkboxSelector + ':checked');
        if (checked.length > 0) {
            defaultBar.classList.add('d-none');
            defaultBar.classList.remove('d-flex');
            selectionBar.classList.remove('d-none');
            selectionBar.classList.add('d-flex');
            countEl.textContent = checked.length + (checked.length === 1 ? ' seleccionado' : ' seleccionados');
        } else {
            defaultBar.classList.remove('d-none');
            defaultBar.classList.add('d-flex');
            selectionBar.classList.add('d-none');
            selectionBar.classList.remove('d-flex');
        }
    }

    // Delegado en el form (no en cada checkbox): así sigue funcionando si
    // las filas se reemplazan dinámicamente (ver subjects/list.html, filtro
    // de texto en vivo) sin tener que volver a llamar a esta función.
    form.addEventListener('change', function (e) {
        if (e.target.matches(checkboxSelector)) update();
    });

    const selectAll = document.getElementById('selectAll');
    if (selectAll) {
        selectAll.addEventListener('change', function () {
            form.querySelectorAll(checkboxSelector).forEach(function (cb) { cb.checked = selectAll.checked; });
            update();
        });
    }

    const cancelBtn = document.getElementById('listSelectionCancelBtn');
    if (cancelBtn) {
        cancelBtn.addEventListener('click', function () {
            form.querySelectorAll(checkboxSelector).forEach(function (cb) { cb.checked = false; });
            if (selectAll) selectAll.checked = false;
            update();
        });
    }

    return update;
}
