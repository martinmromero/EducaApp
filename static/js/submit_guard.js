/* Evita el envío doble de formularios POST: un segundo clic mientras el servidor
   todavía responde (Render lento al arrancar) creaba el mismo registro varias veces.
   Escucha en document, o sea después de los manejadores propios de cada formulario:
   si alguno canceló el envío (validación, confirmación, guardado por AJAX) no se traba nada. */
(function () {
  var ESPERA_MAX_MS = 15000; // un POST que descarga un archivo no navega: el botón se libera solo

  function botones(form) {
    return form.querySelectorAll('button[type="submit"], button:not([type]), input[type="submit"]');
  }

  function liberar(form) {
    delete form.dataset.enviando;
    botones(form).forEach(function (b) {
      if (b.dataset.guardaPrevio !== undefined) {
        b.disabled = false;
        delete b.dataset.guardaPrevio;
      }
    });
  }

  document.addEventListener('submit', function (e) {
    var form = e.target;
    if (!form || !form.tagName || form.tagName !== 'FORM') return;
    if ((form.method || '').toLowerCase() !== 'post') return;
    if (form.hasAttribute('data-permitir-reenvio')) return;
    if (form.dataset.enviando) {
      e.preventDefault();
      return;
    }
    if (e.defaultPrevented) return;
    form.dataset.enviando = '1';
    // Deshabilitar en el mismo turno quitaría el name/value del botón que envía.
    setTimeout(function () {
      botones(form).forEach(function (b) {
        if (!b.disabled) {
          b.dataset.guardaPrevio = '1';
          b.disabled = true;
        }
      });
    }, 0);
    setTimeout(function () { liberar(form); }, ESPERA_MAX_MS);
  });

  // Volver con "atrás" desde el caché del navegador deja el formulario como estaba.
  window.addEventListener('pageshow', function (e) {
    if (!e.persisted) return;
    document.querySelectorAll('form[data-enviando]').forEach(liberar);
  });
})();
