/*
 * Escape de HTML compartido: window.EducaAppEscape(valor) devuelve el texto
 * listo para interpolar dentro de un innerHTML / insertAdjacentHTML, tanto
 * en contenido de elemento como en valores de atributo entre comillas.
 *
 * Cargado desde el <head> de base.html, así que está disponible para
 * cualquier script de página, incluidos los que corren mientras se parsea
 * el contenido.
 *
 * Regla: todo dato que no sea una constante del propio script (texto de una
 * pregunta o de una opción, nombres de materias/tópicos/instituciones,
 * descripciones de resultados de aprendizaje, mensajes que vuelven del
 * servidor, etc.) tiene que pasar por acá antes de entrar a un innerHTML —
 * ese contenido lo puede escribir otro docente y llegar compartido por un
 * grupo de confianza. Si no hace falta HTML, mejor textContent.
 */
(function () {
  'use strict';
  var MAP = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };

  window.EducaAppEscape = function (value) {
    if (value === null || value === undefined) return '';
    return String(value).replace(/[&<>"']/g, function (ch) { return MAP[ch]; });
  };
})();
