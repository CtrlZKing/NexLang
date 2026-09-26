// Minimal service worker. NexIDE only ever talks to its own local
// backend (127.0.0.1), so this deliberately does no offline caching -
// its only job is to exist, since Chromium requires an active service
// worker before it will offer to install a page as a standalone app
// ("Install NexIDE"), which is what gives NexIDE a real, independent
// taskbar/Start-Menu icon (see docs/IDE_IDENTITY.md).

self.addEventListener("install", (event) => {
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  // Pass everything straight through to the network (the local NexIDE
  // server). No caching: the backend and the files it serves can change
  // between runs, and this app is never used offline.
  event.respondWith(fetch(event.request));
});
