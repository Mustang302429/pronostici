// Service worker: l'app si apre anche senza rete (mostra gli ultimi dati scaricati).
// I dati vengono sempre presi prima dalla rete, così sono aggiornati.
const CACHE = 'pronostici-v3';
const BASE = ['./', 'index.html', 'style.css', 'app.js', 'manifest.webmanifest', 'icon-192.png', 'icon-512.png'];
self.addEventListener('install', e => { e.waitUntil(caches.open(CACHE).then(c => c.addAll(BASE))); self.skipWaiting(); });
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(k => Promise.all(k.filter(x => x !== CACHE).map(x => caches.delete(x))))); self.clients.claim();
});
self.addEventListener('fetch', e => {
  const u = new URL(e.request.url);
  if (e.request.method !== 'GET' || u.origin !== location.origin) return;
  e.respondWith(fetch(e.request).then(r => {
    const copia = r.clone(); const k = u.pathname.endsWith('data.json') ? new Request(u.origin + u.pathname) : e.request;
    caches.open(CACHE).then(c => c.put(k, copia)); return r;
  }).catch(() => caches.match(u.pathname.endsWith('data.json') ? new Request(u.origin + u.pathname) : e.request)));
});
