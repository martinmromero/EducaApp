/*
 * Service worker de EducaApp — mínimo, a propósito.
 *
 * Objetivo real: que el navegador considere la app "instalable" (ícono en
 * el inicio del celular, splash screen, abre sin la barra de direcciones).
 * No promete uso offline de verdad: EducaApp es una app Django clásica
 * (cada página se renderiza en el servidor con sesión + CSRF), así que solo
 * cachea estáticos same-origin bajo /static/ (CSS/JS/íconos) — nunca HTML
 * de páginas ni pedidos cross-origin a CDNs (Bootstrap, Font Awesome, etc.
 * quedan afuera para no pelear con CORS ni con el opaque-response caching).
 *
 * Se sirve desde /sw.js (no desde /static/sw.js) para que el scope por
 * default cubra todo el sitio — ver material/views.py:service_worker.
 */
// v1 servía "cache primero, red en segundo plano" (cache.match ||
// networkFetch): en cualquier visita con algo ya cacheado, esa visita
// SIEMPRE mostraba la versión vieja, y recién actualizaba el cache para la
// visita siguiente — con cada deploy, cualquier navegador que ya hubiera
// visitado el sitio quedaba mostrando JS/CSS de un deploy atrás como
// mínimo, indefinidamente. Como este service worker nunca promete uso
// offline real (ver comentario de arriba), no hay motivo para preferir el
// cache: v2 pasa a "red primero, cache solo como respaldo si falla la red".
const CACHE_NAME = 'educaapp-static-v2';

self.addEventListener('install', () => {
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;

  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;
  if (!url.pathname.startsWith('/static/')) return;

  event.respondWith(
    fetch(req)
      .then((resp) => {
        if (resp && resp.status === 200) {
          const copy = resp.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(req, copy));
        }
        return resp;
      })
      .catch(() => caches.open(CACHE_NAME).then((cache) => cache.match(req)))
  );
});
