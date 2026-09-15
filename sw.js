/**
 * Playmaker Service Worker (sw.js)
 * Caching strategy:
 *  - Network-First with cache fallback for HTML navigation and dynamic puzzle data
 *  - Cache-First with network fallback for static assets (images, fonts, stylesheets, scripts)
 */

const CACHE_NAME = 'playmaker-v1';
const PRECACHE_ASSETS = [
  './',
  './index.html',
  './manifest.json',
  './favicon.ico',
  './assets/favicon.png',
  './assets/favicon-192.png',
  './games/footy-ui.css',
  './games/footy-ui.js'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(PRECACHE_ASSETS).catch((err) => {
        console.warn('[SW] Pre-caching partial failure:', err);
      });
    }).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((name) => {
          if (name !== CACHE_NAME) {
            return caches.delete(name);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const request = event.request;
  
  // Ignore non-GET or chrome-extension / non-http requests
  if (request.method !== 'GET' || !request.url.startsWith('http')) {
    return;
  }

  const url = new URL(request.url);

  // Network-First for HTML pages and dynamic JSON/CSV data
  const isHtmlOrData = request.mode === 'navigate' || 
                       request.destination === 'document' ||
                       url.pathname.endsWith('.html') || 
                       url.pathname.endsWith('.json') || 
                       url.pathname.endsWith('.csv');

  if (isHtmlOrData) {
    event.respondWith(
      fetch(request)
        .then((response) => {
          if (response && response.status === 200) {
            const responseClone = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(request, responseClone));
          }
          return response;
        })
        .catch(() => caches.match(request).then((cached) => cached || caches.match('./index.html')))
    );
    return;
  }

  // Cache-First for static assets (images, CSS, JS, fonts)
  event.respondWith(
    caches.match(request).then((cachedResponse) => {
      if (cachedResponse) {
        // Fetch in background to revalidate cache
        fetch(request).then((networkResponse) => {
          if (networkResponse && networkResponse.status === 200) {
            caches.open(CACHE_NAME).then((cache) => cache.put(request, networkResponse));
          }
        }).catch(() => {});
        return cachedResponse;
      }

      return fetch(request).then((networkResponse) => {
        if (networkResponse && networkResponse.status === 200) {
          const responseClone = networkResponse.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(request, responseClone));
        }
        return networkResponse;
      });
    })
  );
});
