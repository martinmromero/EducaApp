/* embed.js — Pantallas de EducaApp que se muestran dentro de un <iframe> de
   otra pantalla (hoy: el paso Examen del Asistente completo, que monta el
   asistente de examen y su vista previa en un <iframe name="educaapp-embed-exam">).

   Contrato: el <iframe> se llama "educaapp-embed-<algo>". Dentro, esta
   pantalla (a) se pinta sin el menú lateral ni la barra superior (clase
   html.embed-mode, ver styles.css) y (b) le avisa al host con postMessage
   — mismo origen — vía EducaAppEmbed.notify(tipo, datos). Fuera de un
   <iframe> así nombrado no hace nada, así que cualquier pantalla puede
   llamarlo sin chequear nada. */
(function () {
    var embedded = false;
    try {
        embedded = window.self !== window.top && /^educaapp-embed/.test(window.name || '');
    } catch (e) { /* acceso cruzado bloqueado: no es nuestro host */ }
    if (embedded) document.documentElement.classList.add('embed-mode');
    window.EducaAppEmbed = {
        isEmbedded: embedded,
        notify: function (type, payload) {
            if (!embedded) return false;
            window.parent.postMessage(Object.assign({ type: type }, payload || {}), window.location.origin);
            return true;
        },
    };
    // Enlaces "Empezar de nuevo" / "Salir" de la barra inferior de un asistente embebido:
    // no navegan solos (saldrían del <iframe>), le piden al host que lo haga.
    if (embedded) {
        document.addEventListener('click', function (e) {
            var link = e.target.closest ? e.target.closest('[data-fw-action]') : null;
            if (!link) return;
            e.preventDefault();
            window.EducaAppEmbed.notify('educaapp:fw-' + link.getAttribute('data-fw-action'));
        });
    }
    // Toda pantalla propia que cargue este script avisa que "llegó". Si el
    // host no recibe este aviso tras cargar el <iframe>, sabe que lo que se
    // ve es otra cosa (una pantalla que no se puede enmarcar, el login por
    // sesión vencida, un error del servidor) y ofrece una salida en vez de
    // dejar un recuadro en blanco.
    if (embedded) {
        // Una pantalla que se arma sola al cargar (precarga, borrador) lo declara con
        // data-embed-defer-ready en el <body>: el host la mantiene oculta, con un
        // aviso de "preparando", hasta que ella misma manda 'educaapp:content-ready'.
        // Sin eso el usuario veía cómo se iban llenando los pasos uno por uno.
        var announce = function () {
            var deferred = !!(document.body && document.body.hasAttribute('data-embed-defer-ready'));
            window.EducaAppEmbed.notify('educaapp:embed-ready', { deferred: deferred });
        };
        if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', announce);
        else announce();
    }
})();
