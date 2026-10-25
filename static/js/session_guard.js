/* Aviso de sesión vencida para los pedidos por fetch (asistentes, guardados por AJAX).
   Si la sesión venció, el servidor redirige al ingreso y fetch devuelve la página de ingreso en vez del
   JSON esperado: los asistentes lo mostraban como "Error de red — reintentar" y no había forma de saber
   que lo que faltaba era ingresar de nuevo. Acá se detecta ese caso y se ofrece ingresar sin perder la
   pantalla (los asistentes guardan su borrador y lo ofrecen recuperar al volver). */
(function () {
  var original = window.fetch;
  if (!original) return;
  var avisado = false;

  function esIngreso(url) {
    try { return new URL(url, window.location.href).pathname.indexOf('/accounts/login') === 0; } catch (e) { return false; }
  }

  function avisar() {
    if (avisado) return;
    avisado = true;
    var destino = '/accounts/login/?next=' + encodeURIComponent(window.location.pathname + window.location.search);
    var texto = 'La sesión venció, así que no se pudo guardar lo último. Ingresar de nuevo para seguir: el trabajo en curso queda para recuperar.';
    if (window.EducaAppModal && window.EducaAppModal.confirm) {
      window.EducaAppModal.confirm(texto, { title: 'Sesión vencida', okLabel: 'Ingresar de nuevo', cancelLabel: 'Quedarme acá' }).then(function (ok) {
        avisado = false;
        if (ok) window.top.location.href = destino;
      });
    } else {
      window.top.location.href = destino;
    }
  }

  window.fetch = function () {
    return original.apply(this, arguments).then(function (respuesta) {
      try {
        if (respuesta.redirected && esIngreso(respuesta.url) && !esIngreso(window.location.href)) avisar();
        else if (respuesta.status === 401) avisar();
      } catch (e) { /* nunca romper el pedido original */ }
      return respuesta;
    });
  };
})();
