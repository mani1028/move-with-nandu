// SAFE SERVICE WORKER — NO CACHE BREAKAGE

self.addEventListener("install", event => {
  self.skipWaiting();
});

self.addEventListener("activate", event => {
  event.waitUntil(self.clients.claim());
});

// Network-first strategy (always get latest)
self.addEventListener("fetch", event => {
  event.respondWith(
    fetch(event.request).catch(() => {
      return new Response("Offline", { status: 503 });
    })
  );
});