/* Descargas de archivos que el servidor arma al momento (PDF/DOCX de exámenes y lotes): mientras se
   prepara, el botón muestra "Preparando…" y no admite otro clic. Antes no había ningún aviso y, como
   la primera descarga tarda, se volvía a tocar el botón y se pedía el mismo archivo varias veces.
   La descarga la hace el propio navegador (un marco oculto, con el gesto del toque intacto: funciona también
   en el celular y dentro del asistente). El servidor deja una cookie descarga_<token> cuando el archivo sale;
   si en cambio responde una página (error, sesión vencida) el marco la carga y se avisa.
   Uso: EducaAppDescargar(url, boton), o un enlace con href que contenga /exportar/ (se engancha solo). */
(function () {
  var ocupado = false;
  var ESPERA_MAX_MS = 120000;

  function aviso(texto) {
    if (window.EducaAppModal && window.EducaAppModal.alert) {
      window.EducaAppModal.alert(texto, { title: 'No se pudo descargar', variant: 'warning' });
    } else {
      window.alert(texto);
    }
  }

  function cookie(nombre) {
    return document.cookie.split('; ').some(function (c) { return c.indexOf(nombre + '=') === 0; });
  }

  window.EducaAppDescargar = function (url, boton) {
    if (ocupado) return;
    ocupado = true;
    var token = Math.random().toString(36).slice(2, 12) + Date.now().toString(36);
    var nombreCookie = 'descarga_' + token;
    var html = null;
    if (boton) {
      html = boton.innerHTML;
      boton.dataset.descargaBloqueado = '1';
      boton.setAttribute('aria-busy', 'true');
      boton.classList.add('disabled');
      boton.innerHTML = '<span class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span>Preparando…';
    }
    var marco = document.createElement('iframe');
    marco.style.display = 'none';
    marco.setAttribute('aria-hidden', 'true');
    var inicio = Date.now();
    var terminado = false;
    var reloj = null;

    function liberar() {
      if (terminado) return;
      terminado = true;
      clearInterval(reloj);
      ocupado = false;
      document.cookie = nombreCookie + '=; Max-Age=0; path=/';
      setTimeout(function () { if (marco.parentNode) marco.parentNode.removeChild(marco); }, 2000);
      if (boton) {
        boton.innerHTML = html;
        boton.classList.remove('disabled');
        boton.removeAttribute('aria-busy');
        delete boton.dataset.descargaBloqueado;
      }
    }

    // Una descarga real no dispara "load" en el marco; si lo dispara, el servidor devolvió una página.
    marco.addEventListener('load', function () {
      if (terminado || cookie(nombreCookie)) return;
      liberar();
      aviso('No se pudo preparar el archivo. Probar de nuevo en unos segundos; si sigue pasando, avisar.');
    });
    reloj = setInterval(function () {
      if (cookie(nombreCookie)) {
        // El archivo ya salió: el navegador lo está guardando.
        setTimeout(liberar, 600);
        clearInterval(reloj);
      } else if (Date.now() - inicio > ESPERA_MAX_MS) {
        liberar();
        aviso('El archivo tarda demasiado en prepararse. Probar de nuevo en unos minutos.');
      }
    }, 300);

    var sep = url.indexOf('?') === -1 ? '?' : '&';
    marco.src = url + sep + 'descarga_token=' + token;
    document.body.appendChild(marco);
  };

  document.addEventListener('click', function (e) {
    var enlace = e.target.closest && e.target.closest('a[href*="/exportar/"]');
    if (!enlace || e.defaultPrevented || e.button !== 0 || e.ctrlKey || e.metaKey || e.shiftKey) return;
    e.preventDefault();
    if (enlace.dataset.descargaBloqueado) return;
    window.EducaAppDescargar(enlace.getAttribute('href'), enlace);
  });
})();
