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
})();
