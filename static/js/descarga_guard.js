/* Descargas de archivos que el servidor arma al momento (PDF/DOCX de exámenes y lotes): mientras se
   prepara, el botón muestra "Preparando…" y no admite otro clic. Antes no había ningún aviso y, como
   la primera descarga tarda, se volvía a tocar el botón y se pedía el mismo archivo varias veces.
   Se baja con fetch y se entrega como archivo; si algo falla, se avisa en pantalla.
   Uso: EducaAppDescargar(url, boton), o un enlace con href que contenga /exportar/ (se engancha solo). */
(function () {
  var ocupado = false;

  function nombreDe(respuesta, url) {
    var cd = respuesta.headers.get('Content-Disposition') || '';
    var m = /filename\*=UTF-8''([^;]+)/i.exec(cd) || /filename="?([^";]+)"?/i.exec(cd);
    if (m) {
      try { return decodeURIComponent(m[1]); } catch (e) { return m[1]; }
    }
    return decodeURIComponent(new URL(url, window.location.href).pathname.split('/').filter(Boolean).pop() || 'archivo');
  }

  function aviso(texto) {
    if (window.EducaAppModal && window.EducaAppModal.alert) {
      window.EducaAppModal.alert(texto, { title: 'No se pudo descargar', variant: 'warning' });
    } else {
      window.alert(texto);
    }
  }

  window.EducaAppDescargar = function (url, boton) {
    if (ocupado) return Promise.resolve(false);
    ocupado = true;
    var html = null;
    if (boton) {
      html = boton.innerHTML;
      boton.dataset.descargaBloqueado = '1';
      boton.setAttribute('aria-busy', 'true');
      boton.classList.add('disabled');
      boton.innerHTML = '<span class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span>Preparando…';
    }
    function liberar() {
      ocupado = false;
      if (boton) {
        boton.innerHTML = html;
        boton.classList.remove('disabled');
        boton.removeAttribute('aria-busy');
        delete boton.dataset.descargaBloqueado;
      }
    }
    return fetch(url, { credentials: 'same-origin' }).then(function (r) {
      var tipo = (r.headers.get('Content-Type') || '').toLowerCase();
      var esArchivo = r.ok && tipo.indexOf('text/html') === -1;
      if (!esArchivo) throw new Error('El servidor no devolvió el archivo (código ' + r.status + ').');
      return r.blob().then(function (blob) {
        var enlace = document.createElement('a');
        var objeto = URL.createObjectURL(blob);
        enlace.href = objeto;
        enlace.download = nombreDe(r, url);
        document.body.appendChild(enlace);
        enlace.click();
        document.body.removeChild(enlace);
        setTimeout(function () { URL.revokeObjectURL(objeto); }, 30000);
        return true;
      });
    }).catch(function (e) {
      aviso('No se pudo preparar el archivo. Probar de nuevo en unos segundos; si sigue pasando, avisar. (' + e.message + ')');
      return false;
    }).then(function (ok) {
      liberar();
      return ok;
    });
  };

  document.addEventListener('click', function (e) {
    var enlace = e.target.closest && e.target.closest('a[href*="/exportar/"]');
    if (!enlace || e.defaultPrevented || e.button !== 0 || e.ctrlKey || e.metaKey || e.shiftKey) return;
    e.preventDefault();
    if (enlace.dataset.descargaBloqueado) return;
    window.EducaAppDescargar(enlace.getAttribute('href'), enlace);
  });
})();
