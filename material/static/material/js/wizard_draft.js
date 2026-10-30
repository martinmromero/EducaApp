// wizard_draft.js — Backup a sessionStorage del progreso de un wizard, con
// oferta de recuperación si se recarga la pantalla. Cubre 3 escenarios
// reales encontrados hoy en distintos wizards: F5 accidental, cierre de
// pestaña, y volver de crear algo relacionado en una pestaña nueva (ej.
// una rúbrica) sin encontrar cómo seguir — antes cualquiera de los tres
// perdía TODO el progreso, sin ningún respaldo.
//
// Este módulo solo sabe guardar/cargar/borrar un blob de estado y ofrecer
// el diálogo de "¿recuperar?" — la SECUENCIA real de restauración (qué
// campo depende de qué fetch en cascada, en qué orden) sigue siendo
// responsabilidad de cada wizard, porque difiere demasiado entre uno y
// otro como para generalizarla acá sin volverla más frágil.
//
// Uso:
//   var draft = window.EducaAppWizardDraft.init('educaapp_oral_wizard_draft');
//   form.addEventListener('change', function () { draft.save(collectState()); });
//   form.addEventListener('input', function () { draft.save(collectState()); });
//   ...
//   var saved = draft.load();
//   if (saved) {
//       draft.confirmRestore('Encontramos un cuestionario oral sin terminar de una sesión anterior. ¿Querés recuperarlo?')
//           .then(function (yes) { if (yes) { /* restaurar campos desde saved */ } else { draft.clear(); } });
//   }
//   // al guardar con éxito:
//   draft.clear();
//
// Gotcha real encontrado usando esto en Plantilla de Examen: si la
// restauración llega hasta el último paso, NO alcanza con
// wizardCtrl.goToStep(n) — wizard_engine.js solo deja saltar a un paso
// <= maxStepReached, que sigue en 1 si nunca se pasó por goNext() en esta
// carga de página. Hay que "caminar" los pasos con goNext() (los datos ya
// restaurados hacen que onValidateStep pase limpio en cada uno), no saltar
// directo.
window.EducaAppWizardDraft = (function () {
    // El borrador vive en sessionStorage, que es del navegador y no de la cuenta:
    // en un equipo compartido, otra persona que ingresara en la misma pestaña
    // veía ofrecido el trabajo de la anterior. La clave lleva el id de la cuenta
    // (base.html lo publica en window.EducaAppUserId).
    function scopedKey(key) {
        var uid = window.EducaAppUserId;
        return uid ? key + ':u' + uid : key;
    }
    // opts.persist: el borrador sobrevive al cierre del navegador (localStorage,
    // con vencimiento de 7 días) en vez de vivir solo en la pestaña
    // (sessionStorage). Es el "retomar mañana" del Asistente paso a paso; los demás
    // asistentes siguen con el borrador de pestaña.
    var DIAS_MS = 7 * 24 * 60 * 60 * 1000;
    function init(baseKey, opts) {
        var key = scopedKey(baseKey);
        var persist = !!(opts && opts.persist);
        function store() { return persist ? window.localStorage : window.sessionStorage; }
        function save(state) {
            try { store().setItem(key, JSON.stringify(persist ? { t: Date.now(), s: state } : state)); } catch (e) { /* almacenamiento lleno o bloqueado (navegación privada) — best-effort */ }
        }
        function load() {
            var raw;
            try { raw = store().getItem(key); } catch (e) { return null; }
            if (!raw) return null;
            try {
                var parsed = JSON.parse(raw);
                if (!persist) return parsed;
                if (!parsed || typeof parsed.t !== 'number' || (Date.now() - parsed.t) > DIAS_MS) { clear(); return null; }
                return parsed.s;
            } catch (e) { clear(); return null; }
        }
        function clear() {
            try { store().removeItem(key); } catch (e) { /* ver save */ }
        }
        function confirmRestore(message) {
            if (!window.EducaAppModal) return Promise.resolve(false);
            return window.EducaAppModal.confirm(message, {
                title: 'Trabajo sin guardar',
                variant: 'info',
                okLabel: 'Recuperar',
                cancelLabel: 'Descartar',
            });
        }
        return { save: save, load: load, clear: clear, confirmRestore: confirmRestore };
    }
    return { init: init, scopedKey: scopedKey };
})();
