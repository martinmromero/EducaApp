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
        // Para un asistente embebido en otro (Asistente paso a paso): "Atrás" en
        // el primer paso no desaparece, sale hacia el host (onBackFromFirst).
        var keepBackOnFirst = !!config.keepBackOnFirst;
        var onBackFromFirst = config.onBackFromFirst || function () {};
        // Primer paso que se ve (puede no ser el 1: un asistente embebido salta los que
        // ya vienen resueltos del host). "Atrás" ahí sale hacia el host, no a un paso oculto.
        var firstVisibleStep = config.firstVisibleStep || function () { return 1; };
        // Se llama con el número de paso cada vez que se muestra uno (el asistente
        // embebido se lo cuenta al host, que muestra "Paso X de N").
        var onStep = config.onStep || function () {};
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
            if (backBtn) backBtn.classList.toggle('d-none', n === 1 && !keepBackOnFirst);
            if (nextBtn) nextBtn.classList.toggle('d-none', n === totalSteps);
            if (submitBtn) submitBtn.classList.toggle('d-none', n !== totalSteps);
            currentStep = n;
            onStep(n);
            if (n === totalSteps) onEnterFinalStep();
        }

        // Un solo criterio de posición para todos los asistentes: al pasar de un paso a otro (Siguiente, Atrás o
        // tocar un paso del indicador) el indicador de pasos queda arriba de la pantalla, siempre en el mismo
        // lugar. Al abrir el asistente no se mueve nada (sin esto cada paso, y cada asistente, quedaba en un lugar
        // distinto: offsetTop es relativo al contenedor, no a la página, y el asistente completo oculta su
        // introducción justo después de mostrar el paso, lo que corría todo). El desplazamiento se hace en el
        // turno siguiente, cuando ya terminaron de acomodarse los otros listeners; en el celular se deja lugar
        // para el botón flotante del menú.
        function scrollToStepper() {
            if (!stepperEl) return;
            setTimeout(function () {
                var movil = window.innerWidth <= 767;
                var rect = stepperEl.getBoundingClientRect();
                // En pantalla ancha, si el indicador ya se ve entero no hace falta mover nada.
                if (!movil && rect.top >= 0) return;
                var top = rect.top + window.pageYOffset - (movil ? 64 : 16);
                window.scrollTo({ top: Math.max(0, top), behavior: 'smooth' });
            }, 0);
        }

        function goNext() {
            if (!onValidateStep(currentStep)) return;
            var next = Math.min(currentStep + 1, totalSteps);
            maxStepReached = Math.max(maxStepReached, next);
            showStep(next);
            scrollToStepper();
        }
        function goBack() {
            if (keepBackOnFirst && currentStep <= firstVisibleStep()) { onBackFromFirst(); return; }
            showStep(Math.max(currentStep - 1, 1));
            scrollToStepper();
        }
        function goToStep(n) {
            if (n <= maxStepReached) showStep(n);
        }

        if (nextBtn) nextBtn.addEventListener('click', goNext);
        if (backBtn) backBtn.addEventListener('click', goBack);
        document.querySelectorAll('.wiz-step-pill').forEach(function (pill) {
            pill.addEventListener('click', function () {
                var destino = parseInt(pill.dataset.stepPill, 10);
                if (destino <= maxStepReached && destino !== currentStep) scrollToStepper();
                goToStep(destino);
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
