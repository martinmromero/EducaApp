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
const CACHE_NAME = 'educaapp-static-v1';

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
    caches.open(CACHE_NAME).then((cache) =>
      cache.match(req).then((cached) => {
        const networkFetch = fetch(req)
          .then((resp) => {
            if (resp && resp.status === 200) cache.put(req, resp.clone());
            return resp;
          })
          .catch(() => cached);
        return cached || networkFetch;
      })
    )
  );
});
