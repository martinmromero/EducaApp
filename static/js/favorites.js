/*
 * Botón de favorito reutilizable (exámenes, plantillas, materias).
 * Requiere un botón con clase "favorite-star", data-model, data-id y
 * data-active ("1"/"0"), y el token CSRF en el DOM (Django lo agrega
 * automáticamente en cualquier <form> con {% csrf_token %}; si la página
 * no tiene ningún form, se lee de la cookie).
 */
(function () {
  function getCookie(name) {
    const match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
    return match ? decodeURIComponent(match[2]) : null;
  }

  function getCsrfToken() {
    const input = document.querySelector('input[name="csrfmiddlewaretoken"]');
    return input ? input.value : getCookie('csrftoken');
  }

  function renderStar(btn, isActive) {
    btn.dataset.active = isActive ? '1' : '0';
    btn.innerHTML = isActive ? '<i class="fas fa-star"></i>' : '<i class="far fa-star"></i>';
    btn.classList.toggle('text-warning', isActive);
    btn.title = isActive ? 'Quitar de favoritos' : 'Agregar a favoritos';
  }

  function onClick(e) {
    const btn = e.currentTarget;
    btn.disabled = true;
    fetch('/favoritos/toggle/', {
      method: 'POST',
      headers: {
        'X-CSRFToken': getCsrfToken(),
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: 'model=' + encodeURIComponent(btn.dataset.model) + '&object_id=' + encodeURIComponent(btn.dataset.id),
    })
      .then((r) => r.json())
      .then((data) => {
        renderStar(btn, data.is_favorite);
        document.dispatchEvent(new CustomEvent('favoriteToggled', { detail: { btn: btn, isFavorite: data.is_favorite } }));
      })
      .finally(() => { btn.disabled = false; });
  }

  function init() {
    document.querySelectorAll('.favorite-star').forEach(function (btn) {
      renderStar(btn, btn.dataset.active === '1');
      btn.addEventListener('click', onClick);
    });
  }

  // Expuesto para volver a inicializar botones agregados dinámicamente
  // después de la carga inicial (ver subjects/list.html, filtro en vivo).
  window.EducaAppFavorites = { init: init };

  document.addEventListener('DOMContentLoaded', init);
})();
