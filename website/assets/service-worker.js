'use strict';
const PREFIX = 'mdaai-public-';
const CACHE = PREFIX + '__REVISION__';
const PUBLIC = new Set(__PUBLIC_URLS__);
const LIMIT = 40;
const MAX_BYTES = 512 * 1024;
let writes = Promise.resolve();
self.addEventListener('install', event => {
  event.waitUntil((async () => {
    const response = await fetch('/offline.html', {cache:'reload'});
    if (!response.ok || !response.headers.get('content-type')?.includes('text/html')) throw new Error('Offline fallback unavailable');
    await (await caches.open(CACHE)).put('/offline.html', response);
  })());
});
self.addEventListener('activate', event => {
  event.waitUntil((async () => {
    await Promise.all((await caches.keys()).filter(k => k.startsWith(PREFIX) && k !== CACHE).map(k => caches.delete(k)));
    await self.clients.claim();
  })());
});
self.addEventListener('message', event => {
  if (event.data?.type === 'ACTIVATE_UPDATE') event.waitUntil(self.skipWaiting());
});
function save(request, response) {
  writes = writes.catch(() => {}).then(async () => {
    const type = response.headers.get('content-type') || '';
    if (!response.ok || response.status !== 200 || response.redirected || response.type !== 'basic' ||
        /no-store|private/i.test(response.headers.get('cache-control') || '') ||
        !/text\/html|text\/css|javascript/.test(type) ||
        (request.mode === 'navigate' && !type.includes('text/html')) ||
        (await response.clone().arrayBuffer()).byteLength > MAX_BYTES) return;
    const cache = await caches.open(CACHE);
    await cache.delete(request);
    const keys = (await cache.keys()).filter(r => new URL(r.url).pathname !== '/offline.html');
    // Evict BEFORE insertion so even concurrent readers never see LIMIT + 1.
    while (keys.length >= LIMIT - 1) await cache.delete(keys.shift());
    await cache.put(request, response);
  });
  return writes;
}
self.addEventListener('fetch', event => {
  const request = event.request, url = new URL(request.url);
  if (request.method !== 'GET' || url.origin !== self.location.origin || url.search ||
      request.headers.has('authorization') || request.headers.has('range')) return;
  const navigation = request.mode === 'navigate';
  // Even unknown navigations receive fallback, but never cache unknown/auth/API routes.
  if (!navigation && !PUBLIC.has(url.pathname)) return;
  if (/^\/(api|auth|login|logout|account|admin)(\/|$)/i.test(url.pathname)) return;
  event.respondWith((async () => {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 5000);
    try {
      const response = await fetch(request, {signal:controller.signal});
      // Preserve genuine HTTP error statuses; fallback only on network failure.
      if (PUBLIC.has(url.pathname)) event.waitUntil(save(request, response.clone()));
      return response;
    } catch (_) {
      const cache = await caches.open(CACHE);
      return (PUBLIC.has(url.pathname) && await cache.match(request)) ||
        (navigation ? await cache.match('/offline.html') : Response.error());
    } finally {clearTimeout(timer);}
  })());
});
