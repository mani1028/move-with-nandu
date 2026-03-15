// SAFE SERVICE WORKER — NO CACHE BREAKAGE

self.addEventListener("install", event => {
  self.skipWaiting();
});

self.addEventListener("activate", event => {
  event.waitUntil(self.clients.claim());
});

// Network-first strategy (always get latest)
self.addEventListener("fetch", event => {
  const url = event.request.url || "";
  if (url.includes("/api/")) {
    // API calls must always hit network to avoid stale rides/payments/auth state.
    event.respondWith(fetch(event.request));
    return;
  }

  event.respondWith(
    fetch(event.request).catch(() => {
      return new Response("Offline", { status: 503 });
    })
  );
});