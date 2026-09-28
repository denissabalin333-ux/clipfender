const CACHE = 'clipfender-shell-v3';
const PRECACHE = ['/offline.html', '/favicon.svg', '/favicon.ico', '/favicon-32x32.png', '/apple-touch-icon.png', '/manifest.webmanifest'];
self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(PRECACHE)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', event => event.waitUntil(self.clients.claim()));
self.addEventListener('fetch', event => {
  const request = event.request;
  if (request.method !== 'GET' || !request.url.startsWith(self.location.origin)) return;
  const url = new URL(request.url);
  if (url.pathname.startsWith('/api/')) return;
  if (url.pathname.startsWith('/static/')) {
    event.respondWith(caches.match(request).then(cached => cached || fetch(request).then(response => {
      const copy = response.clone();
      caches.open(CACHE).then(cache => cache.put(request, copy));
      return response;
    }).catch(() => caches.match('/offline.html'))));
    return;
  }
  if (request.mode === 'navigate') {
    event.respondWith(fetch(request).catch(() => caches.match('/offline.html')));
  }
});
