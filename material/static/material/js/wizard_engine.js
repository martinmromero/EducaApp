// wizard_engine.js — Motor genérico de navegación para los asistentes paso
// a paso (Crear Examen, Cuestionario Oral, y los que se sumen). No conoce
// nada de ningún dominio puntual — cada wizard le pasa su propia validación
// por paso y su propio render de resumen.
//
// Convención de ids/clases compartida por TODOS los templates de wizard
// (ver wizard_common.css): #wizStepper con .wiz-step-pill[data-step-pill]
// adentro, un .wiz-step[data-step] por paso, #wizBackBtn, #wizNextBtn,
// #wizSubmitBtn.
//
// Uso:
//   var wiz = window.EducaAppWizard.init({
//       totalSteps: 3,
//       onValidateStep: function (n) { ... return true/false ... },
//       onEnterFinalStep: function () { ... renderSummary() ... },
//   });
//   // al final de todo el setup propio del wizard:
//   wiz.goToStep(1);
window.EducaAppWizard = (function () {
    function init(config) {
        var totalSteps = config.totalSteps;
        var onValidateStep = config.onValidateStep || function () { return true; };
        var onEnterFinalStep = config.onEnterFinalStep || function () {};
        var currentStep = 1;
        var maxStepReached = 1;

        var backBtn = document.getElementById('wizBackBtn');
        var nextBtn = document.getElementById('wizNextBtn');
        var submitBtn = document.getElementById('wizSubmitBtn');
        var stepperEl = document.getElementById('wizStepper');

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
            if (backBtn) backBtn.classList.toggle('d-none', n === 1);
            if (nextBtn) nextBtn.classList.toggle('d-none', n === totalSteps);
            if (submitBtn) submitBtn.classList.toggle('d-none', n !== totalSteps);
            currentStep = n;
            if (n === totalSteps) onEnterFinalStep();
            if (stepperEl) window.scrollTo({ top: stepperEl.offsetTop - 20, behavior: 'smooth' });
        }

        function goNext() {
            if (!onValidateStep(currentStep)) return;
            var next = Math.min(currentStep + 1, totalSteps);
            maxStepReached = Math.max(maxStepReached, next);
            showStep(next);
        }
        function goBack() {
            showStep(Math.max(currentStep - 1, 1));
        }
        function goToStep(n) {
            if (n <= maxStepReached) showStep(n);
        }

        if (nextBtn) nextBtn.addEventListener('click', goNext);
        if (backBtn) backBtn.addEventListener('click', goBack);
        document.querySelectorAll('.wiz-step-pill').forEach(function (pill) {
            pill.addEventListener('click', function () {
                goToStep(parseInt(pill.dataset.stepPill, 10));
            });
        });

        return {
            goNext: goNext,
            goBack: goBack,
            goToStep: goToStep,
            current: function () { return currentStep; },
        };
    }

    return { init: init };
})();
